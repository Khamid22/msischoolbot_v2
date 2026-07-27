from pathlib import Path

from werkzeug.security import check_password_hash

from backend.modules.domains.identity import staff_accounts as service


class _Connection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _patch_storage(monkeypatch, *, existing=False):
    captured = {"staff": None, "account": None, "profile": None, "audit": None}
    staff = {"id": 25, "role": "customer_support"} if existing else None
    account = {"id": 203, "role": "customer_support"} if existing else None
    monkeypatch.setattr(service.repository, "_phase1_accounts_available", lambda _conn: True)
    monkeypatch.setattr(service.repository, "_staff_identity_by_login", lambda _conn, _login: staff)
    monkeypatch.setattr(service.repository, "_account_identity_by_login", lambda _conn, _login: account)
    monkeypatch.setattr(service.repository, "_account_identity_by_staff_id", lambda _conn, _staff_id: account)

    def save(key, value):
        def capture(_conn, **values):
            captured[key] = values
            return value

        return capture

    monkeypatch.setattr(service.repository, "_insert_or_update_staff_role", save("staff", 25))
    monkeypatch.setattr(service.repository, "_upsert_staff_account", save("account", 203))
    monkeypatch.setattr(service.repository, "_upsert_staff_profile_role", save("profile", 60))
    monkeypatch.setattr(
        service.repository,
        "_insert_account_audit_event",
        lambda _conn, **values: captured.__setitem__("audit", values),
    )
    return captured


def test_cs0001_provisioning_matches_fixed_hr_account_pattern(monkeypatch):
    captured = _patch_storage(monkeypatch)
    conn = _Connection()

    created, error, credentials = service._create_customer_support_account(
        conn,
        commit=True,
    )

    assert created is True
    assert error == ""
    assert credentials == {
        "role": "customer_support",
        "login": "cs0001",
        "temporary_password": "cs0001",
        "display_name": "Customer Support",
        "must_change_password": False,
        "account_id": 203,
        "staff_id": 25,
    }
    assert captured["staff"]["role"] == "customer_support"
    assert captured["staff"]["password_hash"] == captured["account"]["password_hash"]
    assert check_password_hash(captured["account"]["password_hash"], "cs0001")
    assert captured["account"]["must_change_password"] is False
    assert captured["profile"]["department"] == "Customer Support"
    assert captured["audit"] == {
        "event_type": "account.created",
        "entity_account_id": 203,
        "detail": {"role": "customer_support", "method": "operator_cli"},
    }
    assert conn.commits == 1


def test_cs0001_rerun_resets_same_account_and_invalidates_sessions(monkeypatch):
    captured = _patch_storage(monkeypatch, existing=True)
    conn = _Connection()

    created, error, credentials = service._create_customer_support_account(conn, commit=True)

    assert created is True
    assert error == ""
    assert credentials["account_id"] == 203
    assert captured["audit"]["event_type"] == "account.password_reset"
    assert conn.commits == 1
    assert "session_version = session_version + 1" in Path(
        "backend/modules/domains/identity/staff_repository.py"
    ).read_text()


def test_cs0001_collision_with_another_role_fails_closed(monkeypatch):
    monkeypatch.setattr(service.repository, "_phase1_accounts_available", lambda _conn: True)
    monkeypatch.setattr(
        service.repository,
        "_staff_identity_by_login",
        lambda _conn, _login: {"id": 4, "role": "hr_manager"},
    )

    created, error, credentials = service._create_customer_support_account(_Connection())

    assert created is False
    assert "another staff role" in error
    assert credentials == {}


def test_cs0001_script_has_no_arbitrary_login_or_password_arguments():
    source = Path("scripts/create_customer_support_account.py").read_text()
    assert "--temporary-password" not in source
    assert "--login" not in source
    assert 'print(f"Password: {credentials[' in source
