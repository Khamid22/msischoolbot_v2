"""Teacher Academy account provisioning contracts."""

from __future__ import annotations

import pytest

from backend.modules.domains.teacher_academy import account_provisioning


class _Rows:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self):
        self.advisory_locks = 0

    def execute(self, sql, params=None):
        if "pg_advisory_xact_lock" in sql:
            self.advisory_locks += 1
        return _Rows()


def _context(**updates):
    row = {
        "id": 8,
        "full_name": "Example Teacher",
        "phone": "",
        "email": "",
        "telegram_username": "",
        "notes": "",
        "subject_id": 3,
        "subject_program_id": None,
        "academy_status": "new_academy_teacher",
        "account_onboarding_status": "pending",
        "academy_staff_id": None,
        "candidate_id": 44,
        "candidate_account_id": None,
        "candidate_status": "teacher_academy",
        "staff_id": None,
        "staff_login": "",
        "staff_password_hash": "",
        "staff_role": "",
        "teacher_id": None,
        "teacher_candidate_id": None,
        "staff_account_id": None,
        "linked_candidate_account_id": None,
        "account_id": None,
        "account_role": "",
        "account_staff_id": None,
    }
    row.update(updates)
    return row


def test_provisioning_creates_and_links_every_canonical_identity(monkeypatch):
    conn = _Connection()
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "get_recruitment_academy_account_context",
        lambda *_args, **_kwargs: _context(),
    )
    monkeypatch.setattr(
        account_provisioning.repository,
        "insert_teacher_profile_row",
        lambda *_args, **_kwargs: calls.append(("teacher", _kwargs)) or 51,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "link_teacher_identity_to_candidate",
        lambda *_args, **_kwargs: calls.append(("teacher-link", _kwargs)) or True,
    )
    monkeypatch.setattr(
        account_provisioning.repository,
        "get_next_teacher_code",
        lambda *_args, **_kwargs: "TCH0042",
    )
    monkeypatch.setattr(
        account_provisioning.repository,
        "insert_teacher_auth",
        lambda *_args, **_kwargs: calls.append(("staff", _args[1:])) or 61,
    )
    monkeypatch.setattr(
        account_provisioning,
        "_provision_teacher_account_v2",
        lambda *_args, **_kwargs: calls.append(("account", _kwargs)) or 71,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "mark_recruitment_academy_account_ready",
        lambda *_args, **_kwargs: calls.append(("academy", _kwargs)) or True,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "attach_lifecycle_profile_account",
        lambda *_args, **_kwargs: calls.append(("candidate", _kwargs)) or True,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "insert_recruitment_academy_account_audit",
        lambda *_args, **_kwargs: calls.append(("audit", _kwargs)),
    )

    result = account_provisioning.provision_recruitment_academy_account(
        conn,
        academy_teacher_id=8,
        actor_account_id=10,
        actor_login="AD0001",
        now="2026-07-20T12:00:00Z",
    )

    assert result.created is True
    assert result.login == "TCH0042"
    assert result.teacher_id == 51
    assert result.staff_id == 61
    assert result.account_id == 71
    assert conn.advisory_locks == 1
    assert [name for name, _detail in calls] == [
        "teacher",
        "teacher-link",
        "staff",
        "account",
        "academy",
        "candidate",
        "audit",
    ]


def test_provisioning_retry_reuses_complete_links_without_mutation(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "get_recruitment_academy_account_context",
        lambda *_args, **_kwargs: _context(
            account_onboarding_status="complete",
            academy_staff_id=61,
            candidate_account_id=71,
            staff_id=61,
            staff_login="TCH0042",
            staff_password_hash="hash",
            staff_role="teacher",
            teacher_id=51,
            teacher_candidate_id=44,
            staff_account_id=71,
            linked_candidate_account_id=71,
            account_id=71,
            account_role="teacher",
            account_staff_id=61,
        ),
    )

    result = account_provisioning.provision_recruitment_academy_account(
        conn,
        academy_teacher_id=8,
        actor_account_id=10,
        actor_login="AD0001",
        now="2026-07-20T12:00:00Z",
    )

    assert result.created is False
    assert result.login == "TCH0042"
    assert conn.advisory_locks == 0


def test_provisioning_repairs_pending_academy_link_with_existing_teacher_account(
    monkeypatch,
):
    conn = _Connection()
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "get_recruitment_academy_account_context",
        lambda *_args, **_kwargs: _context(
            candidate_account_id=71,
            staff_id=61,
            staff_login="TCH0042",
            staff_password_hash="hash",
            staff_role="teacher",
            teacher_id=51,
            teacher_candidate_id=44,
            staff_account_id=71,
            linked_candidate_account_id=71,
            account_id=71,
            account_role="teacher",
            account_staff_id=61,
        ),
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "link_teacher_identity_to_candidate",
        lambda *_args, **_kwargs: calls.append(("teacher-link", _kwargs)) or True,
    )
    monkeypatch.setattr(
        account_provisioning,
        "_provision_teacher_account_v2",
        lambda *_args, **_kwargs: calls.append(("account", _kwargs)) or 71,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "mark_recruitment_academy_account_ready",
        lambda *_args, **_kwargs: calls.append(("academy", _kwargs)) or True,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "attach_lifecycle_profile_account",
        lambda *_args, **_kwargs: calls.append(("candidate", _kwargs)) or True,
    )
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "insert_recruitment_academy_account_audit",
        lambda *_args, **_kwargs: calls.append(("audit", _kwargs)),
    )

    result = account_provisioning.provision_recruitment_academy_account(
        conn,
        academy_teacher_id=8,
        actor_account_id=10,
        actor_login="AD0001",
        now="2026-07-20T12:00:00Z",
    )

    assert result.created is False
    assert result.login == "TCH0042"
    assert conn.advisory_locks == 0
    assert [name for name, _detail in calls] == [
        "teacher-link",
        "account",
        "academy",
        "candidate",
        "audit",
    ]


def test_provisioning_rejects_conflicting_account_links(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "get_recruitment_academy_account_context",
        lambda *_args, **_kwargs: _context(
            candidate_account_id=99,
            staff_id=61,
            staff_login="TCH0042",
            staff_password_hash="hash",
            staff_role="teacher",
            teacher_id=51,
            staff_account_id=71,
            linked_candidate_account_id=99,
            account_id=71,
        ),
    )

    with pytest.raises(
        account_provisioning.AcademyAccountProvisioningError,
        match="different accounts",
    ):
        account_provisioning.provision_recruitment_academy_account(
            conn,
            academy_teacher_id=8,
            actor_account_id=10,
            actor_login="AD0001",
            now="2026-07-20T12:00:00Z",
        )


def test_provisioning_rejects_non_teacher_lifecycle_account(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(
        account_provisioning.mutations_repository,
        "get_recruitment_academy_account_context",
        lambda *_args, **_kwargs: _context(
            candidate_account_id=99,
            linked_candidate_account_id=99,
            account_id=99,
            account_role="student",
        ),
    )

    with pytest.raises(
        account_provisioning.AcademyAccountProvisioningError,
        match="another role",
    ):
        account_provisioning.provision_recruitment_academy_account(
            conn,
            academy_teacher_id=8,
            actor_account_id=10,
            actor_login="AD0001",
            now="2026-07-20T12:00:00Z",
        )
