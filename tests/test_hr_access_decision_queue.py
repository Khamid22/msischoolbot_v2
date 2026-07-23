"""Access and transaction contracts for standalone HR recruitment decisions."""

from __future__ import annotations

import json
import os
from base64 import b64encode
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from itsdangerous import TimestampSigner

from backend.core.access import CurrentUser
from backend.modules.hr.recruitment import handoff_api, policies, repository, service
from backend.modules.hr.recruitment.decisions import service as decision_service
from backend.modules.hr.recruitment.handoffs import intake_repository


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _signed_session(data):
    secret = (
        os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )
    return TimestampSigner(secret).sign(b64encode(json.dumps(data).encode())).decode()


def _set_session(client, role: str, **extra):
    client.cookies.set(
        "session",
        _signed_session(
            {
                "auth_role": role,
                "auth_login": f"{role}@test",
                "account_id": 41,
                "staff_id": 51,
                **extra,
            }
        ),
    )


def _user(role: str = "academic_director") -> CurrentUser:
    return CurrentUser(
        login=f"{role}@test",
        role=role,
        account_id=41,
        staff_id=51,
    )


class _Connection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_teacher_academy_promotion_requires_a_canonical_subject(monkeypatch):
    conn = _Connection()
    candidate = {
        "id": 8,
        "full_name": "Ada Teacher",
        "status": "under_review",
        "version": 4,
        "subject_id": None,
        "academy_teacher_id": None,
        "active_teacher_id": None,
    }
    monkeypatch.setattr(
        decision_service.repository,
        "candidate_evaluation_state",
        lambda *_args, **_kwargs: {
            "interview_passed": True,
            "demo_passed": True,
            "subject_test_passed": True,
        },
    )
    dependencies = decision_service.DecisionDependencies(
        connect=_connection_factory(conn),
        lock_candidate=lambda *_args, **_kwargs: candidate,
        get_candidate=lambda *_args, **_kwargs: candidate,
        sync_next_actions=lambda *_args, **_kwargs: None,
        notify_cancelled_appointments=lambda *_args, **_kwargs: None,
        provision_academy_account=lambda *_args, **_kwargs: None,
    )

    with pytest.raises(
        service.RecruitmentError,
        match="Set the candidate subject before adding them to Teacher Academy",
    ) as exc:
        decision_service.make_final_decision(
            _user("hr_manager"),
            8,
            {"decision": "teacher_academy"},
            dependencies=dependencies,
        )

    assert exc.value.status_code == 409
    assert conn.commits == 0


def test_teacher_academy_promotion_requires_an_active_subject_curriculum(monkeypatch):
    conn = _Connection()
    candidate = {
        "id": 8,
        "full_name": "Ada Teacher",
        "status": "under_review",
        "version": 4,
        "subject_id": 3,
        "academy_teacher_id": None,
        "active_teacher_id": None,
    }
    monkeypatch.setattr(
        decision_service.repository,
        "candidate_evaluation_state",
        lambda *_args, **_kwargs: {
            "interview_passed": True,
            "demo_passed": True,
            "subject_test_passed": True,
        },
    )
    monkeypatch.setattr(
        decision_service.repository,
        "active_subject_program_id",
        lambda *_args, **_kwargs: None,
    )
    dependencies = decision_service.DecisionDependencies(
        connect=_connection_factory(conn),
        lock_candidate=lambda *_args, **_kwargs: candidate,
        get_candidate=lambda *_args, **_kwargs: candidate,
        sync_next_actions=lambda *_args, **_kwargs: None,
        notify_cancelled_appointments=lambda *_args, **_kwargs: None,
        provision_academy_account=lambda *_args, **_kwargs: None,
    )

    with pytest.raises(
        service.RecruitmentError,
        match="No active curriculum is configured for the candidate subject",
    ) as exc:
        decision_service.make_final_decision(
            _user("hr_manager"),
            8,
            {"decision": "teacher_academy"},
            dependencies=dependencies,
        )

    assert exc.value.status_code == 409
    assert conn.commits == 0


def test_existing_academy_intake_inherits_candidate_subject():
    class _Cursor:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class _IntakeConnection:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            if "FROM msi_v2.subject_programs" in sql:
                return _Cursor({"id": 3})
            if "SELECT id, academy_status, user_id" in sql:
                return _Cursor(
                    {
                        "id": 31,
                        "academy_status": "new_academy_teacher",
                        "user_id": 17,
                    }
                )
            return _Cursor()

    conn = _IntakeConnection()
    academy_teacher_id = intake_repository.ensure_academy_intake(
        conn,
        candidate={"id": 8, "subject_id": 3},
        actor_login="hr@test",
        now="2026-07-21T00:00:00Z",
    )

    assert academy_teacher_id == 31
    update_sql, update_params = conn.calls[2]
    assert "subject_id = COALESCE(subject_id, NULLIF(%s::bigint, 0))" in update_sql
    assert "subject_program_id = COALESCE" in update_sql
    assert update_params == (3, 3, "2026-07-21T00:00:00Z", 31)


def _connection_factory(conn):
    @contextmanager
    def connect():
        yield conn

    return connect


def test_removed_admin_roles_fail_closed_but_director_handoff_remains_available(client, monkeypatch):
    for role in ("admin", "system_admin"):
        _set_session(client, role)
        assert client.get("/api/v1/recruitment/candidates/1", headers=XHR).status_code == 403
        assert client.get("/api/v1/recruitment/decision-queue", headers=XHR).status_code == 403

    monkeypatch.setattr(
        handoff_api,
        "provision_recruitment_teacher_account",
        lambda teacher_id, **_values: (
            True,
            f"Teacher {teacher_id} provisioned.",
            {"login": "T0001", "temporary_password": "temporary"},
        ),
    )
    _set_session(client, "academic_director")
    response = client.post(
        "/api/v1/recruitment/active-teacher-intakes/7/provision-account",
        headers=XHR,
    )

    assert response.status_code == 200
    assert response.json()["data"]["message"] == "Teacher 7 provisioned."

    monkeypatch.setattr(
        handoff_api,
        "onboard_recruitment_academy_teacher",
        lambda **_values: (
            True,
            "Academy onboarding completed.",
            {"login": "T0002", "temporary_password": "temporary"},
        ),
    )
    academy_response = client.post(
        "/api/v1/recruitment/academy-intakes/8/onboard",
        headers=XHR,
        json={"subject_program_id": 3, "curriculum_item_ids": [11]},
    )

    assert academy_response.status_code == 200
    assert academy_response.json()["data"]["message"] == "Academy onboarding completed."


def test_subject_scoped_hod_can_assign_academy_curriculum(client, monkeypatch):
    monkeypatch.setattr(
        handoff_api,
        "can_user_manage_academy_teacher",
        lambda user, academy_teacher_id: user.role == "head_of_department"
        and academy_teacher_id == 8,
    )
    monkeypatch.setattr(
        handoff_api,
        "onboard_recruitment_academy_teacher",
        lambda **_values: (
            True,
            "Teacher account is ready and the curriculum was assigned.",
            {"login": "TCH0008", "temporary_password": ""},
        ),
    )
    _set_session(client, "head_of_department")

    allowed = client.post(
        "/api/v1/recruitment/academy-intakes/8/onboard",
        headers=XHR,
        json={"subject_program_id": 3, "curriculum_item_ids": [11]},
    )
    denied = client.post(
        "/api/v1/recruitment/academy-intakes/9/onboard",
        headers=XHR,
        json={"subject_program_id": 3, "curriculum_item_ids": [11]},
    )

    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_hr_login_routes_directly_to_recruitment_when_password_change_is_optional(client, monkeypatch):
    import backend.modules.identity.page as identity_page

    csrf = "hr-first-login-csrf"
    client.cookies.set("session", _signed_session({"csrf_token": csrf}))
    monkeypatch.setattr(
        identity_page,
        "authenticate_account_password",
        lambda login, password: {
            "account": {"id": 41, "role": "hr_manager", "login": login},
            "profile": {"role": "hr_manager"},
            "session": {
                "account_id": 41,
                "account_role": "hr_manager",
                "canonical_role": "hr_manager",
                "auth_role": "hr_manager",
                "auth_login": login,
                "staff_id": 51,
                "must_change_password": False,
                "session_version": 3,
            },
        },
    )

    response = client.post(
        "/login",
        data={"login": "HR0001", "password": "temporary", "csrf_token": csrf},
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/hr-manager"


def test_academic_director_decision_queue_endpoint_is_role_scoped(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "list_decision_queue",
        lambda user, **_values: {
            "items": [{"id": 1, "full_name": "Ada", "access_reason": "approval_request"}],
            "page": 1,
            "per_page": 25,
            "total": 1,
            "total_pages": 1,
            "role": user.role,
        },
    )
    _set_session(client, "academic_director")
    allowed = client.get("/api/v1/recruitment/decision-queue", headers=XHR)
    assert allowed.status_code == 200
    assert allowed.json()["data"]["role"] == "academic_director"

    _set_session(client, "head_of_department")
    denied = client.get("/api/v1/recruitment/decision-queue", headers=XHR)
    assert denied.status_code == 403


def test_decision_queue_sql_unions_assignment_and_actionable_approval():
    sql, params = repository._visibility_clause(41, None, include_decision_queue=True)

    assert "assignee_account_id = %s" in sql
    assert "queue_approval.status IN ('requested', 'approved')" in sql
    assert " OR EXISTS" in sql
    assert params == [41]


def test_academic_director_can_view_actionable_request_without_assignment(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(policies, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "candidate_assignment_row", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        repository,
        "candidate_actionable_approval_row",
        lambda *_args, **_kwargs: {
            "id": 9,
            "requested_outcome": "active_teacher",
            "status": "requested",
        },
    )

    policies.ensure_candidate_view(_user(), 8)


def test_approval_visibility_does_not_grant_academic_evaluation_write(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(policies, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "candidate_assignment_row", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        policies.ensure_academic_write(_user(), 8)

    assert exc.value.status_code == 403


def test_assigned_hod_can_view_and_evaluate_recruitment_candidate(monkeypatch):
    conn = _Connection()
    assignment = {
        "candidate_id": 8,
        "assignee_account_id": 41,
        "subject_id": 999,
        "status": "active",
    }
    monkeypatch.setattr(policies, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "candidate_assignment_row",
        lambda *_args, **_kwargs: assignment,
    )

    hod = _user("head_of_department")
    policies.ensure_candidate_view(hod, 8)
    policies.ensure_academic_write(hod, 8)
    policies.ensure_subject_test_write(hod, 8)


def test_hr_can_record_subject_tests_without_academic_assignment():
    policies.ensure_subject_test_write(_user("hr_manager"), 8)
    permissions = service._permissions(_user("hr_manager"))

    assert permissions["can_add_subject_test"] is True
    assert permissions["can_add_academic_evaluation"] is False

    assigned_demo_permissions = service._permissions(
        _user("hr_manager"), can_add_academic_evaluation=True
    )
    assert assigned_demo_permissions["can_add_academic_evaluation"] is True


def test_hr_can_enter_demo_write_flow_for_service_level_assignment_check():
    policies.ensure_demo_write(_user("hr_manager"), 8)

    with pytest.raises(HTTPException) as exc:
        policies.ensure_demo_write(_user("ceo"), 8)

    assert exc.value.status_code == 403


def test_subject_test_write_remains_fail_closed_for_unrelated_roles():
    with pytest.raises(HTTPException) as exc:
        policies.ensure_subject_test_write(_user("ceo"), 8)

    assert exc.value.status_code == 403


def _patch_approval_transaction(monkeypatch, *, approval_status: str = "requested"):
    conn = _Connection()
    events: list[tuple[str, object]] = []
    candidate = {
        "id": 8,
        "full_name": "Ada Teacher",
        "phone": "+998",
        "telegram_username": "ada",
        "subject_id": 3,
        "applied_position": "Math Teacher",
        "status": "under_review",
        "version": 4,
        "academy_teacher_id": None,
        "active_teacher_id": None,
    }
    approval = {
        "id": 9,
        "candidate_id": 8,
        "requested_outcome": "active_teacher",
        "status": approval_status,
        "requested_by_account_id": 12,
        "reviewed_by_account_id": None,
    }
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "lock_candidate_decision_row", lambda *_args: candidate)
    monkeypatch.setattr(repository, "get_approval_row", lambda *_args, **_kwargs: approval)
    monkeypatch.setattr(
        repository,
        "review_approval",
        lambda *_args, **_kwargs: events.append(("approved", _kwargs["status"])) or True,
    )
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **_kwargs: events.append((_kwargs["event_type"], _kwargs["detail"])),
    )
    monkeypatch.setattr(
        repository,
        "touch_candidate",
        lambda *_args, **_kwargs: events.append(("touched", _kwargs["candidate_id"])),
    )
    monkeypatch.setattr(
        repository,
        "ensure_active_teacher_intake",
        lambda *_args, **_kwargs: events.append(("intake", 77)) or 77,
    )
    monkeypatch.setattr(
        repository,
        "ensure_academy_intake",
        lambda *_args, **_kwargs: events.append(("academy", 88)) or 88,
    )
    monkeypatch.setattr(
        repository,
        "update_candidate_stage",
        lambda *_args, **_kwargs: events.append(("stage", _kwargs["stage"])) or True,
    )
    monkeypatch.setattr(
        repository,
        "insert_final_decision",
        lambda *_args, **_kwargs: events.append(("decision", _kwargs["values"])) or 15,
    )
    monkeypatch.setattr(
        repository,
        "consume_approval",
        lambda *_args, **_kwargs: events.append(("consumed", _kwargs["approval_id"])),
    )
    monkeypatch.setattr(service, "get_candidate", lambda *_args: {"id": 8, "status": "under_review"})
    return conn, events, candidate, approval


def test_academic_director_approval_records_review_without_finalizing(monkeypatch):
    conn, events, _candidate, _approval = _patch_approval_transaction(monkeypatch)

    result = service.review_approval(
        _user(),
        8,
        9,
        status="approved",
        review_comment="Academic review complete.",
    )

    assert result["status"] == "under_review"
    assert ("approved", "approved") in events
    assert ("touched", 8) in events
    assert any(event == "candidate.hire_approval_approved" for event, _detail in events)
    assert not any(
        event in {"intake", "academy", "stage", "decision", "consumed"}
        for event, _detail in events
    )
    assert conn.commits == 1


def test_academic_director_cannot_review_legacy_academy_approval(monkeypatch):
    conn, events, _candidate, approval = _patch_approval_transaction(monkeypatch)
    approval["requested_outcome"] = "teacher_academy"

    with pytest.raises(service.RecruitmentError) as exc:
        service.review_approval(
            _user(),
            8,
            9,
            status="approved",
            review_comment="Approved for Academy.",
        )

    assert exc.value.status_code == 409
    assert events == []
    assert conn.commits == 0


@pytest.mark.parametrize("approval_status", ["approved", "consumed", "returned", "revoked"])
def test_non_pending_approvals_conflict(monkeypatch, approval_status):
    _patch_approval_transaction(monkeypatch, approval_status=approval_status)

    with pytest.raises(service.RecruitmentError) as exc:
        service.review_approval(
            _user(),
            8,
            9,
            status="approved",
            review_comment="Retry.",
        )

    assert exc.value.status_code == 409


def test_mismatched_approval_conflicts(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args: {
            "id": 8,
            "status": "under_review",
            "version": 1,
            "academy_teacher_id": None,
            "active_teacher_id": None,
        },
    )
    monkeypatch.setattr(repository, "get_approval_row", lambda *_args, **_kwargs: None)

    with pytest.raises(service.RecruitmentError) as exc:
        service.review_approval(
            _user(),
            8,
            9,
            status="approved",
            review_comment="Wrong candidate.",
        )

    assert exc.value.status_code == 409


def test_academic_director_rejection_revokes_open_requests_and_audits(monkeypatch):
    conn = _Connection()
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(repository, "recruitment_setting_value_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args: {
            "id": 8,
            "status": "under_review",
            "version": 4,
            "academy_teacher_id": None,
            "active_teacher_id": None,
        },
    )
    monkeypatch.setattr(repository, "revoke_open_approvals", lambda *_args, **_kwargs: [9, 10])
    monkeypatch.setattr(repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(repository, "update_candidate_stage", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(repository, "insert_final_decision", lambda *_args, **_kwargs: 18)
    monkeypatch.setattr(
        repository,
        "insert_audit",
        lambda *_args, **_kwargs: events.append((_kwargs["event_type"], _kwargs["detail"])),
    )
    monkeypatch.setattr(service, "get_candidate", lambda *_args: {"id": 8, "status": "rejected"})

    result = service.make_final_decision(
        _user(),
        8,
        {
            "decision": "rejected",
            "rejection_reason": "insufficient_subject_knowledge",
            "reason_detail": "Academic standard not met.",
        },
    )

    assert result["status"] == "rejected"
    assert [event for event, _detail in events] == [
        "candidate.hire_approvals_revoked",
        "candidate.final_decision_made",
    ]
    assert events[0][1]["approval_ids"] == [9, 10]
    assert conn.commits == 1


def test_hr_withdrawal_uses_an_active_database_reason(monkeypatch):
    conn = _Connection()
    decisions = []
    monkeypatch.setattr(service, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(
        repository,
        "recruitment_setting_value_exists",
        lambda _conn, *, category, value: (
            category == "withdrawal_reason"
            and value == "accepted_another_offer"
        ),
    )
    monkeypatch.setattr(
        repository,
        "lock_candidate_decision_row",
        lambda *_args: {
            "id": 8,
            "status": "test_and_demo",
            "version": 4,
            "academy_teacher_id": None,
            "active_teacher_id": None,
        },
    )
    monkeypatch.setattr(
        repository, "revoke_open_approvals", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        repository, "cancel_scheduled_appointments", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        repository, "update_candidate_stage", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        repository,
        "insert_final_decision",
        lambda *_args, **kwargs: decisions.append(kwargs["values"]) or 18,
    )
    monkeypatch.setattr(repository, "insert_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        service,
        "get_candidate",
        lambda *_args: {"id": 8, "status": "candidate_withdrew"},
    )

    result = service.make_final_decision(
        _user("hr_manager"),
        8,
        {
            "decision": "candidate_withdrew",
            "withdrawal_reason": "accepted_another_offer",
            "reason_detail": "",
        },
    )

    assert result["status"] == "candidate_withdrew"
    assert decisions[0]["withdrawal_reason"] == "accepted_another_offer"
    assert decisions[0]["rejection_reason"] == ""
    assert conn.commits == 1


@pytest.mark.parametrize("decision", ["candidate_withdrew"])
def test_academic_director_cannot_record_hr_operational_outcomes(decision):
    with pytest.raises(service.RecruitmentError) as exc:
        service.make_final_decision(
            _user(),
            8,
            {"decision": decision, "reason_detail": "Not an AD action."},
        )

    assert exc.value.status_code == 403
