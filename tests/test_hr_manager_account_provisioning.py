import inspect
from pathlib import Path

from werkzeug.security import check_password_hash

from backend.modules.people.staff import service


class _Connection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _patch_successful_storage(monkeypatch, *, existing=False):
    captured = {"staff": None, "account": None, "profile": None, "audit": None}
    staff = {"id": 20, "role": "hr_manager"} if existing else None
    account = {"id": 10, "role": "hr_manager"} if existing else None
    monkeypatch.setattr(service.repository, "_phase1_accounts_available", lambda _conn: True)
    monkeypatch.setattr(service.repository, "_staff_identity_by_login", lambda _conn, _login: staff)
    monkeypatch.setattr(service.repository, "_account_identity_by_login", lambda _conn, _login: account)
    monkeypatch.setattr(
        service.repository,
        "_account_identity_by_staff_id",
        lambda _conn, _staff_id: account,
    )
    monkeypatch.setattr(service, "_generate_temporary_password", lambda: "SafePass4826")

    def save_staff(_conn, **values):
        captured["staff"] = values
        return 20

    def save_account(_conn, **values):
        captured["account"] = values
        return 10

    def save_profile(_conn, **values):
        captured["profile"] = values
        return 30

    monkeypatch.setattr(service.repository, "_insert_or_update_staff_role", save_staff)
    monkeypatch.setattr(service.repository, "_upsert_staff_account", save_account)
    monkeypatch.setattr(service.repository, "_upsert_staff_profile_role", save_profile)
    monkeypatch.setattr(
        service.repository,
        "_insert_account_audit_event",
        lambda _conn, **values: captured.__setitem__("audit", values),
    )
    return captured


def test_hr0001_provisioning_hashes_one_time_password_and_forces_change(monkeypatch):
    captured = _patch_successful_storage(monkeypatch)
    conn = _Connection()

    created, error, credentials = service._create_hr_manager_account(
        conn,
        display_name="Recruitment Lead",
        commit=True,
    )

    assert created is True
    assert error == ""
    assert credentials == {
        "role": "hr_manager",
        "login": "HR0001",
        "temporary_password": "SafePass4826",
        "display_name": "Recruitment Lead",
        "must_change_password": True,
        "account_id": 10,
        "staff_id": 20,
    }
    staff_hash = captured["staff"]["password_hash"]
    account_hash = captured["account"]["password_hash"]
    assert staff_hash == account_hash
    assert staff_hash != credentials["temporary_password"]
    assert check_password_hash(staff_hash, credentials["temporary_password"])
    assert captured["account"]["role"] == "hr_manager"
    assert captured["profile"]["department"] == "Human Resources"
    assert captured["audit"]["event_type"] == "account.created"
    assert captured["audit"]["detail"] == {"role": "hr_manager", "method": "operator_cli"}
    assert conn.commits == 1


def test_hr0001_rerun_resets_same_account_and_audits_password_reset(monkeypatch):
    captured = _patch_successful_storage(monkeypatch, existing=True)
    conn = _Connection()

    created, error, credentials = service._create_hr_manager_account(conn, commit=True)

    assert created is True
    assert error == ""
    assert credentials["account_id"] == 10
    assert credentials["staff_id"] == 20
    assert captured["audit"]["event_type"] == "account.password_reset"
    assert conn.commits == 1


def test_hr0001_collision_with_another_role_fails_closed(monkeypatch):
    monkeypatch.setattr(service.repository, "_phase1_accounts_available", lambda _conn: True)
    monkeypatch.setattr(
        service.repository,
        "_staff_identity_by_login",
        lambda _conn, _login: {"id": 4, "role": "academic_director"},
    )
    monkeypatch.setattr(
        service.repository,
        "_insert_or_update_staff_role",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not mutate")),
    )

    created, error, credentials = service._create_hr_manager_account(_Connection())

    assert created is False
    assert "another staff role" in error
    assert credentials == {}


def test_hr0001_account_role_collision_fails_closed(monkeypatch):
    monkeypatch.setattr(service.repository, "_phase1_accounts_available", lambda _conn: True)
    monkeypatch.setattr(service.repository, "_staff_identity_by_login", lambda _conn, _login: None)
    monkeypatch.setattr(
        service.repository,
        "_account_identity_by_login",
        lambda _conn, _login: {"id": 7, "role": "ceo"},
    )

    created, error, credentials = service._create_hr_manager_account(_Connection())

    assert created is False
    assert "another account role" in error
    assert credentials == {}


def test_hr0001_partial_write_failure_rolls_back(monkeypatch):
    captured = _patch_successful_storage(monkeypatch)
    monkeypatch.setattr(service.repository, "_upsert_staff_account", lambda *_args, **_kwargs: 0)
    conn = _Connection()

    created, error, credentials = service._create_hr_manager_account(conn, commit=True)

    assert created is False
    assert "Unable to create the HR Manager account" in error
    assert credentials == {}
    assert captured["audit"] is None
    assert conn.rollbacks == 1
    assert conn.commits == 0


def test_hr0001_reset_invalidates_sessions_and_has_no_operator_password_argument():
    repository_source = inspect.getsource(service.repository._upsert_staff_account)
    command_source = Path("scripts/create_hr_manager_account.py").read_text()

    assert "must_change_password = true" in repository_source
    assert "session_version = session_version + 1" in repository_source
    assert "password_changed_at = NULL" in repository_source
    assert "--temporary-password" not in command_source
    assert "--login" not in command_source
