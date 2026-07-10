from werkzeug.security import generate_password_hash, check_password_hash

from backend.services.identity import accounts


class _Conn:
    db_backend = "postgres"


def _account(password="Initial123"):
    return {
        "id": 7,
        "login": "MSI00007",
        "password_hash": generate_password_hash(password),
        "role": "student",
        "status": "active",
        "full_name": "Student",
        "must_change_password": True,
        "session_version": 1,
    }


def test_change_own_password_updates_version_and_audit(monkeypatch):
    conn = _Conn()
    row = _account()
    captured = {}
    monkeypatch.setattr(accounts.repository, "get_account_by_id_row", lambda *args, **kwargs: row)

    def change_password(_conn, **kwargs):
        captured.update(kwargs)
        return 2

    monkeypatch.setattr(accounts.repository, "change_account_password", change_password)
    monkeypatch.setattr(
        accounts.repository,
        "insert_account_audit_event",
        lambda _conn, **kwargs: captured.update({"audit": kwargs}),
    )

    outcome = accounts.change_own_password(
        7,
        current_password="Initial123",
        new_password="Private456",
        confirm_password="Private456",
        conn=conn,
    )

    assert outcome.changed is True
    assert outcome.session_version == 2
    assert captured["must_change_password"] is False
    assert check_password_hash(captured["password_hash"], "Private456")
    assert captured["audit"]["event_type"] == "account.password_changed"


def test_change_own_password_enforces_confirmation_length_and_difference():
    too_short = accounts.change_own_password(
        7,
        current_password="Initial123",
        new_password="short",
        confirm_password="short",
        conn=_Conn(),
    )
    mismatch = accounts.change_own_password(
        7,
        current_password="Initial123",
        new_password="Private456",
        confirm_password="Private789",
        conn=_Conn(),
    )
    unchanged = accounts.change_own_password(
        7,
        current_password="Initial123",
        new_password="Initial123",
        confirm_password="Initial123",
        conn=_Conn(),
    )

    assert too_short.code == "password_too_short"
    assert mismatch.code == "password_mismatch"
    assert unchanged.code == "password_unchanged"


def test_admin_reset_forces_change_and_invalidates_sessions(monkeypatch):
    conn = _Conn()
    captured = {}
    monkeypatch.setattr(
        accounts.repository,
        "get_student_account_by_legacy_id_row",
        lambda *args, **kwargs: _account(),
    )
    monkeypatch.setattr(
        accounts.repository,
        "change_account_password",
        lambda _conn, **kwargs: captured.update(kwargs) or 4,
    )
    monkeypatch.setattr(accounts.repository, "insert_account_audit_event", lambda *args, **kwargs: None)

    outcome = accounts.reset_student_password(
        1007,
        "Reset789",
        actor_account_id=3,
        conn=conn,
    )

    assert outcome.changed is True
    assert outcome.session_version == 4
    assert captured["must_change_password"] is True
