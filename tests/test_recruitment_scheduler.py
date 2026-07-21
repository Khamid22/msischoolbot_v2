"""Appointment scheduling contracts for the recruitment workspace."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import notifications, repository, service
from backend.modules.hr.recruitment.schemas import AppointmentCreate


ROOT = Path(__file__).resolve().parents[1]
XHR = {"X-Requested-With": "XMLHttpRequest"}


def _user(role: str = "hr_manager") -> CurrentUser:
    return CurrentUser(
        login=f"{role}@test",
        role=role,
        account_id=41,
        staff_id=51,
    )


class _Connection:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class _DatabaseConnection(_Connection):
    """Marks a mocked connection as production-like without executing SQL."""

    def execute(self, *_args, **_kwargs):
        raise AssertionError("This test must mock every repository operation.")


class _QueryResult:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _NotificationListConnection:
    def __init__(self):
        self.queries: list[str] = []

    def execute(self, query, _params):
        self.queries.append(str(query))
        if "count(*)" in str(query):
            return _QueryResult(row={"total": 0})
        return _QueryResult(rows=[])


class _StageUpdateConnection:
    def __init__(self):
        self.params = ()
        self.last_sql = ""

    def execute(self, query, params):
        self.last_sql = query
        self.params = tuple(params)
        return _QueryResult(row={"id": 7, "status": "test_and_demo", "version": 5})


def _connection_factory(conn):
    @contextmanager
    def connect():
        yield conn

    return connect


def test_stage_update_normalizes_legacy_historical_transition_source():
    conn = _StageUpdateConnection()

    updated = repository.update_candidate_stage(
        conn,
        candidate_id=7,
        stage="test_and_demo",
        expected_version=4,
        actor_account_id=41,
        now="2026-07-20T05:19:26+00:00",
        comment="Passed historical job interview",
        transition_source="historical_restoration",
    )

    assert updated["version"] == 5
    assert conn.params[10] == "restored"


def test_stage_update_anchors_new_candidate_sla_to_application_date():
    """Dragging a card back to Application Received must not reset an
    already-elapsed/overdue SLA to a fresh countdown from "now"."""
    conn = _StageUpdateConnection()

    repository.update_candidate_stage(
        conn,
        candidate_id=7,
        stage="new_candidate",
        expected_version=4,
        actor_account_id=41,
        now="2026-07-21T12:00:00+00:00",
        comment="Moved to Application Received.",
        transition_source="manual",
    )

    sql = conn.last_sql
    assert "candidate.application_date" in sql
    assert "updated.status = 'new_candidate'" in sql
    assert "AT TIME ZONE 'Asia/Tashkent'" in sql
    assert conn.params[9] == "Moved to Application Received."
    assert conn.params[10] == "manual"
    assert "teacher_recruitment_pipeline_stages definition" in sql


def test_stage_update_anchors_custom_stage_sla_without_rewriting_history_time():
    conn = _StageUpdateConnection()

    repository.update_candidate_stage(
        conn,
        candidate_id=7,
        stage="custom_reference_check",
        expected_version=4,
        actor_account_id=41,
        now="2026-07-21T12:00:00+00:00",
        comment="Moved to Reference Check.",
        transition_source="manual",
    )

    sql = conn.last_sql
    assert "definition.stage_kind = 'custom'" in sql
    assert "updated.application_date::timestamp AT TIME ZONE 'Asia/Tashkent'" in sql
    assert "updated.created_at" in sql
    assert "SELECT updated.id, updated.status" in sql


def _future_values(**overrides):
    return {
        "stage": "job_interview",
        "expected_version": 4,
        "starts_at": datetime(2099, 7, 16, 10, 0),
        "responsible_account_id": None,
        "appointment_format": "Online",
        "location_or_link": "https://meet.example/interview",
        "topic": "",
        "note": "First interview",
        **overrides,
    }


def test_migration_adds_normalized_appointments_and_optional_evaluation_links():
    migration = (ROOT / "database/alembic/versions/0018_recruitment_appointments.py").read_text()

    assert 'revision = "0018_recruitment_appointments"' in migration
    assert 'down_revision = "0017_candidate_trash_bin"' in migration
    assert "CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_appointments" in migration
    assert "appointment_type IN ('job_interview', 'demo_lesson')" in migration
    assert "status IN ('scheduled', 'completed', 'cancelled', 'no_show')" in migration
    assert migration.count("ADD COLUMN IF NOT EXISTS appointment_id BIGINT") == 2


def test_workflow_simplification_migration_preserves_history_and_enforces_one_active_appointment():
    migration = (ROOT / "database/alembic/versions/0019_recruitment_workflow_simplification.py").read_text()

    assert 'revision = "0019_recruitment_workflow"' in migration
    assert 'down_revision = "0018_recruitment_appointments"' in migration
    assert "'responded'" in migration
    assert "CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_holds" in migration
    assert "ADD COLUMN IF NOT EXISTS origin_stage" in migration
    assert migration.count("ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ") == 3
    assert "idx_teacher_candidate_appointments_active_type" in migration
    assert "Superseded during recruitment workflow migration" in migration
    assert "DELETE FROM msi_v2.teacher_candidates" not in migration
    assert "DELETE FROM msi_v2.teacher_candidate_appointments" not in migration


def test_notification_migration_preserves_history_and_protects_system_reasons():
    migration = (ROOT / "database/alembic/versions/0020_recruitment_notifications_and_auto_outcomes.py").read_text()

    assert 'revision = "0020_recruitment_notifications"' in migration
    assert 'down_revision = "0019_recruitment_workflow"' in migration
    assert "CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_notifications" in migration
    assert "idx_teacher_recruitment_notifications_dedupe" in migration
    assert "idx_account_telegram_links_active_identity" in migration
    assert "failed_job_interview" in migration
    assert "failed_subject_test" in migration
    assert "failed_demo_lesson" in migration
    assert "is_system_generated" in migration
    assert "DELETE FROM msi_v2.teacher_candidates" not in migration


def test_notification_dashboard_can_request_unread_rows_only():
    conn = _NotificationListConnection()

    rows, total = repository.list_recruitment_notification_rows(
        conn,
        account_id=41,
        limit=8,
        offset=0,
        unread_only=True,
    )

    assert rows == []
    assert total == 0
    assert len(conn.queries) == 2
    assert all("read_at IS NULL" in query for query in conn.queries)


def test_naive_form_time_is_interpreted_as_asia_tashkent():
    normalized = service._school_datetime(datetime(2099, 7, 16, 10, 0))

    assert normalized == datetime(2099, 7, 16, 5, 0, tzinfo=UTC)


def test_appointment_contract_is_point_in_time_and_rejects_duration():
    payload = AppointmentCreate.model_validate(
        {
            "appointment_type": "job_interview",
            "starts_at": "2099-07-16T10:00:00",
            "appointment_format": "Online",
        }
    )
    assert not hasattr(payload, "duration_minutes")

    with pytest.raises(ValueError):
        AppointmentCreate.model_validate(
            {
                "appointment_type": "job_interview",
                "starts_at": "2099-07-16T10:00:00",
                "duration_minutes": 30,
            }
        )


def test_past_appointment_uses_the_same_point_in_time_contract(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(
        repository,
        "responsible_account_row",
        lambda *_args, **_kwargs: {
            "id": 72,
            "role": "academic_director",
            "status": "active",
        },
    )

    prepared = service._prepare_appointment(
        conn,
        user=_user(),
        candidate={"id": 7, "subject_id": 3},
        appointment_type="demo_lesson",
        values={
            "starts_at": datetime(2020, 7, 16, 10, 0),
            "responsible_account_id": 72,
            "appointment_format": "In person",
            "topic": "Quadratic equations",
        },
    )

    assert prepared["starts_at"] == "2020-07-16T05:00:00+00:00"
    assert prepared["ends_at"] is None
    assert prepared["responsible_account_id"] == 72
    assert prepared["appointment_format"] == "In person"


def test_hr_manager_can_be_assigned_as_demo_evaluator(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(
        repository,
        "responsible_account_row",
        lambda *_args, **_kwargs: {
            "id": 41,
            "role": "hr_manager",
            "status": "active",
        },
    )

    prepared = service._prepare_appointment(
        conn,
        user=_user(),
        candidate={"id": 7, "subject_id": 3},
        appointment_type="demo_lesson",
        values={
            "starts_at": datetime(2099, 7, 16, 10, 0),
            "responsible_account_id": 41,
            "appointment_format": "In person",
        },
    )

    assert prepared["responsible_account_id"] == 41


def test_start_overwrites_scheduled_time_and_uses_optimistic_version(monkeypatch):
    conn = _Connection()
    calls = []
    audits = []
    reads = [
        {
            "id": 92,
            "candidate_id": 7,
            "appointment_type": "job_interview",
            "status": "scheduled",
            "starts_at": "2025-01-01T08:00:00+00:00",
            "ends_at": None,
            "responsible_account_id": 41,
            "version": 4,
        },
        {
            "id": 92,
            "candidate_id": 7,
            "appointment_type": "job_interview",
            "status": "in_progress",
            "starts_at": "2026-07-20T19:45:00+00:00",
            "started_at": "2026-07-20T19:45:00+00:00",
            "ends_at": None,
            "responsible_account_id": 41,
            "version": 5,
        },
    ]
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {"id": 7, "status": "job_interview"},
    )
    monkeypatch.setattr(
        repository,
        "get_appointment_row",
        lambda *_args, **_kwargs: reads.pop(0),
    )
    monkeypatch.setattr(
        repository,
        "start_appointment_session",
        lambda *_args, **kwargs: calls.append(kwargs) or {"id": 92, "version": 5},
    )
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        service,
        "_audit_appointment",
        lambda *_args, **kwargs: audits.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )
    monkeypatch.setattr(
        service, "_sync_system_next_actions", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        service, "get_candidate", lambda *_args, **_kwargs: {"id": 7}
    )

    result = service.start_appointment_session(
        _user(),
        7,
        92,
        expected_version=4,
    )

    assert calls[0]["expected_version"] == 4
    assert calls[0]["now"] != "2025-01-01T08:00:00+00:00"
    assert result["appointment"]["starts_at"] == "2026-07-20T19:45:00+00:00"
    assert result["appointment"]["ends_at"] is None
    assert audits == [
        (
            "candidate.interview_started",
            {
                "scheduled_starts_at": "2025-01-01T08:00:00+00:00",
                "started_at": calls[0]["now"],
                "scheduled_time_overwritten": True,
            },
        )
    ]
    assert conn.commits == 1


def test_only_assigned_evaluator_can_start_demo(monkeypatch):
    conn = _Connection()
    starts = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo"},
    )
    monkeypatch.setattr(
        repository,
        "get_appointment_row",
        lambda *_args, **_kwargs: {
            "id": 92,
            "candidate_id": 7,
            "appointment_type": "demo_lesson",
            "status": "scheduled",
            "starts_at": "2026-07-20T08:00:00+00:00",
            "responsible_account_id": 72,
            "version": 4,
        },
    )
    monkeypatch.setattr(
        repository,
        "start_appointment_session",
        lambda *_args, **kwargs: starts.append(kwargs) or {"id": 92},
    )

    with pytest.raises(service.RecruitmentError, match="assigned evaluator") as exc:
        service.start_appointment_session(
            _user("academic_director"),
            7,
            92,
            expected_version=4,
        )

    assert exc.value.status_code == 403
    assert starts == []
    assert conn.commits == 0


def test_interview_completion_uses_existing_structured_profile_fields(monkeypatch):
    captured = []
    monkeypatch.setattr(
        service,
        "_add_record",
        lambda *_args, **kwargs: captured.append((_args, kwargs)) or {"id": 7},
    )

    result = service.complete_interview_session(
        _user(),
        7,
        92,
        {
            "expected_version": 5,
            "result": "passed",
            "english_level_option_id": 3,
            "education_background": "BA in English",
            "teaching_experience_option_id": 8,
            "interests_hobbies": "Debate and reading",
            "motivation_expectations": "Wants to grow as a teacher",
        },
    )

    values = captured[0][0][2]
    assert result == {"id": 7}
    assert values["appointment_id"] == 92
    assert values["english_level_option_id"] == 3
    assert values["education_background"] == "BA in English"
    assert values["teaching_experience_option_id"] == 8
    assert values["interests_hobbies"] == "Debate and reading"
    assert values["motivation_expectations"] == "Wants to grow as a teacher"
    assert values["notes"] == ""


def test_forward_stage_progress_never_fabricates_evaluation_passes():
    states = service._derived_evaluation_states(
        {
            "status": "under_review",
            "latest_interview_result": "",
            "latest_demo_result": "",
            "latest_subject_test_result": "",
        }
    )

    assert states == {
        "interview": "missing",
        "demo": "missing",
        "subject_test": "missing",
    }


def test_scheduled_stage_move_creates_appointment_and_stage_atomically(monkeypatch):
    conn = _Connection()
    events = []
    moved = []
    inserted = []
    candidate = {"id": 7, "status": "new_candidate", "version": 4, "subject_id": 3}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: moved.append(kwargs) or {"id": 7, "status": kwargs["stage"], "version": 5},
    )
    monkeypatch.setattr(
        repository,
        "insert_appointment",
        lambda *_args, **kwargs: inserted.append(kwargs) or 91,
    )
    monkeypatch.setattr(repository, "list_appointment_conflicts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])),
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "job_interview",
            "appointments": [{"id": 91, "appointment_type": "job_interview"}],
        },
    )

    result = service.schedule_stage_move(_user(), 7, _future_values())

    assert conn.commits == 1
    assert moved[0]["stage"] == "job_interview"
    assert moved[0]["expected_version"] == 4
    assert inserted[0]["values"]["starts_at"] == "2099-07-16T05:00:00+00:00"
    assert inserted[0]["values"]["ends_at"] is None
    assert inserted[0]["values"]["responsible_account_id"] == 41
    assert result["appointment"]["id"] == 91
    assert [event for event, _detail in events] == [
        "candidate.appointment_scheduled",
        "candidate.stage_changed",
    ]


def test_demo_stage_move_ensures_evaluator_assignment_and_audits_it(monkeypatch):
    conn = _Connection()
    assignments = []
    events = []
    candidate = {"id": 7, "status": "job_interview", "version": 4, "subject_id": 3}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(
        repository,
        "responsible_account_row",
        lambda *_args, **_kwargs: {"id": 72, "role": "academic_director", "status": "active"},
    )
    monkeypatch.setattr(repository, "list_appointment_conflicts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **_kwargs: {"id": 7, "version": 5})
    monkeypatch.setattr(
        repository,
        "ensure_candidate_assignment",
        lambda *_args, **kwargs: assignments.append(kwargs),
    )
    monkeypatch.setattr(repository, "insert_appointment", lambda *_args, **_kwargs: 92)
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])),
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 7, "appointments": [{"id": 92}]},
    )

    service.schedule_stage_move(
        _user(),
        7,
        _future_values(
            stage="test_and_demo",
            responsible_account_id=72,
            topic="Quadratic equations",
        ),
    )

    assert assignments[0]["assignee_account_id"] == 72
    assert assignments[0]["subject_id"] == 3
    assert "candidate.assignment_ensured" in [event for event, _detail in events]


def test_point_in_time_appointments_do_not_run_slot_conflict_checks(monkeypatch):
    conn = _Connection()
    conflict_checks = []
    monkeypatch.setattr(
        repository,
        "list_appointment_conflicts",
        lambda *_args, **_kwargs: conflict_checks.append(True) or [],
    )

    prepared = service._prepare_appointment(
        conn,
        user=_user(),
        candidate={"id": 7, "subject_id": 3},
        appointment_type="job_interview",
        values=_future_values(),
        job_interviewer_account_id=41,
    )

    assert prepared["ends_at"] is None
    assert conflict_checks == []


def test_hod_demo_evaluator_is_assigned_without_teacher_academy_scope_check(monkeypatch):
    conn = _Connection()
    assignments = []
    candidate = {"id": 7, "status": "job_interview", "version": 4, "subject_id": 3}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(
        repository,
        "responsible_account_row",
        lambda *_args, **_kwargs: {"id": 72, "role": "head_of_department", "status": "active"},
    )
    monkeypatch.setattr(repository, "list_appointment_conflicts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **_kwargs: {"id": 7, "version": 5})
    monkeypatch.setattr(
        repository,
        "ensure_candidate_assignment",
        lambda *_args, **kwargs: assignments.append(kwargs),
    )
    monkeypatch.setattr(repository, "insert_appointment", lambda *_args, **_kwargs: 92)
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 7, "appointments": [{"id": 92}]},
    )

    result = service.schedule_stage_move(
        _user(),
        7,
        _future_values(stage="test_and_demo", responsible_account_id=72),
    )

    assert result["appointment"]["id"] == 92
    assert assignments[0]["assignee_account_id"] == 72
    assert assignments[0]["subject_id"] == 3
    assert conn.commits == 1


def test_appointment_list_accepts_current_and_completed_statuses_and_loads_evaluator():
    conn = _NotificationListConnection()

    rows, total = repository.list_appointment_rows(
        conn,
        status="scheduled,in_progress,completed",
        limit=25,
        offset=0,
    )

    assert rows == []
    assert total == 0
    assert all("appointment.status = ANY(%s::text[])" in query for query in conn.queries)
    assert all("teacher_candidate_demo_lessons demo_evaluation" in query for query in conn.queries)
    assert all("demo_evaluator" in query for query in conn.queries)


def test_appointment_list_filters_by_derived_schedule_statuses():
    conn = _NotificationListConnection()

    rows, total = repository.list_appointment_rows(
        conn,
        display_status="passed,failed,scheduled,in_progress,overdue,not_conducted",
        limit=25,
        offset=0,
    )

    assert rows == []
    assert total == 0
    assert all("interview_evaluation.result" in query for query in conn.queries)
    assert all("appointment.starts_at < now()" in query for query in conn.queries)
    assert all("'not_conducted'" in query for query in conn.queries)


def test_schedule_service_routes_semantic_statuses_to_the_derived_filter(monkeypatch):
    conn = _Connection()
    captured = {}
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "list_appointment_rows",
        lambda *_args, **kwargs: captured.update(kwargs) or ([], 0),
    )

    result = service.list_appointments(
        _user(),
        status="passed,overdue,not_conducted",
    )

    assert result["items"] == []
    assert captured["status"] == ""
    assert captured["display_status"] == "passed,overdue,not_conducted"


@pytest.mark.parametrize(
    ("role", "account_id", "appointment_type", "responsible_id", "status", "can_start", "can_resume"),
    [
        ("hr_manager", 41, "job_interview", 99, "scheduled", True, False),
        ("academic_director", 41, "job_interview", 41, "scheduled", False, False),
        ("hr_manager", 41, "demo_lesson", 41, "scheduled", True, False),
        ("head_of_department", 41, "demo_lesson", 41, "in_progress", False, True),
        ("academic_director", 41, "demo_lesson", 99, "scheduled", False, False),
        ("head_of_department", None, "demo_lesson", None, "scheduled", False, False),
    ],
)
def test_schedule_service_returns_role_aware_session_actions(
    monkeypatch,
    role,
    account_id,
    appointment_type,
    responsible_id,
    status,
    can_start,
    can_resume,
):
    conn = _Connection()
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "list_appointment_rows",
        lambda *_args, **_kwargs: (
            [
                {
                    "id": 91,
                    "candidate_id": 7,
                    "appointment_type": appointment_type,
                    "responsible_account_id": responsible_id,
                    "status": status,
                    "starts_at": "2026-07-21T10:00:00+00:00",
                    "evaluation_outcome": "",
                }
            ],
            1,
        ),
    )

    result = service.list_appointments(
        CurrentUser(
            login=f"{role}@test",
            role=role,
            account_id=account_id,
            staff_id=51,
        )
    )

    assert result["items"][0]["can_start"] is can_start
    assert result["items"][0]["can_resume"] is can_resume


@pytest.mark.parametrize("stage", ["job_interview", "test_and_demo"])
def test_ordinary_stage_endpoint_enters_scheduled_stage_without_an_appointment(monkeypatch, stage):
    conn = _Connection()
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "get_candidate_row",
        lambda *_args, **_kwargs: {"id": 7, "status": "new_candidate", "version": 4},
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: {"id": kwargs["candidate_id"], "status": kwargs["stage"], "version": 5},
    )
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": stage})

    result = service.move_candidate(_user(), 7, stage=stage, expected_version=4)

    assert result["status"] == stage
    assert conn.commits == 1


def test_terminal_candidate_must_be_reopened_before_an_additional_appointment(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "get_candidate_row",
        lambda *_args, **_kwargs: {"id": 7, "status": "rejected", "subject_id": 3},
    )

    with pytest.raises(service.RecruitmentError, match="Reopen this candidate"):
        service.create_appointment(
            _user(),
            7,
            {**_future_values(), "appointment_type": "job_interview"},
        )

    assert conn.commits == 0


def test_recording_demo_from_appointment_links_and_completes_atomically(monkeypatch):
    conn = _Connection()
    saved_values = []
    completed = []
    events = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: {"id": 7})
    monkeypatch.setattr(
        repository,
        "get_appointment_row",
        lambda *_args, **_kwargs: {
            "id": 92,
            "appointment_type": "demo_lesson",
            "status": "in_progress",
            "starts_at": "2099-07-16T05:00:00+00:00",
            "responsible_account_id": 41,
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_demo",
        lambda *_args, **kwargs: saved_values.append(kwargs["values"]) or 108,
    )
    monkeypatch.setattr(
        repository,
        "complete_appointment",
        lambda *_args, **kwargs: completed.append(kwargs) or {"id": 92, "version": 2},
    )
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])),
    )
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7})

    service.add_demo(
        _user("hr_manager"),
        7,
        {
            "appointment_id": 92,
            "demo_at": None,
            "result": "passed",
            "score": 9,
            "topic": "Quadratic equations",
        },
    )

    assert conn.commits == 1
    assert saved_values[0]["appointment_id"] == 92
    assert saved_values[0]["demo_at"] == "2099-07-16T05:00:00+00:00"
    assert completed[0]["appointment_id"] == 92
    assert [event for event, _detail in events] == [
        "candidate.appointment_completed",
        "candidate.demo_lesson_recorded",
    ]


def test_hr_cannot_record_demo_without_an_assigned_appointment(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "get_candidate_row",
        lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo"},
    )

    with pytest.raises(service.RecruitmentError, match="assigned to their account") as exc:
        service.add_demo(_user("hr_manager"), 7, {"result": "passed"})

    assert exc.value.status_code == 403
    assert conn.commits == 0


def test_hr_demo_notification_links_back_to_hr_recruitment():
    assert notifications._candidate_action_url(7, "hr_manager") == (
        "/hr-manager/recruitment/candidates/7?tab=evaluations"
    )


def test_cancel_appointment_uses_version_and_writes_audit(monkeypatch):
    conn = _Connection()
    updates = []
    events = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "get_appointment_row",
        lambda *_args, **_kwargs: {"id": 92, "status": "scheduled"},
    )
    monkeypatch.setattr(
        repository,
        "set_appointment_status",
        lambda *_args, **kwargs: updates.append(kwargs) or {"id": 92, "version": 3},
    )
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])),
    )
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7})

    service.change_appointment_status(
        _user(),
        7,
        92,
        status="cancelled",
        expected_version=2,
        reason="Candidate requested a new date",
    )

    assert conn.commits == 1
    assert updates[0]["expected_version"] == 2
    assert updates[0]["status"] == "cancelled"
    assert events == [
        (
            "candidate.appointment_cancelled",
            {"appointment_id": 92, "reason": "Candidate requested a new date"},
        )
    ]


def test_failed_evaluation_cancels_remaining_upcoming_appointments(monkeypatch):
    conn = _Connection()
    events = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: {"id": 7})
    monkeypatch.setattr(repository, "insert_interview", lambda *_args, **_kwargs: 108)
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [91, 92])
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "next_appointment": None})

    result = service.add_interview(_user(), 7, {"result": "failed", "notes": "Did not pass"})

    assert result["next_appointment"] is None
    assert conn.commits == 1
    assert events[0][0] == "candidate.appointments_cancelled_after_failed_evaluation"
    assert events[0][1]["appointment_ids"] == [91, 92]
    assert events[1][0] == "candidate.interview_recorded"


def test_failed_interview_atomically_rejects_with_evaluator_origin_and_system_reason(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    decisions = []
    events = []
    candidate = {"id": 7, "status": "job_interview", "version": 4}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(repository, "insert_interview", lambda *_args, **_kwargs: 108)
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(repository, "revoke_open_approvals", lambda *_args, **_kwargs: [33])
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **kwargs: stage_updates.append(kwargs) or {"id": 7})
    monkeypatch.setattr(repository, "insert_final_decision", lambda *_args, **kwargs: decisions.append(kwargs) or 90)
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs)))
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "rejected"})

    result = service.add_interview(_user(), 7, {"result": "failed", "notes": "Insufficient interview result"})

    assert result["status"] == "rejected"
    assert stage_updates[0]["stage"] == "rejected"
    assert stage_updates[0]["expected_version"] == 4
    assert decisions[0]["values"]["rejection_reason"] == "failed_job_interview"
    assert decisions[0]["values"]["origin_stage"] == "job_interview"
    assert decisions[0]["values"]["source_evaluation_type"] == "interview"
    assert decisions[0]["values"]["source_evaluation_id"] == 108
    assert decisions[0]["actor_account_id"] == 41
    assert [event for event, _kwargs in events] == [
        "candidate.interview_recorded",
        "candidate.final_decision_made",
        "candidate.stage_changed",
    ]
    assert conn.commits == 1


def test_passed_interview_from_interview_schedule_advances_to_test_and_demo(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    events = []
    candidate = {"id": 7, "status": "responded", "version": 4}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_a, **_k: candidate)
    monkeypatch.setattr(repository, "insert_interview", lambda *_a, **_k: 108)
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_a, **kw: stage_updates.append(kw) or {"id": 7})
    monkeypatch.setattr(repository, "insert_audit", lambda *_a, **kw: events.append((kw["event_type"], kw)))
    monkeypatch.setattr(service, "get_candidate", lambda *_a, **_k: {"id": 7, "status": "test_and_demo"})

    result = service.add_interview(_user(), 7, {"result": "passed", "notes": "Strong"})

    assert result["status"] == "test_and_demo"
    assert stage_updates[0]["stage"] == "test_and_demo"
    assert stage_updates[0]["expected_version"] == 4
    stage_changed = [kw for event, kw in events if event == "candidate.stage_changed"]
    assert stage_changed
    assert stage_changed[0]["detail"]["from"] == "responded"
    assert stage_changed[0]["detail"]["to"] == "test_and_demo"


def test_failed_interview_records_hr_supplied_rejection_reason(monkeypatch):
    conn = _DatabaseConnection()
    decisions = []
    candidate = {"id": 7, "status": "job_interview", "version": 4}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_a, **_k: candidate)
    monkeypatch.setattr(repository, "insert_interview", lambda *_a, **_k: 108)
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_a, **_k: [])
    monkeypatch.setattr(repository, "revoke_open_approvals", lambda *_a, **_k: [])
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_a, **_k: {"id": 7})
    monkeypatch.setattr(repository, "insert_final_decision", lambda *_a, **kw: decisions.append(kw) or 90)
    monkeypatch.setattr(repository, "insert_audit", lambda *_a, **_k: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_a, **_k: {"id": 7, "status": "rejected"})

    service.add_interview(
        _user(),
        7,
        {"result": "failed", "notes": "n", "reason_detail": "Weak subject knowledge"},
    )

    assert decisions[0]["values"]["reason_detail"] == "Weak subject knowledge"
    assert decisions[0]["values"]["rejection_reason"] == "failed_job_interview"


def test_passed_assigned_demo_remains_in_test_and_demo(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    events = []
    appointment = {
        "id": 92,
        "candidate_id": 7,
        "appointment_type": "demo_lesson",
        "status": "in_progress",
        "starts_at": "2099-07-16T05:00:00+00:00",
        "responsible_account_id": 41,
        "responsible_role": "academic_director",
        "candidate_name": "Candidate Seven",
        "topic": "Quadratic equations",
        "version": 1,
    }

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo", "version": 4})
    monkeypatch.setattr(repository, "get_appointment_row", lambda *_args, **_kwargs: appointment)
    monkeypatch.setattr(repository, "insert_demo", lambda *_args, **_kwargs: 109)
    monkeypatch.setattr(repository, "complete_appointment", lambda *_args, **_kwargs: {"id": 92, "version": 2})
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **kwargs: stage_updates.append(kwargs) or {"id": 7})
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append(kwargs["event_type"]))
    monkeypatch.setattr(service, "_sync_system_next_actions", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(notifications, "cancel_demo_reminders", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(notifications, "enqueue_demo_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo"})

    result = service.add_demo(
        _user("academic_director"),
        7,
        {"appointment_id": 92, "result": "passed", "score": 9, "topic": "Quadratic equations"},
    )

    assert result["status"] == "test_and_demo"
    assert stage_updates == []
    assert "candidate.demo_lesson_recorded" in events
    assert "candidate.appointment_completed" in events
    assert "candidate.stage_changed" not in events
    assert conn.commits == 1


def test_academy_supplemental_failure_never_rejects_or_restarts_recruitment(
    monkeypatch,
):
    conn = _DatabaseConnection()
    events = []
    stage_changes = []
    final_decisions = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "teacher_academy",
            "version": 8,
            "subject_id": 3,
            "subject": "Mathematics",
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_subject_test",
        lambda *_args, **_kwargs: 108,
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: stage_changes.append(kwargs),
    )
    monkeypatch.setattr(
        repository,
        "insert_final_decision",
        lambda *_args, **kwargs: final_decisions.append(kwargs),
    )
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )
    monkeypatch.setattr(
        service, "_sync_system_next_actions", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 7, "status": "teacher_academy"},
    )

    result = service.add_subject_test(
        _user(),
        7,
        {"result": "failed", "score": 45, "test_at": "2026-07-20T12:00:00Z"},
    )

    assert result["status"] == "teacher_academy"
    assert stage_changes == []
    assert final_decisions == []
    assert events == [
        (
            "candidate.subject_test_recorded",
            {"record_id": 108, "result": "failed"},
        )
    ]
    assert conn.commits == 1


def test_subject_test_pass_advances_only_after_demo_pass(monkeypatch):
    conn = _DatabaseConnection()
    stage_changes = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "test_and_demo",
            "version": 8,
            "subject_id": 3,
            "subject": "Mathematics",
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_subject_test",
        lambda *_args, **_kwargs: 108,
    )
    monkeypatch.setattr(
        repository,
        "candidate_evaluation_state",
        lambda *_args, **_kwargs: {
            "interview_passed": True,
            "interview_failed": False,
            "demo_passed": True,
            "demo_failed": False,
            "subject_test_passed": True,
            "subject_test_failed": False,
        },
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: stage_changes.append(kwargs) or {"id": 7},
    )
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        service, "_sync_system_next_actions", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 7, "status": "under_review"},
    )

    result = service.add_subject_test(
        _user(),
        7,
        {"result": "passed", "score": 80, "test_at": "2026-07-20T12:00:00Z"},
    )

    assert result["status"] == "under_review"
    assert stage_changes[0]["stage"] == "under_review"
    assert conn.commits == 1


def test_passed_interview_moves_job_interview_to_test_and_demo(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    events = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_args, **_kwargs: {"id": 7, "status": "job_interview", "version": 4})
    monkeypatch.setattr(repository, "insert_interview", lambda *_args, **_kwargs: 110)
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **kwargs: stage_updates.append(kwargs) or {"id": 7, "status": "test_and_demo", "version": 5})
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo"})

    result = service.add_interview(
        _user(),
        7,
        {"result": "passed", "notes": "Candidate passed the interview."},
    )

    assert result["status"] == "test_and_demo"
    assert stage_updates[0]["stage"] == "test_and_demo"
    assert stage_updates[0]["expected_version"] == 4
    assert stage_updates[0]["transition_source"] == "automatic"
    assert events == [
        ("candidate.interview_recorded", {"record_id": 110, "result": "passed"}),
        ("candidate.stage_changed", {"from": "job_interview", "to": "test_and_demo", "reason": "Passed job interview"}),
    ]
    assert conn.commits == 1


def test_demo_notifications_have_versioned_dedupe_keys_and_future_reminders():
    class NotificationConnection:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            return self

    conn = NotificationConnection()
    appointment = {
        "id": 92,
        "candidate_id": 7,
        "appointment_type": "demo_lesson",
        "starts_at": datetime(2099, 7, 16, 5, 0, tzinfo=UTC),
        "responsible_account_id": 41,
        "responsible_role": "head_of_department",
        "candidate_name": "Candidate Seven",
        "topic": "Quadratic equations",
    }

    notifications.enqueue_demo_event(
        conn,
        appointment=appointment,
        event_type="demo_assigned",
        version_token=3,
        include_reminders=True,
    )

    insert_params = [params for sql, params in conn.calls if "INSERT INTO msi_v2.teacher_recruitment_notifications" in sql]
    assert len(insert_params) == 3
    assert {params[-1] for params in insert_params} == {
        "appointment:92:demo_assigned:3",
        "appointment:92:demo_reminder_24h:3",
        "appointment:92:demo_reminder_1h:3",
    }
    assert all(params[6].startswith("/head-of-departments/recruitment") for params in insert_params)


def test_delete_evaluation_is_permanent_and_minimally_audited(monkeypatch):
    conn = _Connection()
    events = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "get_candidate_row",
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "teacher_academy",
            "version": 8,
        },
    )
    monkeypatch.setattr(
        repository,
        "delete_evaluation",
        lambda *_args, **_kwargs: {
            "id": 108,
            "result": "passed",
            "appointment_id": None,
        },
    )
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "_sync_system_next_actions", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7})

    service.delete_evaluation(
        _user(),
        7,
        evaluation_type="interview",
        attempt_id=108,
    )

    assert conn.commits == 1
    assert events == [("candidate.evaluation_deleted", {
        "evaluation_type": "interview",
        "attempt_id": 108,
        "result": "passed",
        "appointment_id": None,
    })]


def test_delete_failed_evaluation_removes_system_rejection_and_recalculates_stage(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    deleted_decisions = []
    events = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_args, **_kwargs: {"id": 7, "status": "rejected", "version": 8})
    monkeypatch.setattr(repository, "get_evaluation_row", lambda *_args, **_kwargs: {"id": 108, "result": "failed", "appointment_id": None, "voided_at": None})
    monkeypatch.setattr(repository, "get_system_decision_for_evaluation", lambda *_args, **_kwargs: {"id": 90, "origin_stage": "job_interview"})
    monkeypatch.setattr(repository, "latest_active_final_decision", lambda *_args, **_kwargs: {"id": 90})
    monkeypatch.setattr(repository, "delete_evaluation", lambda *_args, **_kwargs: {"id": 108, "result": "failed", "appointment_id": None})
    monkeypatch.setattr(repository, "delete_system_final_decision", lambda *_args, **kwargs: deleted_decisions.append(kwargs) or True)
    monkeypatch.setattr(
        repository,
        "candidate_evaluation_state",
        lambda *_args, **_kwargs: {
            "interview_passed": False,
            "interview_failed": False,
            "demo_passed": False,
            "demo_failed": False,
            "subject_test_passed": False,
            "subject_test_failed": False,
        },
    )
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **kwargs: stage_updates.append(kwargs) or {"id": 7})
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "_sync_system_next_actions", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "job_interview"})

    result = service.delete_evaluation(
        _user(),
        7,
        evaluation_type="interview",
        attempt_id=108,
    )

    assert result["status"] == "job_interview"
    assert deleted_decisions[0]["decision_id"] == 90
    assert stage_updates[0]["stage"] == "job_interview"
    assert stage_updates[0]["expected_version"] == 8
    assert [event for event, _detail in events] == ["candidate.evaluation_deleted"]
    assert conn.commits == 1


def test_on_hold_is_not_an_available_stage_or_final_decision():
    with pytest.raises(service.RecruitmentError, match="Unknown candidate stage"):
        service.move_candidate(_user(), 7, stage="on_hold", expected_version=4)

    with pytest.raises(service.RecruitmentError, match="Unknown final decision"):
        service.make_final_decision(_user(), 7, {"decision": "on_hold"})
