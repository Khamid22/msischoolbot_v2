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


def _connection_factory(conn):
    @contextmanager
    def connect():
        yield conn

    return connect


def test_admin_candidate_apis_fail_closed_but_handoff_remains_available(client, monkeypatch):
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
    _set_session(client, "admin")
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
    monkeypatch.setattr(service, "get_candidate", lambda *_args: {"id": 8, "status": "active_teacher"})
    return conn, events, candidate, approval


@pytest.mark.parametrize("approval_status", ["requested", "approved"])
def test_academic_director_approval_atomically_finalizes_and_consumes(
    monkeypatch,
    approval_status,
):
    conn, events, _candidate, _approval = _patch_approval_transaction(
        monkeypatch,
        approval_status=approval_status,
    )

    result = service.review_approval(
        _user(),
        8,
        9,
        status="approved",
        review_comment="Academic review complete.",
    )

    assert result["status"] == "active_teacher"
    assert ("intake", 77) in events
    assert ("stage", "active_teacher") in events
    assert ("consumed", 9) in events
    assert any(event == "candidate.final_decision_made" for event, _detail in events)
    if approval_status == "requested":
        assert ("approved", "approved") in events
        assert any(event == "candidate.hire_approval_approved" for event, _detail in events)
    else:
        assert ("approved", "approved") not in events
    assert conn.commits == 1


def test_approval_retry_reuses_consumed_outcome_without_duplicate_mutations(monkeypatch):
    conn, events, candidate, approval = _patch_approval_transaction(
        monkeypatch,
        approval_status="consumed",
    )
    candidate.update({"status": "active_teacher", "active_teacher_id": 77})
    monkeypatch.setattr(
        repository,
        "final_decision_for_approval",
        lambda *_args, **_kwargs: {"id": 15, "decision": "active_teacher"},
    )

    result = service.review_approval(
        _user(),
        8,
        9,
        status="approved",
        review_comment="Retry.",
    )

    assert result["status"] == "active_teacher"
    assert events == []
    assert conn.rollbacks == 1
    assert conn.commits == 0


@pytest.mark.parametrize("approval_status", ["returned", "revoked"])
def test_returned_and_revoked_approvals_conflict(monkeypatch, approval_status):
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
    monkeypatch.setattr(
        repository,
        "get_approval_by_id",
        lambda *_args, **_kwargs: {"id": 9, "candidate_id": 99},
    )

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


@pytest.mark.parametrize("decision", ["on_hold", "candidate_withdrew"])
def test_academic_director_cannot_record_hr_operational_outcomes(decision):
    with pytest.raises(service.RecruitmentError) as exc:
        service.make_final_decision(
            _user(),
            8,
            {"decision": decision, "reason_detail": "Not an AD action."},
        )

    assert exc.value.status_code == 403
