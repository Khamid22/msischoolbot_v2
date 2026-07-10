from contextlib import contextmanager
import hashlib

from backend.modules.parents import service


class _Connection:
    def rollback(self):
        raise AssertionError("rollback was not expected")


@contextmanager
def _connected(connection):
    yield connection


def test_new_parent_invite_stores_only_a_sha256_digest(monkeypatch):
    connection = _Connection()
    captured = {}
    raw_code = "secret-parent-code"
    monkeypatch.setattr(service, "_connect", lambda: _connected(connection))
    monkeypatch.setattr(service.secrets, "token_urlsafe", lambda _size: raw_code)
    monkeypatch.setattr(
        service.parent_repository,
        "get_student_v2_id_by_legacy_row",
        lambda _conn, _student_id: 41,
    )
    monkeypatch.setattr(
        service.parent_repository,
        "get_staff_db_id_for_admin_id",
        lambda _conn, _staff_id: 9,
    )
    monkeypatch.setattr(
        service.parent_repository,
        "insert_parent_invite_row",
        lambda _conn, **values: captured.update(values),
    )

    returned_code = service.create_parent_invite_code(7, issued_by=9)

    assert returned_code == raw_code
    assert captured["token_hash"] == hashlib.sha256(raw_code.encode()).hexdigest()
    assert raw_code not in captured.values()


def test_parent_invite_claim_locks_links_provisions_and_consumes_once(monkeypatch):
    connection = _Connection()
    calls = []
    monkeypatch.setattr(service, "_connect", lambda: _connected(connection))
    monkeypatch.setattr(
        service.parent_repository,
        "get_pending_parent_invite_payload",
        lambda conn, digest, for_update=False: calls.append(("lock", conn, for_update))
        or {"id": 5, "student_row_id": 7},
    )
    monkeypatch.setattr(
        service.parent_repository,
        "link_parent_from_invite",
        lambda conn, **values: calls.append(("link", conn, values["student_row_id"]))
        or {"id": 11, "full_name": "Parent", "phone": "", "telegram_username": ""},
    )
    monkeypatch.setattr(
        service,
        "provision_parent_account",
        lambda conn, **values: calls.append(("account", conn, values["parent_id"])) or 13,
    )
    auth_result = {
        "account": {"id": 13},
        "profile": {"parent_id": 11},
        "session": {"account_id": 13, "session_version": 1},
    }
    monkeypatch.setattr(
        service,
        "load_account_auth_result",
        lambda account_id, conn=None, record_login=False: calls.append(
            ("session", conn, account_id, record_login)
        )
        or auth_result,
    )
    monkeypatch.setattr(
        service.parent_repository,
        "consume_parent_invite",
        lambda conn, invite_id, **values: calls.append(("consume", conn, invite_id))
        or {"id": invite_id},
    )

    parent = service.claim_parent_invite_code("one-time", full_name="Parent")

    assert parent["id"] == 11
    assert parent["account_id"] == 13
    assert parent["auth_result"] is auth_result
    assert calls == [
        ("lock", connection, True),
        ("link", connection, 7),
        ("account", connection, 11),
        ("session", connection, 13, True),
        ("consume", connection, 5),
    ]


def test_secure_invite_migration_drops_plaintext_token_storage():
    source = open(
        "database/alembic/versions/0006_secure_parent_invites.py",
        encoding="utf-8",
    ).read()

    assert "hashlib.sha256" in source
    assert "DROP COLUMN IF EXISTS token" in source
    assert "used_by_parent_id" in source
