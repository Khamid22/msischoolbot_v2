"""Appointment scheduling contracts for the recruitment workspace."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import repository, service
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


def _connection_factory(conn):
    @contextmanager
    def connect():
        yield conn

    return connect


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


def test_hod_demo_evaluator_must_cover_the_candidate_subject(monkeypatch):
    conn = _Connection()
    candidate = {"id": 7, "status": "job_interview", "version": 4, "subject_id": 3}

    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: candidate)
    monkeypatch.setattr(
        repository,
        "responsible_account_row",
        lambda *_args, **_kwargs: {"id": 72, "role": "head_of_department", "status": "active"},
    )
    monkeypatch.setattr(repository, "hod_account_has_subject_scope", lambda *_args, **_kwargs: False)

    with pytest.raises(service.RecruitmentError, match="outside this candidate's subject scope") as raised:
        service.schedule_stage_move(
            _user(),
            7,
            _future_values(stage="test_and_demo", responsible_account_id=72),
        )

    assert raised.value.status_code == 403
    assert conn.commits == 0


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
        lambda *_args, **_kwargs: {"id": 7, "status": "on_hold", "subject_id": 3},
    )

    with pytest.raises(service.RecruitmentError, match="Move the candidate to Job Interview"):
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


def test_on_hold_records_origin_reason_date_and_cancels_appointments(monkeypatch):
    conn = _Connection()
    holds = []
    events = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "get_candidate_row", lambda *_args, **_kwargs: {"id": 7, "status": "job_interview", "application_date": "2026-07-01"})
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **_kwargs: {"id": 7, "status": "on_hold", "version": 5})
    monkeypatch.setattr(repository, "release_open_hold", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(repository, "insert_candidate_hold", lambda *_args, **kwargs: holds.append(kwargs) or 12)
    monkeypatch.setattr(repository, "set_candidate_application_date", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [91])
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **kwargs: events.append((kwargs["event_type"], kwargs["detail"])))
    monkeypatch.setattr(service, "get_candidate", lambda *_args, **_kwargs: {"id": 7, "status": "on_hold"})

    result = service.hold_candidate(
        _user(),
        7,
        expected_version=4,
        reason="Waiting for availability",
        application_date="2026-07-03",
    )

    assert result["status"] == "on_hold"
    assert holds[0]["origin_stage"] == "job_interview"
    assert holds[0]["reason"] == "Waiting for availability"
    assert holds[0]["application_date"] == "2026-07-03"
    assert events[0][1]["cancelled_appointment_ids"] == [91]
    assert conn.commits == 1
