from backend.modules.domains.identity.passwords import verify_password_hash
from backend.modules.domains.identity import repository as accounts_repository
from backend.modules.domains.teacher_records import service as teachers_service


class _Connection:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


class _CaptureConnection:
    def __init__(self):
        self.calls = []

    def execute(self, statement, parameters=()):
        self.calls.append((statement, parameters))
        return self

    def fetchone(self):
        return None


def test_existing_teacher_account_update_binds_status_and_identity_fields_in_order():
    conn = _CaptureConnection()

    account_id = accounts_repository.save_teacher_account(
        conn,
        account_id=88,
        teacher_id=42,
        staff_id=24,
        login="TCH0042",
        legacy_login="matht001",
        password_hash="hashed-password",
        full_name="Example Teacher",
        status="active",
    )

    assert account_id == 88
    assert conn.calls[0][1] == (
        "TCH0042",
        "hashed-password",
        "active",
        "Example Teacher",
        24,
        88,
    )


def test_teacher_password_reset_updates_legacy_and_canonical_credentials(monkeypatch):
    conn = _Connection()
    captured = {}

    monkeypatch.setattr(teachers_service, "backfill_teacher_auth", lambda active_conn: None)
    monkeypatch.setattr(
        teachers_service.repository,
        "get_teacher_password_reset_row",
        lambda active_conn, teacher_id: {
            "teacher_id": teacher_id,
            "full_name": "Example Teacher",
            "teacher_status": "active",
            "account_id": 88,
            "login": "TCH0042",
        },
    )

    def update_legacy(active_conn, **kwargs):
        captured["legacy"] = kwargs
        return 1

    def update_canonical(active_conn, **kwargs):
        captured["canonical"] = kwargs
        return 7

    def audit(active_conn, **kwargs):
        captured["audit"] = kwargs

    monkeypatch.setattr(teachers_service.repository, "update_teacher_legacy_password", update_legacy)
    monkeypatch.setattr(teachers_service.repository, "activate_teacher_account_with_password", update_canonical)
    monkeypatch.setattr(teachers_service.repository, "insert_teacher_password_reset_audit_event", audit)
    monkeypatch.setattr(teachers_service, "utc_now_iso", lambda: "2026-07-13T10:00:00Z")

    reset, error, credentials = teachers_service._reset_teacher_password(
        conn,
        teacher_id=42,
        actor_account_id=12,
        actor_login="AD0001",
        commit=True,
    )

    assert reset is True
    assert error == ""
    # Reset restores the password to the login and re-enables the account.
    assert credentials == {
        "login": "TCH0042",
        "temporary_password": "TCH0042",
        "display_name": "Example Teacher",
        "must_change_password": False,
        "updated_at": "2026-07-13T10:00:00Z",
    }
    assert captured["legacy"]["teacher_id"] == 42
    assert captured["canonical"]["account_id"] == 88
    assert verify_password_hash(captured["canonical"]["password_hash"], "TCH0042")
    assert verify_password_hash(captured["legacy"]["password_hash"], "TCH0042")
    assert captured["audit"] == {
        "teacher_id": 42,
        "account_id": 88,
        "actor_account_id": 12,
        "actor_login": "AD0001",
    }
    assert conn.committed is True


def test_teacher_password_reset_rejects_disabled_teacher(monkeypatch):
    conn = _Connection()
    monkeypatch.setattr(teachers_service, "backfill_teacher_auth", lambda active_conn: None)
    monkeypatch.setattr(
        teachers_service.repository,
        "get_teacher_password_reset_row",
        lambda active_conn, teacher_id: {
            "teacher_id": teacher_id,
            "full_name": "Former Teacher",
            "teacher_status": "inactive",
            "account_id": 88,
            "login": "TCH0042",
        },
    )

    reset, error, credentials = teachers_service._reset_teacher_password(
        conn,
        teacher_id=42,
    )

    assert reset is False
    assert error == "Teacher account is disabled."
    assert credentials == {}
    assert conn.committed is False
