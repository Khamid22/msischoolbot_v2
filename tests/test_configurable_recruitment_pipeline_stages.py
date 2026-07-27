"""Contracts for database-backed configurable Recruitment pipeline stages."""

from contextlib import contextmanager
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.core.access import CurrentUser
from backend.modules.domains.recruitment import repository, service
from backend.modules.domains.recruitment.schemas import (
    PipelineStageArchive,
    PipelineStageCreate,
    PipelineStageUpdate,
)


def _user(role: str) -> CurrentUser:
    return CurrentUser(
        login=f"{role}@test",
        role=role,
        account_id=10,
        staff_id=20,
    )


def _stage(
    key: str,
    label: str,
    order: int,
    *,
    kind: str = "system",
    active: bool = True,
) -> dict[str, object]:
    return {
        "id": order,
        "stage_key": key,
        "label": label,
        "stage_kind": kind,
        "color_token": "blue" if kind == "custom" else "neutral",
        "sort_order": order,
        "is_pipeline": True,
        "is_active": active,
        "replacement_stage_key": None,
        "sla_target_days": 2,
        "version": 1,
    }


def test_stage_payload_contract_validates_palette_sla_and_versions():
    payload = PipelineStageCreate.model_validate(
        {
            "label": "Reference Check",
            "color_token": "violet",
            "after_stage_key": "job_interview",
            "sla_target_days": 3,
        }
    )
    assert payload.color_token == "violet"
    assert PipelineStageUpdate.model_validate(
        {"expected_version": 4, "label": "References"}
    ).expected_version == 4
    assert PipelineStageArchive.model_validate(
        {"expected_version": 4, "replacement_stage_key": "test_and_demo"}
    ).replacement_stage_key == "test_and_demo"

    with pytest.raises(ValidationError):
        PipelineStageCreate.model_validate(
            {
                "label": "Reference Check",
                "color_token": "pink",
                "after_stage_key": "job_interview",
                "sla_target_days": 3,
            }
        )
    with pytest.raises(ValidationError):
        PipelineStageCreate.model_validate(
            {
                "label": "Reference Check",
                "color_token": "rose",
                "after_stage_key": "job_interview",
                "sla_target_days": 0,
            }
        )


def test_ceo_reads_pipeline_configuration_but_cannot_mutate(monkeypatch):
    rows = [
        _stage("new_candidate", "Application Received", 10),
        _stage("custom_reference", "Reference Check", 20, kind="custom"),
    ]

    @contextmanager
    def connect():
        yield object()

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "list_pipeline_stage_rows",
        lambda *_args, **_kwargs: rows,
    )

    response = service.list_pipeline_stages(_user("ceo"))

    assert response["read_only"] is True
    assert [item["label"] for item in response["items"]] == [
        "Application Received",
        "Reference Check",
    ]
    assert all(item["can_rename"] is False for item in response["items"])
    with pytest.raises(service.RecruitmentError, match="Only HR Manager"):
        service.create_pipeline_stage(
            _user("ceo"),
            label="References",
            color_token="cyan",
            after_stage_key="job_interview",
            sla_target_days=2,
        )


def test_custom_placement_never_reorders_system_stages_relative_to_each_other():
    rows = [
        _stage("new_candidate", "Application Received", 10),
        _stage("responded", "Interview Schedule", 20),
        _stage("custom_reference", "Reference Check", 30, kind="custom"),
        _stage("job_interview", "Job Interview", 40),
    ]

    ordered = service._ordered_stage_keys_after(
        rows,
        stage_key="custom_reference",
        after_stage_key="new_candidate",
    )

    assert ordered == [
        "new_candidate",
        "custom_reference",
        "responded",
        "job_interview",
    ]
    assert [key for key in ordered if not key.startswith("custom_")] == [
        "new_candidate",
        "responded",
        "job_interview",
    ]


def test_dragging_to_custom_stage_is_a_versioned_manual_transition(monkeypatch):
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()
    transition: dict[str, object] = {}
    audits: list[tuple[str, dict[str, object]]] = []

    @contextmanager
    def connect():
        yield conn

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "active_pipeline_stage_by_key",
        lambda *_args, **_kwargs: _stage(
            "custom_reference", "Reference Check", 25, kind="custom"
        ),
    )
    monkeypatch.setattr(
        repository,
        "get_candidate_row",
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "responded",
            "version": 4,
        },
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: transition.update(kwargs)
        or {"id": 7, "status": kwargs["stage"], "version": 5},
    )
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: audits.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )
    monkeypatch.setattr(service, "_sync_system_next_actions", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "custom_reference",
            "version": 5,
        },
    )

    result = service.move_candidate(
        _user("hr_manager"),
        7,
        stage="custom_reference",
        expected_version=4,
        reason="References requested",
    )

    assert result["status"] == "custom_reference"
    assert transition["stage"] == "custom_reference"
    assert transition["expected_version"] == 4
    assert transition["transition_source"] == "manual"
    assert transition["comment"] == "References requested"
    assert audits == [
        (
            "candidate.stage_changed",
            {
                "from": "responded",
                "to": "custom_reference",
                "reason": "References requested",
            },
        )
    ]
    assert conn.commits == 1


def test_registry_migration_preserves_records_and_replaces_fixed_stage_checks():
    migration = Path(
        "database/alembic/versions/0035_configurable_recruitment_pipeline_stages.py"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_pipeline_stages" in migration
    assert "teacher_candidates_status_stage_fk" in migration
    assert "teacher_candidate_stage_history_stage_fk" in migration
    assert "teacher_recruitment_sla_rules_stage_fk" in migration
    assert "uq_recruitment_pipeline_stage_label" in migration
    assert "lower(btrim(label))" in migration
    assert "'on_hold', 'On Hold (legacy)'" in migration
    assert "UPDATE msi_v2.teacher_candidates" not in migration.split("def downgrade", 1)[0]


def test_test_and_demo_stage_has_a_unique_orange_color_migration():
    migration = Path(
        "database/alembic/versions/0038_test_demo_stage_color.py"
    ).read_text(encoding="utf-8")
    upgrade = migration.split("def downgrade", 1)[0]

    assert 'revision = "0039_test_demo_color"' in migration
    assert 'down_revision = "0038_appt_start_rollback"' in migration
    assert "stage_key = 'test_and_demo'" in upgrade
    assert "color_token = 'orange'" in upgrade
    assert "stage_key = 'teacher_academy'" not in migration


def test_custom_stage_sla_uses_application_date_with_created_at_fallback():
    source = Path(
        "backend/modules/domains/recruitment/candidates/repository.py"
    ).read_text(encoding="utf-8")

    assert "definition.stage_kind = 'custom'" in source
    assert "updated.application_date::timestamp AT TIME ZONE 'Asia/Tashkent'" in source
    assert "updated.created_at" in source
