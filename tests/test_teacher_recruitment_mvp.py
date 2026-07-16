"""Contracts for the clean Teacher Recruitment MVP (not the deleted legacy pipeline)."""

import json
import os
from base64 import b64encode
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner
from pydantic import ValidationError

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository, service
from backend.modules.hr.recruitment.constants import ALL_STAGES, PRIMARY_STAGES, REJECTION_REASONS
from backend.modules.hr.recruitment.schemas import (
    CandidateCreate,
    CandidateUpdate,
    DemoLessonWrite,
    SubjectTestWrite,
)


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _signed_session(data):
    secret = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip() or "dev-only-insecure-key-do-not-use-in-prod"
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    return TimestampSigner(secret).sign(encoded).decode("utf-8")


def _set_session(client, role, **extra):
    client.cookies.set(
        "session",
        _signed_session({"auth_role": role, "auth_login": f"{role}@test", **extra}),
    )


def _user(role="hr_manager"):
    return CurrentUser(login=f"{role}@test", role=role, account_id=10, staff_id=20)


def test_stage_and_rejection_taxonomies_are_stable():
    assert PRIMARY_STAGES == (
        "new_candidate",
        "responded",
        "job_interview",
        "test_and_demo",
        "under_review",
        "teacher_academy",
        "active_teacher",
    )
    assert ALL_STAGES == {*PRIMARY_STAGES, "rejected", "candidate_withdrew", "trash_bin"}
    assert "other" in REJECTION_REASONS
    assert "missing_or_invalid_documents" in REJECTION_REASONS


def test_minimal_candidate_and_blank_optional_values_validate():
    candidate = CandidateCreate.model_validate({"full_name": "  Ada Teacher  ", "application_date": ""})
    assert candidate.full_name == "Ada Teacher"
    assert candidate.application_date is None

    test = SubjectTestWrite.model_validate(
        {"result": "not_completed", "score": "", "maximum_score": ""}
    )
    assert test.score is None
    assert test.maximum_score is None

    update = CandidateUpdate.model_validate(
        {"education_background": "  BA in English Education  "}
    )
    assert update.education_background == "BA in English Education"
    with pytest.raises(ValidationError):
        CandidateUpdate.model_validate({"source": "free-form source"})


def test_demo_score_is_restricted_to_zero_through_ten():
    assert DemoLessonWrite.model_validate({"result": "passed", "score": 10}).score == 10
    with pytest.raises(ValidationError):
        DemoLessonWrite.model_validate({"result": "passed", "score": 10.01})


def test_overdue_task_status_is_derived_and_not_stored():
    payload = service._task_payload(
        {
            "id": 1,
            "status": "pending",
            "due_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        }
    )
    assert payload["status"] == "pending"
    assert payload["effective_status"] == "overdue"


def test_hod_summary_visibility_fails_closed_without_subject_scope():
    assert repository._visibility_clause(10, set()) == ("FALSE", [])
    sql, params = repository._visibility_clause(10, {7, 3})
    assert "visibility.subject_id = ANY" in sql
    assert params == [10, [3, 7]]


def test_protected_stage_and_decision_rules_fail_before_persistence():
    with pytest.raises(service.RecruitmentError, match="protected outcome"):
        service.move_candidate(
            _user(), 1, stage="active_teacher", expected_version=1
        )
    with pytest.raises(service.RecruitmentError, match="Only CEO"):
        service.make_final_decision(
            _user(), 1, {"decision": "active_teacher", "approval_id": 1}
        )
    with pytest.raises(service.RecruitmentError, match="Explain"):
        service.make_final_decision(
            _user("academic_director"),
            1,
            {"decision": "rejected", "rejection_reason": "other", "reason_detail": ""},
        )
    with pytest.raises(service.RecruitmentError, match="comment is required"):
        service.review_approval(
            _user("academic_director"),
            1,
            1,
            status="returned",
            review_comment="",
        )


def test_hr_trash_move_is_recoverable_versioned_and_audited(monkeypatch):
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()
    events = []

    @contextmanager
    def connect():
        yield conn

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "get_candidate_row",
        lambda *_args, **_kwargs: {"id": 7, "status": "job_interview", "version": 4},
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: {
            "id": kwargs["candidate_id"],
            "status": kwargs["stage"],
            "version": kwargs["expected_version"] + 1,
        },
    )
    monkeypatch.setattr(repository, "revoke_open_approvals", lambda *_args, **_kwargs: [21])
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [31])
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])),
    )
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "trash_bin"})

    candidate = service.move_candidate(
        _user(),
        7,
        stage="trash_bin",
        expected_version=4,
        reason="Pipeline trash drop",
    )

    assert candidate["status"] == "trash_bin"
    assert conn.commits == 1
    assert events == [
        (
            "candidate.hire_approvals_revoked",
            {"approval_ids": [21], "reason": "Candidate moved to Trash Bin."},
        ),
        (
            "candidate.appointments_cancelled",
            {"appointment_ids": [31], "reason": "Candidate moved to Trash Bin."},
        ),
        (
            "candidate.moved_to_trash",
            {"from": "job_interview", "to": "trash_bin", "reason": "Pipeline trash drop"},
        ),
    ]


def test_recruitment_api_is_role_scoped_and_hr_pipeline_is_available(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "list_pipeline",
        lambda user, **_filters: {"stages": {}, "counts": {}, "total": 0, "role": user.role},
    )
    _set_session(client, "hr_manager", account_id=10, staff_id=20)
    allowed = client.get("/api/v1/recruitment/pipeline", headers=XHR)
    assert allowed.status_code == 200
    assert allowed.json()["data"]["role"] == "hr_manager"

    _set_session(client, "student", account_id=11)
    denied = client.get("/api/v1/recruitment/pipeline", headers=XHR)
    assert denied.status_code == 403

    for role in ("admin", "system_admin"):
        _set_session(client, role, account_id=12)
        denied = client.get("/api/v1/recruitment/pipeline", headers=XHR)
        assert denied.status_code == 403


def test_hod_recruitment_is_limited_to_assigned_work_without_pipeline(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "list_pipeline",
        lambda user, **_filters: {"role": user.role},
    )
    _set_session(client, "head_of_department", account_id=14, staff_id=24)

    root = client.get("/head-of-departments/recruitment")
    assert root.status_code == 200
    assert '"view":"candidates"' in root.text
    assert client.get("/head-of-departments/recruitment/pipeline").status_code == 404
    assert client.get("/api/v1/recruitment/pipeline", headers=XHR).status_code == 403


def test_hr_page_renders_new_shared_workspace_without_legacy_pipeline(client):
    _set_session(client, "hr_manager", account_id=10, staff_id=20)
    response = client.get("/hr-manager")
    assert response.status_code == 200
    assert '"page":"recruitment-workspace"' in response.text
    assert "Lesson Practice" not in response.text

    settings = client.get("/hr-manager/settings")
    assert settings.status_code == 200
    assert '"view":"settings"' in settings.text

    trash = client.get("/hr-manager/trash")
    assert trash.status_code == 200
    assert '"view":"trash"' in trash.text

    schedule = client.get("/hr-manager/schedule")
    assert schedule.status_code == 200
    assert '"view":"schedule"' in schedule.text

    _set_session(client, "ceo", account_id=11, staff_id=21)
    assert client.get("/ceo/recruitment/trash").status_code == 404


def test_appointment_apis_allow_scoped_reads_but_only_hr_or_ceo_management(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "list_appointments",
        lambda user, **_values: {"items": [], "total": 0, "role": user.role},
    )
    monkeypatch.setattr(
        service,
        "schedule_stage_move",
        lambda user, candidate_id, values: {
            "candidate": {"id": candidate_id, "status": values["stage"]},
            "appointment": {"id": 90, "appointment_type": "job_interview"},
            "role": user.role,
        },
    )

    _set_session(client, "academic_director", account_id=41, staff_id=51)
    visible = client.get("/api/v1/recruitment/appointments", headers=XHR)
    assert visible.status_code == 200
    assert visible.json()["data"]["role"] == "academic_director"
    denied = client.post(
        "/api/v1/recruitment/candidates/7/scheduled-stage-moves",
        headers=XHR,
        json={
            "stage": "job_interview",
            "expected_version": 4,
            "starts_at": "2099-07-16T10:00:00",
            "duration_minutes": 30,
        },
    )
    assert denied.status_code == 403

    _set_session(client, "hr_manager", account_id=41, staff_id=51)
    allowed = client.post(
        "/api/v1/recruitment/candidates/7/scheduled-stage-moves",
        headers=XHR,
        json={
            "stage": "job_interview",
            "expected_version": 4,
            "starts_at": "2099-07-16T10:00:00",
            "duration_minutes": 30,
        },
    )
    assert allowed.status_code == 201
    assert allowed.json()["data"]["appointment"]["id"] == 90

    def conflict(*_args, **_kwargs):
        raise service.RecruitmentError(
            "The selected staff member is busy.",
            status_code=409,
            code="appointment_conflict",
            details=[{"id": 91, "candidate_name": "Existing candidate"}],
        )

    monkeypatch.setattr(service, "schedule_stage_move", conflict)
    overlapping = client.post(
        "/api/v1/recruitment/candidates/7/scheduled-stage-moves",
        headers=XHR,
        json={
            "stage": "job_interview",
            "expected_version": 4,
            "starts_at": "2099-07-16T10:00:00",
            "duration_minutes": 30,
            "responsible_account_id": 41,
        },
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["code"] == "appointment_conflict"
    assert overlapping.json()["details"][0]["candidate_name"] == "Existing candidate"


def test_recruitment_settings_api_is_hr_managed_and_ceo_read_only(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "list_settings",
        lambda user: {"items": [], "sources": [], "rejection_reasons": [], "role": user.role},
    )
    monkeypatch.setattr(
        service,
        "add_setting",
        lambda user, **values: {"id": 9, "category": values["category"], "label": values["label"]},
    )
    monkeypatch.setattr(
        service,
        "remove_setting",
        lambda user, setting_id: {"id": setting_id, "is_active": False},
    )

    _set_session(client, "hr_manager", account_id=10, staff_id=20)
    assert client.get("/api/v1/recruitment/settings", headers=XHR).status_code == 200
    created = client.post(
        "/api/v1/recruitment/settings",
        headers=XHR,
        json={"category": "source", "label": "Job fair"},
    )
    assert created.status_code == 201
    assert created.json()["data"]["setting"]["label"] == "Job fair"
    assert client.delete("/api/v1/recruitment/settings/9", headers=XHR).status_code == 200

    _set_session(client, "ceo", account_id=11, staff_id=21)
    response = client.get("/api/v1/recruitment/settings", headers=XHR)
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "ceo"
    assert client.post(
        "/api/v1/recruitment/settings",
        headers=XHR,
        json={"category": "source", "label": "Denied"},
    ).status_code == 403


def test_hr_setting_creation_is_normalized_committed_and_audited(monkeypatch):
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()
    events = []

    @contextmanager
    def connect():
        yield conn

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(repository, "recruitment_setting_by_label_or_value", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        repository,
        "save_recruitment_setting",
        lambda *_args, **kwargs: {
            "id": 7,
            "category": kwargs["category"],
            "value": kwargs["value"],
            "label": kwargs["label"],
            "is_active": True,
            "sort_order": 10,
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_recruitment_setting_audit",
        lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])),
    )

    setting = service.add_setting(
        _user(),
        category="rejection_reason",
        label="  Weak communication skills  ",
    )

    assert setting["value"] == "weak_communication_skills"
    assert setting["label"] == "Weak communication skills"
    assert conn.commits == 1
    assert events == [
        (
            "recruitment.setting_created",
            {
                "category": "rejection_reason",
                "value": "weak_communication_skills",
                "label": "Weak communication skills",
            },
        )
    ]


def test_admin_recruitment_pages_are_not_registered(client):
    _set_session(client, "admin", account_id=1)

    for path in (
        "/internal/operations/recruitment",
        "/internal/operations/recruitment/pipeline",
        "/internal/operations/recruitment/candidates",
    ):
        assert client.get(path).status_code == 404


def test_migration_preserves_candidates_and_normalizes_history():
    source = Path("database/alembic/versions/0013_teacher_recruitment_mvp.py").read_text()
    for mapping in (
        "WHEN 'new' THEN 'new_candidate'",
        "WHEN 'interview' THEN 'job_interview'",
        "WHEN 'math_test' THEN 'test_and_demo'",
        "WHEN 'training_passed' THEN 'under_review'",
        "WHEN 'hired' THEN 'active_teacher'",
    ):
        assert mapping in source
    for table in (
        "teacher_candidate_documents",
        "teacher_candidate_interviews",
        "teacher_candidate_subject_tests",
        "teacher_candidate_demo_lessons",
        "teacher_candidate_assignments",
        "teacher_candidate_tasks",
        "teacher_candidate_notes",
        "teacher_candidate_hire_approvals",
        "teacher_candidate_final_decisions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS msi_v2.{table}" in source
    upgrade_source = source.split("def downgrade", 1)[0]
    assert "DROP TABLE IF EXISTS msi_v2.teacher_candidates" not in upgrade_source
    assert "candidate.legacy_event" in upgrade_source


def test_decision_queue_migration_is_history_preserving_and_partial():
    source = Path("database/alembic/versions/0014_hr_access_decision_queue.py").read_text()

    assert "idx_teacher_candidate_hire_approvals_actionable" in source
    assert "WHERE status IN ('requested', 'approved')" in source
    assert "DELETE FROM" not in source
    assert "DROP TABLE" not in source.split("def downgrade", 1)[0]


def test_candidate_education_migration_preserves_existing_candidates():
    source = Path(
        "database/alembic/versions/0021_candidate_education_background.py"
    ).read_text()
    upgrade_source = source.split("def downgrade", 1)[0]

    assert "ADD COLUMN IF NOT EXISTS education_background" in upgrade_source
    assert "DELETE FROM" not in upgrade_source
    assert "DROP TABLE" not in upgrade_source


def test_recruitment_settings_migration_seeds_editable_taxonomies_without_candidate_loss():
    source = Path("database/alembic/versions/0016_recruitment_settings.py").read_text()
    upgrade_source = source.split("def downgrade", 1)[0]

    assert "CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_settings" in upgrade_source
    assert "'source', 'hh.uz', 'hh.uz'" in upgrade_source
    assert "'rejection_reason', 'other', 'Other'" in upgrade_source
    assert "is_active BOOLEAN NOT NULL DEFAULT true" in upgrade_source
    assert "DELETE FROM" not in upgrade_source
    assert "teacher_candidates" not in upgrade_source


def test_candidate_trash_bin_migration_is_soft_delete_only():
    source = Path("database/alembic/versions/0017_candidate_trash_bin.py").read_text()
    upgrade_source = source.split("def downgrade", 1)[0]

    assert "Revision ID: 0017_candidate_trash_bin" in source
    assert "Revises: 0016_recruitment_settings" in source
    assert "'trash_bin'" in upgrade_source
    assert "DELETE FROM" not in upgrade_source
    assert "DROP TABLE" not in upgrade_source


def test_trashed_candidates_are_archived_from_operational_queries():
    source = Path("backend/modules/hr/recruitment/repository.py").read_text()

    assert "else:\n        clauses.append(\"candidate.status <> 'trash_bin'\")" in source
    assert source.count("WHERE candidate.status <> 'trash_bin' AND ({visibility})") == 2


def test_recruitment_document_urls_never_use_public_resource_url():
    source = Path("backend/platform/storage/r2.py").read_text()
    private_function = source.split("def build_private_candidate_document_url", 1)[1]
    private_function = private_function.split("\ndef ", 1)[0]
    assert "generate_presigned_url" in private_function
    assert "public_base_url" not in private_function


def test_deleted_legacy_candidate_endpoints_and_lesson_practice_stay_absent(app):
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/admin/teacher-candidates" not in paths
    assert not Path("frontend/src/features/teacher-academy/TrainingEvaluationModal.tsx").exists()
    assert not Path("frontend/src/features/hr/recruitment/PromoteModal.tsx").exists()
