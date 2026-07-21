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
from backend.modules.hr.recruitment.constants import (
    ALL_STAGES,
    PRIMARY_STAGES,
    REJECTION_REASONS,
)
from backend.modules.hr.recruitment.schemas import (
    CandidateCreate,
    CandidateUpdate,
    DemoLessonWrite,
    SubjectTestWrite,
)


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _signed_session(data):
    secret = (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )
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
    assert ALL_STAGES == {
        *PRIMARY_STAGES,
        "rejected",
        "candidate_withdrew",
        "trash_bin",
    }
    assert "other" in REJECTION_REASONS
    assert "missing_or_invalid_documents" in REJECTION_REASONS


def test_teacher_handoff_repository_reads_only_canonical_tables_and_sorts_server_side():
    class Result:
        def __init__(self, rows):
            self.rows = rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

        def fetchall(self):
            return self.rows

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            return Result([{"total": 0}]) if "count(*) AS total" in sql else Result([])

    academy_conn = Connection()
    assert repository.list_teacher_handoff_rows(
        academy_conn,
        kind="teacher_academy",
        search="Math",
        subject_id=4,
    ) == ([], 0)
    academy_sql = "\n".join(sql for sql, _params in academy_conn.calls)
    assert "FROM msi_v2.academy_teachers academy" in academy_sql
    assert "academy.promoted_teacher_id IS NULL" in academy_sql
    assert "candidate.status = 'teacher_academy'" not in academy_sql
    assert "UNION ALL" not in academy_sql
    assert "academy.created_at AT TIME ZONE 'Asia/Tashkent'" in academy_sql
    assert "FROM msi_v2.academy_lesson_assignments assignment" in academy_sql
    assert "FROM msi_v2.academy_assessments assessment" in academy_sql
    assert "%s = ANY(record.subject_ids)" in academy_sql
    assert "record.average_score DESC NULLS LAST" in academy_sql
    assert "lower(record.full_name)" in academy_sql
    assert academy_conn.calls[0][1] == ("%Math%", "%Math%", "%Math%", 4)

    active_conn = Connection()
    assert repository.list_teacher_handoff_rows(
        active_conn,
        kind="active_teacher",
    ) == ([], 0)
    active_sql = "\n".join(sql for sql, _params in active_conn.calls)
    assert "FROM msi_v2.teachers teacher" in active_sql
    assert "teacher.status = 'active'" in active_sql
    assert "FROM msi_v2.teacher_subjects teacher_subject_link" in active_sql
    assert "candidate.status = 'active_teacher'" not in active_sql
    assert "FROM msi_v2.teacher_candidates candidate" not in active_sql
    assert "record.sort_at DESC NULLS LAST" in active_sql


def test_candidate_training_repository_returns_the_canonical_hod_assessment_details():
    class Result:
        def fetchall(self):
            return []

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            return Result()

    conn = Connection()
    assert repository.list_academy_lifecycle_assessment_rows(conn, 9) == []
    sql, params = conn.calls[0]
    assert params == (9,)
    assert "assessment.assessment_datetime::text" in sql
    assert "assessment.section_feedback" in sql
    assert "assessment.teacher_guidance_compliance_score" in sql
    assert "assessment.engagement_technique_score" in sql
    assert "assessment.strengths" in sql
    assert "assessment.areas_for_improvement" in sql
    assert "assessment.final_recommendation" in sql
    assert (
        "(academy.created_at AT TIME ZONE 'Asia/Tashkent')::date::text"
        in repository._CANDIDATE_COLUMNS
    )


def test_teacher_handoff_service_normalizes_canonical_records_and_fails_closed(
    monkeypatch,
):
    @contextmanager
    def connect():
        yield object()

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "list_teacher_handoff_rows",
        lambda *_args, **_kwargs: (
            [
                {
                    "kind": "teacher_academy",
                    "record_id": 17,
                    "recruitment_candidate_id": 330,
                    "full_name": "Existing Math Teacher",
                    "position": "IGCSE Math Teacher",
                    "subject": "Mathematics",
                    "status": "in_training",
                    "onboarding_status": "complete",
                    "joined_at": "2026-07-17T10:00:00+00:00",
                    "added_on": "2026-07-17",
                    "assigned_count": 12,
                    "evaluated_count": 12,
                    "passed_count": 12,
                    "failed_count": 0,
                    "average_score": 7.24,
                }
            ],
            1,
        ),
    )
    result = service.list_teacher_handoffs(
        _user(),
        kind="teacher_academy",
        search="Math",
        subject_id=4,
    )
    assert result["total"] == 1
    assert result["items"][0]["record_id"] == 17
    assert result["items"][0]["recruitment_candidate_id"] == 330
    assert result["items"][0]["position"] == "IGCSE Math Teacher"
    assert result["items"][0]["added_on"] == "2026-07-17"
    assert result["items"][0]["assigned_count"] == 12
    assert result["items"][0]["evaluated_count"] == 12
    assert result["items"][0]["passed_count"] == 12
    assert result["items"][0]["failed_count"] == 0
    assert result["items"][0]["average_score"] == 7.2
    assert result["items"][0]["academy_completed"] is True
    assert result["items"][0]["can_delete"] is True
    assert result["items"][0]["can_reject"] is True

    academic_result = service.list_teacher_handoffs(
        _user("academic_director"),
        kind="teacher_academy",
        sort="lessons",
    )
    assert academic_result["total"] == 1
    assert academic_result["items"][0]["can_delete"] is True
    assert academic_result["items"][0]["can_reject"] is True

    with pytest.raises(service.RecruitmentError, match="Academic Director"):
        service.list_teacher_handoffs(
            _user("head_of_department"),
            kind="teacher_academy",
        )


def test_minimal_candidate_and_blank_optional_values_validate():
    candidate = CandidateCreate.model_validate(
        {"full_name": "  Ada Teacher  ", "application_date": ""}
    )
    assert candidate.full_name == "Ada Teacher"
    assert candidate.application_date is None
    assert (
        CandidateCreate.model_validate(
            {"full_name": "Ada", "position_option_id": 3}
        ).position_option_id
        == 3
    )

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
        service.move_candidate(_user(), 1, stage="active_teacher", expected_version=1)
    with pytest.raises(service.RecruitmentError, match="Only CEO"):
        service.make_final_decision(
            _user(), 1, {"decision": "active_teacher", "approval_id": 1}
        )
    with pytest.raises(service.RecruitmentError, match="Only HR"):
        service.make_final_decision(
            _user("ceo"), 1, {"decision": "teacher_academy"}
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
    monkeypatch.setattr(
        repository, "revoke_open_approvals", lambda *_args, **_kwargs: [21]
    )
    monkeypatch.setattr(
        repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [31]
    )
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 7, "status": "trash_bin"},
    )

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
            {
                "from": "job_interview",
                "to": "trash_bin",
                "reason": "Pipeline trash drop",
            },
        ),
    ]


def test_non_terminal_stage_move_keeps_scheduled_appointment(monkeypatch):
    """Dragging a card between board stages must not destroy a booking."""

    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()
    events = []
    cancel_calls = []

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
    monkeypatch.setattr(repository, "revoke_open_approvals", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        repository,
        "cancel_scheduled_appointments",
        lambda *_args, **_kwargs: cancel_calls.append(_kwargs) or [],
    )
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **kwargs: events.append(kwargs["event_type"]),
    )
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo"},
    )

    candidate = service.move_candidate(
        _user(),
        7,
        stage="test_and_demo",
        expected_version=4,
        reason="Pipeline move",
    )

    assert candidate["status"] == "test_and_demo"
    # The interview booking is untouched: no cancellation call, no audit event.
    assert cancel_calls == []
    assert "candidate.appointments_cancelled" not in events


def test_candidate_audit_insert_serializes_detail_json():
    """insert_audit must serialize detail to JSON (regression: missing import)."""

    from backend.modules.hr.recruitment.candidates import (
        repository as candidates_repository,
    )

    captured: dict[str, object] = {}

    class _Conn:
        def execute(self, _sql, params):
            captured["params"] = params

    candidates_repository.insert_audit(
        _Conn(),
        candidate_id=7,
        event_type="candidate.moved",
        detail={"from": "job_interview", "to": "test_and_demo"},
        actor_account_id=1,
        actor_staff_id=None,
        now="2026-07-20T00:00:00Z",
    )

    assert json.loads(captured["params"][4]) == {
        "from": "job_interview",
        "to": "test_and_demo",
    }


def test_candidate_creation_anchors_new_stage_sla_to_application_date():
    """The SLA clock must start from application_date, not the row's created_at."""

    from backend.modules.hr.recruitment.candidates import (
        repository as candidates_repository,
    )

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            return Result([{"id": 42}])

    conn = Connection()
    candidate_id = candidates_repository.insert_candidate(
        conn,
        values={"full_name": "Jane Doe", "application_date": "2026-07-17"},
        now="2026-07-21T10:00:00Z",
        actor_account_id=10,
    )

    assert candidate_id == 42
    sql, params = conn.calls[0]
    assert (
        "COALESCE(candidate.application_date::timestamp AT TIME ZONE 'Asia/Tashkent', %s::timestamptz)"
        in sql
    )
    assert params[7] == "2026-07-17"


def test_hr_recovers_closed_candidate_to_recorded_pipeline_stage(monkeypatch):
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
        lambda *_args, **_kwargs: {
            "id": 7,
            "status": "rejected",
            "version": 5,
            "restore_stage": "test_and_demo",
        },
    )
    monkeypatch.setattr(
        repository, "void_latest_closed_decision", lambda *_args, **_kwargs: 91
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **kwargs: {
            "id": kwargs["candidate_id"],
            "status": kwargs["stage"],
        },
    )
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
        lambda *_args, **_kwargs: {"id": 7, "status": "test_and_demo"},
    )

    result = service.restore_closed_candidate(_user(), 7, expected_version=5)

    assert result["status"] == "test_and_demo"
    assert conn.commits == 1
    assert events == [
        (
            "candidate.recovered",
            {"from": "rejected", "to": "test_and_demo", "voided_decision_id": 91},
        )
    ]


def test_permanent_candidate_delete_requires_closed_unlinked_profile(monkeypatch):
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()

    @contextmanager
    def connect():
        yield conn

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 7,
            "full_name": "Closed Candidate",
            "status": "trash_bin",
            "version": 4,
            "academy_teacher_id": None,
            "active_teacher_id": None,
        },
    )
    monkeypatch.setattr(repository, "list_document_rows", lambda *_args, **_kwargs: [])
    purged_academy_candidate_ids = []

    def purge_academy(_conn, *, candidate_id):
        purged_academy_candidate_ids.append(candidate_id)
        return True

    monkeypatch.setattr(
        service.candidate_service,
        "purge_closed_academy_handoff",
        purge_academy,
    )
    monkeypatch.setattr(
        repository, "delete_closed_candidate", lambda *_args, **_kwargs: True
    )

    result = service.permanently_delete_candidate(
        _user(),
        7,
        expected_version=4,
        confirmation="PERMANENTLY DELETE",
    )
    assert result == {"deleted_candidate_id": 7, "deleted_name": "Closed Candidate"}
    assert conn.commits == 1

    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 8,
            "full_name": "Linked Candidate",
            "status": "rejected",
            "version": 2,
            "academy_teacher_id": 12,
            "academy_status": "in_training",
            "academy_promoted_teacher_id": None,
            "active_teacher_id": None,
            "active_teacher_status": None,
        },
    )
    with pytest.raises(service.RecruitmentError, match="open Teacher Academy"):
        service.permanently_delete_candidate(
            _user(),
            8,
            expected_version=2,
            confirmation="PERMANENTLY DELETE",
        )

    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 9,
            "full_name": "Closed Academy Candidate",
            "status": "trash_bin",
            "version": 3,
            "academy_teacher_id": 13,
            "academy_status": "trash_bin",
            "academy_promoted_teacher_id": None,
            "active_teacher_id": 21,
            "active_teacher_status": "academy",
        },
    )
    result = service.permanently_delete_candidate(
        _user(),
        9,
        expected_version=3,
        confirmation="PERMANENTLY DELETE",
    )
    assert result == {
        "deleted_candidate_id": 9,
        "deleted_name": "Closed Academy Candidate",
    }
    assert purged_academy_candidate_ids == [9]
    assert conn.commits == 2

    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args, **_kwargs: {
            "id": 10,
            "full_name": "Open Active Teacher",
            "status": "trash_bin",
            "version": 2,
            "academy_teacher_id": None,
            "academy_status": None,
            "academy_promoted_teacher_id": None,
            "active_teacher_id": 22,
            "active_teacher_status": "active",
        },
    )
    with pytest.raises(service.RecruitmentError, match="open Active Teacher"):
        service.permanently_delete_candidate(
            _user(),
            10,
            expected_version=2,
            confirmation="PERMANENTLY DELETE",
        )


def test_empty_trash_bin_accepts_closed_teacher_handoff_links(monkeypatch):
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()

    @contextmanager
    def connect():
        yield conn

    deleted_candidate_ids = []
    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "list_trash_candidates_for_purge",
        lambda *_args, **_kwargs: [
            {
                "id": 9,
                "full_name": "Closed Academy Candidate",
                "status": "trash_bin",
                "version": 3,
                "academy_teacher_id": 13,
                "academy_status": "trash_bin",
                "academy_promoted_teacher_id": None,
                "active_teacher_id": 21,
                "active_teacher_status": "academy",
            }
        ],
    )
    monkeypatch.setattr(repository, "list_document_rows", lambda *_args, **_kwargs: [])
    purged_academy_candidate_ids = []
    monkeypatch.setattr(
        service.candidate_service,
        "purge_closed_academy_handoff",
        lambda _conn, *, candidate_id: (
            purged_academy_candidate_ids.append(candidate_id) or True
        ),
    )

    def delete_candidate(_conn, *, candidate_id, expected_version):
        deleted_candidate_ids.append((candidate_id, expected_version))
        return True

    monkeypatch.setattr(repository, "delete_closed_candidate", delete_candidate)

    result = service.empty_trash_bin(
        _user(), confirmation="EMPTY TRASH BIN"
    )

    assert result == {"deleted_count": 1}
    assert deleted_candidate_ids == [(9, 3)]
    assert purged_academy_candidate_ids == [9]
    assert conn.commits == 1


def test_recruitment_api_is_role_scoped_and_hr_pipeline_is_available(
    client, monkeypatch
):
    monkeypatch.setattr(
        service,
        "list_pipeline",
        lambda user, **_filters: {
            "stages": {},
            "counts": {},
            "total": 0,
            "role": user.role,
        },
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


def test_hod_recruitment_is_limited_to_assigned_work_without_pipeline(
    client, monkeypatch
):
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


def test_appointment_apis_allow_scoped_reads_but_only_hr_or_ceo_management(
    client, monkeypatch
):
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
        lambda user: {
            "items": [],
            "sources": [],
            "rejection_reasons": [],
            "role": user.role,
        },
    )
    monkeypatch.setattr(
        service,
        "add_setting",
        lambda user, **values: {
            "id": 9,
            "category": values["category"],
            "label": values["label"],
        },
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
    assert (
        client.delete("/api/v1/recruitment/settings/9", headers=XHR).status_code == 200
    )

    _set_session(client, "ceo", account_id=11, staff_id=21)
    response = client.get("/api/v1/recruitment/settings", headers=XHR)
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "ceo"
    assert (
        client.post(
            "/api/v1/recruitment/settings",
            headers=XHR,
            json={"category": "source", "label": "Denied"},
        ).status_code
        == 403
    )


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
    monkeypatch.setattr(
        repository,
        "recruitment_setting_by_label_or_value",
        lambda *_args, **_kwargs: None,
    )
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
        lambda *_args, **kwargs: events.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
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


def test_hr_setting_rename_keeps_value_and_audits_old_and_new_label(monkeypatch):
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    conn = Connection()
    events = []

    @contextmanager
    def connect():
        yield conn

    existing = {
        "id": 7,
        "category": "position",
        "value": "igcse_math_teacher",
        "label": "IGCSE Math Teacher",
        "parent_id": None,
        "is_active": True,
        "is_system": False,
    }

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository, "recruitment_setting_by_id", lambda *_args, **_kwargs: existing
    )
    monkeypatch.setattr(
        repository,
        "recruitment_setting_by_label_or_value",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        repository,
        "rename_recruitment_setting",
        lambda *_args, **kwargs: {
            **existing,
            "label": kwargs["label"],
            "sort_order": 10,
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_recruitment_setting_audit",
        lambda *_args, **kwargs: events.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )

    setting = service.rename_setting(_user(), 7, label="  IGCSE Mathematics Teacher  ")

    assert setting["label"] == "IGCSE Mathematics Teacher"
    assert setting["value"] == "igcse_math_teacher"
    assert conn.commits == 1
    assert events == [
        (
            "recruitment.setting_renamed",
            {
                "category": "position",
                "value": "igcse_math_teacher",
                "from_label": "IGCSE Math Teacher",
                "to_label": "IGCSE Mathematics Teacher",
            },
        )
    ]


def test_hr_setting_rename_rejects_system_rows_and_duplicate_labels(monkeypatch):
    @contextmanager
    def connect():
        yield object()

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "recruitment_setting_by_id",
        lambda *_args, **_kwargs: {
            "id": 1,
            "category": "rejection_reason",
            "value": "failed_job_interview",
            "label": "Failed job interview",
            "parent_id": None,
            "is_active": True,
            "is_system": True,
        },
    )
    with pytest.raises(service.RecruitmentError, match="cannot be renamed"):
        service.rename_setting(_user(), 1, label="New name")

    monkeypatch.setattr(
        repository,
        "recruitment_setting_by_id",
        lambda *_args, **_kwargs: {
            "id": 7,
            "category": "position",
            "value": "igcse_math_teacher",
            "label": "IGCSE Math Teacher",
            "parent_id": None,
            "is_active": True,
            "is_system": False,
        },
    )
    monkeypatch.setattr(
        repository,
        "recruitment_setting_by_label_or_value",
        lambda *_args, **_kwargs: {"id": 9, "is_active": True},
    )
    with pytest.raises(service.RecruitmentError, match="already exists"):
        service.rename_setting(_user(), 7, label="IGCSE Physics Teacher")


def test_hr_setting_restore_reactivates_and_audits(monkeypatch):
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
        "recruitment_setting_by_id",
        lambda *_args, **_kwargs: {
            "id": 7,
            "category": "position",
            "value": "igcse_math_teacher",
            "label": "IGCSE Math Teacher",
            "parent_id": None,
            "is_active": False,
        },
    )
    monkeypatch.setattr(
        repository,
        "save_recruitment_setting",
        lambda *_args, **kwargs: {
            "id": 7,
            "category": "position",
            "value": "igcse_math_teacher",
            "label": "IGCSE Math Teacher",
            "is_active": True,
            "sort_order": 10,
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_recruitment_setting_audit",
        lambda *_args, **kwargs: events.append(
            (kwargs["event_type"], kwargs["detail"])
        ),
    )

    setting = service.restore_setting(_user(), 7)

    assert setting["is_active"] is True
    assert conn.commits == 1
    assert events == [
        (
            "recruitment.setting_reactivated",
            {
                "category": "position",
                "value": "igcse_math_teacher",
                "label": "IGCSE Math Teacher",
            },
        )
    ]


def test_hr_setting_restore_blocks_already_active_and_orphaned_subsource(monkeypatch):
    @contextmanager
    def connect():
        yield object()

    monkeypatch.setattr(service, "connect_auth_db", connect)
    monkeypatch.setattr(
        repository,
        "recruitment_setting_by_id",
        lambda *_args, **_kwargs: {
            "id": 7,
            "category": "position",
            "is_active": True,
            "parent_id": None,
        },
    )
    with pytest.raises(service.RecruitmentError, match="already active"):
        service.restore_setting(_user(), 7)

    def by_id(_conn, setting_id):
        if setting_id == 8:
            return {
                "id": 8,
                "category": "subsource",
                "is_active": False,
                "parent_id": 3,
            }
        return {"id": 3, "category": "source", "is_active": False}

    monkeypatch.setattr(repository, "recruitment_setting_by_id", by_id)
    with pytest.raises(service.RecruitmentError, match="Restore the source"):
        service.restore_setting(_user(), 8)


def test_recruitment_settings_listing_includes_inactive_rows_with_usage_counts(
    monkeypatch,
):
    @contextmanager
    def connect():
        yield object()

    monkeypatch.setattr(service, "connect_auth_db", connect)
    captured_kwargs = {}

    def list_rows(_conn, **kwargs):
        captured_kwargs.update(kwargs)
        return [
            {
                "id": 1,
                "category": "position",
                "value": "igcse_math_teacher",
                "label": "IGCSE Math Teacher",
                "parent_id": None,
                "is_active": True,
                "sort_order": 10,
                "is_system": False,
                "is_legacy": False,
            },
            {
                "id": 2,
                "category": "position",
                "value": "igcse_biology_teacher",
                "label": "IGCSE Biology Teacher",
                "parent_id": None,
                "is_active": False,
                "sort_order": 20,
                "is_system": False,
                "is_legacy": False,
            },
        ]

    monkeypatch.setattr(repository, "list_recruitment_setting_rows", list_rows)
    monkeypatch.setattr(repository, "list_sla_rule_rows", lambda *_a, **_k: [])
    monkeypatch.setattr(
        repository, "recruitment_setting_usage_counts", lambda *_a, **_k: {1: 4}
    )

    result = service.list_settings(_user())

    assert captured_kwargs == {"include_inactive": True}
    by_id = {item["id"]: item for item in result["items"]}
    assert by_id[1]["usage_count"] == 4
    assert by_id[2]["usage_count"] == 0
    assert by_id[2]["is_active"] is False


def test_internal_operations_recruitment_pages_are_not_registered(app):
    paths = {getattr(route, "path", "") for route in app.routes}
    for path in (
        "/internal/operations/recruitment",
        "/internal/operations/recruitment/pipeline",
        "/internal/operations/recruitment/candidates",
    ):
        assert path not in paths


def test_migration_preserves_candidates_and_normalizes_history():
    source = Path(
        "database/alembic/versions/0013_teacher_recruitment_mvp.py"
    ).read_text()
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
    source = Path(
        "database/alembic/versions/0014_hr_access_decision_queue.py"
    ).read_text()

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


def test_sla_anchor_backfill_migration_only_touches_original_open_creation_rows():
    source = Path(
        "database/alembic/versions/0032_backfill_new_candidate_sla_anchor.py"
    ).read_text()
    upgrade_source = source.split("def downgrade", 1)[0]

    # Only the original creation entry for a candidate still open in that
    # stage may be corrected -- never a restored/moved-back stage entry.
    assert "h.stage = 'new_candidate'" in upgrade_source
    assert "h.exited_at IS NULL" in upgrade_source
    assert "h.transition_source = 'manual'" in upgrade_source
    assert "h.comment = 'Candidate created.'" in upgrade_source
    assert "c.status = 'new_candidate'" in upgrade_source
    assert "c.application_date IS NOT NULL" in upgrade_source
    # No-op when already correct, and no destructive statements.
    assert "history.entered_at <> anchor.new_entered_at" in upgrade_source
    assert "DELETE FROM" not in upgrade_source
    assert "DROP TABLE" not in upgrade_source


def test_recruitment_settings_migration_seeds_editable_taxonomies_without_candidate_loss():
    source = Path("database/alembic/versions/0016_recruitment_settings.py").read_text()
    upgrade_source = source.split("def downgrade", 1)[0]

    assert (
        "CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_settings"
        in upgrade_source
    )
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
    appointment_source = Path(
        "backend/modules/hr/recruitment/appointments/repository.py"
    ).read_text()
    candidate_source = Path(
        "backend/modules/hr/recruitment/candidates/read_repository.py"
    ).read_text()

    assert (
        "else:\n        clauses.append(\"candidate.status <> 'trash_bin'\")"
        in appointment_source
    )
    assert (
        candidate_source.count(
            "WHERE candidate.status <> 'trash_bin' AND ({visibility})"
        )
        == 2
    )


def test_recruitment_document_urls_never_use_public_resource_url():
    source = Path("backend/platform/storage/r2.py").read_text()
    private_function = source.split("def build_private_candidate_document_url", 1)[1]
    private_function = private_function.split("\ndef ", 1)[0]
    assert "generate_presigned_url" in private_function
    assert "public_base_url" not in private_function


def test_deleted_legacy_candidate_endpoints_and_lesson_practice_stay_absent(app):
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/admin/teacher-candidates" not in paths
    assert not Path(
        "frontend/src/features/teacher-academy/TrainingEvaluationModal.tsx"
    ).exists()
    assert not Path("frontend/src/features/hr/recruitment/PromoteModal.tsx").exists()
