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

    def execute(self, _query, params):
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
    assert conn.params[11] == "restored"


def _future_values(**overrides):
    return {
        "stage": "job_interview",
        "expected_version": 4,
        "starts_at": datetime(2099, 7, 16, 10, 0),
        "duration_minutes": 30,
        "responsible_account_id": None,
        "appointment_format": "Online",
        "location_or_link": "https://meet.example/interview",
        "topic": "",
        "note": "First interview",
        "allow_conflict": False,
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


def test_api_allows_server_default_duration_and_rejects_out_of_range_values():
    payload = AppointmentCreate.model_validate(
        {"appointment_type": "job_interview", "starts_at": "2099-07-16T10:00:00"}
    )
    assert payload.duration_minutes is None

    with pytest.raises(ValueError):
        AppointmentCreate.model_validate(
            {
                "appointment_type": "job_interview",
                "starts_at": "2099-07-16T10:00:00",
                "duration_minutes": 241,
            }
        )


def test_past_appointment_requires_hr_historical_result_and_skips_future_requirements(monkeypatch):
    conn = _Connection()
    conflicts = []
    monkeypatch.setattr(
        repository,
        "list_appointment_conflicts",
        lambda *_args, **_kwargs: conflicts.append(True) or [],
    )

    prepared = service._prepare_appointment(
        conn,
        user=_user(),
        candidate={"id": 7, "subject_id": 3},
        appointment_type="demo_lesson",
        values={
            "starts_at": datetime(2020, 7, 16, 10, 0),
            "historical_result": "passed",
        },
    )

    assert prepared["is_historical"] is True
    assert prepared["historical_result"] == "passed"
    assert prepared["responsible_account_id"] == 41
    assert prepared["appointment_format"] == ""
    assert conflicts == []

    with pytest.raises(service.RecruitmentError, match="Only HR Manager"):
        service._prepare_appointment(
            conn,
            user=_user("ceo"),
            candidate={"id": 7, "subject_id": 3},
            appointment_type="job_interview",
            values={
                "starts_at": datetime(2020, 7, 16, 10, 0),
                "historical_result": "passed",
            },
        )


def test_historical_interview_is_completed_and_advances_atomically(monkeypatch):
    conn = _Connection()
    candidate = {
        "id": 7,
        "status": "job_interview",
        "version": 4,
        "subject_id": 3,
        "subject": "Mathematics",
    }
    appointments = []
    evaluations = []
    movements = []
    notifications_sent = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(service, "_lock_candidate", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(repository, "active_appointment_for_type", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        repository,
        "insert_appointment",
        lambda *_args, **kwargs: appointments.append(kwargs["values"]) or 91,
    )
    monkeypatch.setattr(
        repository,
        "complete_historical_appointment",
        lambda *_args, **kwargs: appointments.append(kwargs) or {"id": 91, "version": 2},
    )
    monkeypatch.setattr(
        repository,
        "insert_interview",
        lambda *_args, **kwargs: evaluations.append(kwargs["values"]) or 108,
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: movements.append(kwargs) or {"id": 7, "version": 5},
    )
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        notifications,
        "enqueue_demo_event",
        lambda *_args, **_kwargs: notifications_sent.append(True),
    )
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "appointments": []})

    service.create_appointment(
        _user(),
        7,
        {
            "appointment_type": "job_interview",
            "starts_at": datetime(2020, 7, 16, 10, 0),
            "historical_result": "passed",
        },
    )

    assert conn.commits == 1
    assert evaluations == [
        {
            "appointment_id": 91,
            "interview_at": "2020-07-16T05:00:00+00:00",
            "interviewer_account_id": 41,
            "interview_format": "",
            "notes": "",
            "result": "passed",
        }
    ]
    assert movements[0]["stage"] == "test_and_demo"
    assert movements[0]["transition_source"] == "restored"
    assert notifications_sent == []


def test_failed_historical_demo_uses_existing_automatic_rejection_shape(monkeypatch):
    conn = _Connection()
    candidate = {
        "id": 7,
        "status": "test_and_demo",
        "version": 4,
        "subject_id": 3,
        "subject": "Mathematics",
    }
    movements = []
    decisions = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(service, "_lock_candidate", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(repository, "active_appointment_for_type", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "insert_appointment", lambda *_args, **_kwargs: 92)
    monkeypatch.setattr(
        repository,
        "complete_historical_appointment",
        lambda *_args, **_kwargs: {"id": 92, "version": 2},
    )
    monkeypatch.setattr(repository, "insert_demo", lambda *_args, **_kwargs: 109)
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(repository, "revoke_open_approvals", lambda *_args, **_kwargs: [55])
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: movements.append(kwargs) or {"id": 7, "version": 5},
    )
    monkeypatch.setattr(
        repository,
        "insert_final_decision",
        lambda *_args, **kwargs: decisions.append(kwargs["values"]) or 66,
    )
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "appointments": []})

    service.create_appointment(
        _user(),
        7,
        {
            "appointment_type": "demo_lesson",
            "starts_at": datetime(2020, 7, 16, 10, 0),
            "historical_result": "failed",
        },
    )

    assert conn.commits == 1
    assert movements[0]["stage"] == "rejected"
    assert movements[0]["transition_source"] == "restored"
    assert decisions[0]["rejection_reason"] == "failed_demo_lesson"
    assert decisions[0]["origin_stage"] == "test_and_demo"
    assert decisions[0]["source_evaluation_type"] == "demo"
    assert decisions[0]["source_evaluation_id"] == 109


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
    assert inserted[0]["values"]["ends_at"] == "2099-07-16T05:30:00+00:00"
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
            duration_minutes=None,
            responsible_account_id=72,
            topic="Quadratic equations",
        ),
    )

    assert assignments[0]["assignee_account_id"] == 72
    assert assignments[0]["subject_id"] == 3
    assert "candidate.assignment_ensured" in [event for event, _detail in events]


def test_overlap_returns_structured_conflict_before_stage_change(monkeypatch):
    conn = _Connection()
    moved = []
    candidate = {"id": 7, "status": "new_candidate", "version": 4, "subject_id": 3}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(
        repository,
        "responsible_account_row",
        lambda *_args, **_kwargs: {"id": 41, "role": "hr_manager", "status": "active"},
    )
    monkeypatch.setattr(
        repository,
        "list_appointment_conflicts",
        lambda *_args, **_kwargs: [
            {
                "id": 80,
                "candidate_id": 6,
                "candidate_name": "Existing candidate",
                "appointment_type": "job_interview",
                "starts_at": "2099-07-16T05:00:00+00:00",
                "ends_at": "2099-07-16T05:30:00+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: moved.append(kwargs),
    )

    with pytest.raises(service.RecruitmentError) as raised:
        service.schedule_stage_move(
            _user(),
            7,
            _future_values(responsible_account_id=41),
        )

    assert raised.value.status_code == 409
    assert raised.value.code == "appointment_conflict"
    assert raised.value.details[0]["candidate_name"] == "Existing candidate"
    assert moved == []
    assert conn.commits == 0


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
            "status": "scheduled",
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
        _user("academic_director"),
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


def test_passed_assigned_demo_moves_test_and_demo_to_under_review(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    events = []
    appointment = {
        "id": 92,
        "candidate_id": 7,
        "appointment_type": "demo_lesson",
        "status": "scheduled",
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
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append(kwargs["event_type"]))
    monkeypatch.setattr(notifications, "cancel_demo_reminders", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(notifications, "enqueue_demo_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "under_review"})

    result = service.add_demo(
        _user("academic_director"),
        7,
        {"appointment_id": 92, "result": "passed", "score": 9, "topic": "Quadratic equations"},
    )

    assert result["status"] == "under_review"
    assert stage_updates[0]["stage"] == "under_review"
    assert stage_updates[0]["expected_version"] == 4
    assert "candidate.demo_lesson_recorded" in events
    assert "candidate.appointment_completed" in events
    assert "candidate.stage_changed" in events
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


def test_void_evaluation_is_audited_without_deleting_history(monkeypatch):
    conn = _Connection()
    events = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: {"id": 7})
    monkeypatch.setattr(repository, "void_evaluation", lambda *_args, **_kwargs: {"id": 108})
    monkeypatch.setattr(repository, "touch_candidate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7})

    service.void_evaluation(
        _user(),
        7,
        evaluation_type="interview",
        attempt_id=108,
        reason="Entered for the wrong candidate",
    )

    assert conn.commits == 1
    assert events == [("candidate.evaluation_voided", {
        "evaluation_type": "interview",
        "attempt_id": 108,
        "reason": "Entered for the wrong candidate",
    })]


def test_void_failed_evaluation_restores_origin_when_system_rejection_is_latest(monkeypatch):
    conn = _DatabaseConnection()
    stage_updates = []
    voided_decisions = []
    events = []

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_args, **_kwargs: {"id": 7, "status": "rejected", "version": 8})
    monkeypatch.setattr(repository, "get_evaluation_row", lambda *_args, **_kwargs: {"id": 108, "result": "failed", "voided_at": None})
    monkeypatch.setattr(repository, "get_system_decision_for_evaluation", lambda *_args, **_kwargs: {"id": 90, "origin_stage": "job_interview"})
    monkeypatch.setattr(repository, "latest_active_final_decision", lambda *_args, **_kwargs: {"id": 90})
    monkeypatch.setattr(repository, "void_evaluation", lambda *_args, **_kwargs: {"id": 108})
    monkeypatch.setattr(repository, "void_system_final_decision", lambda *_args, **kwargs: voided_decisions.append(kwargs) or True)
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **kwargs: stage_updates.append(kwargs) or {"id": 7})
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "job_interview"})

    result = service.void_evaluation(
        _user(),
        7,
        evaluation_type="interview",
        attempt_id=108,
        reason="Result entered for the wrong candidate",
    )

    assert result["status"] == "job_interview"
    assert voided_decisions[0]["decision_id"] == 90
    assert stage_updates[0]["stage"] == "job_interview"
    assert stage_updates[0]["expected_version"] == 8
    assert [event for event, _detail in events] == [
        "candidate.system_rejection_voided",
        "candidate.stage_changed",
        "candidate.evaluation_voided",
    ]
    assert conn.commits == 1


def test_on_hold_is_not_an_available_stage_or_final_decision():
    with pytest.raises(service.RecruitmentError, match="Unknown candidate stage"):
        service.move_candidate(_user(), 7, stage="on_hold", expected_version=4)

    with pytest.raises(service.RecruitmentError, match="Unknown final decision"):
        service.make_final_decision(_user(), 7, {"decision": "on_hold"})
