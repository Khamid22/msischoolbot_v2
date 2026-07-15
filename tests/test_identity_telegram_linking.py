"""Signed, account-scoped Telegram linking contracts for staff profiles."""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from backend.core.access import CurrentUser
from backend.modules.identity import telegram_linking


class _Result:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _TelegramLinkConnection:
    def __init__(self):
        self.links: list[dict] = []
        self.commits = 0

    def execute(self, sql, params=None):
        params = tuple(params or ())
        normalized = " ".join(sql.split())
        if "FROM msi_v2.accounts" in normalized:
            return _Result(row={"id": int(params[0])})
        if "WHERE telegram_user_id = %s AND status = 'active'" in normalized:
            telegram_id = int(params[0])
            row = next((item for item in self.links if item["telegram_user_id"] == telegram_id and item["status"] == "active"), None)
            return _Result(row=row)
        if "WHERE account_id = %s AND status = 'active'" in normalized and normalized.startswith("SELECT"):
            account_id = int(params[0])
            row = next((item for item in self.links if item["account_id"] == account_id and item["status"] == "active"), None)
            return _Result(row=row)
        if normalized.startswith("UPDATE msi_v2.account_telegram_links") and "telegram_user_id <> %s" in normalized:
            account_id, keep_telegram_id = map(int, params)
            for item in self.links:
                if item["account_id"] == account_id and item["status"] == "active" and item["telegram_user_id"] != keep_telegram_id:
                    item["status"] = "revoked"
            return _Result()
        if normalized.startswith("UPDATE msi_v2.account_telegram_links") and "WHERE id = %s" in normalized:
            username, link_id = params
            item = next(item for item in self.links if item["id"] == int(link_id))
            item["telegram_username"] = username
            return _Result()
        if normalized.startswith("INSERT INTO msi_v2.account_telegram_links"):
            account_id, telegram_id, username = params
            self.links.append({
                "id": len(self.links) + 1,
                "account_id": int(account_id),
                "telegram_user_id": int(telegram_id),
                "telegram_username": username,
                "linked_at": "2026-07-15T12:00:00+00:00",
                "status": "active",
            })
            return _Result(row={"id": len(self.links)})
        if normalized.startswith("UPDATE msi_v2.account_telegram_links") and "RETURNING telegram_user_id" in normalized:
            account_id = int(params[0])
            rows = []
            for item in self.links:
                if item["account_id"] == account_id and item["status"] == "active":
                    item["status"] = "revoked"
                    rows.append({"telegram_user_id": item["telegram_user_id"]})
            return _Result(rows=rows)
        if normalized.startswith("UPDATE msi_v2.teacher_recruitment_notifications"):
            return _Result()
        raise AssertionError(f"Unexpected SQL: {normalized}")

    def commit(self):
        self.commits += 1


def _user(role="academic_director", account_id=41):
    return CurrentUser(login=f"{role}@test", role=role, account_id=account_id, staff_id=51)


def _connection_factory(conn):
    @contextmanager
    def connect():
        yield conn

    return connect


def test_link_requires_verified_telegram_mini_app_init_data(monkeypatch):
    monkeypatch.setattr(telegram_linking, "telegram_user_from_init_data", lambda _value: None)

    with pytest.raises(telegram_linking.TelegramLinkError) as raised:
        telegram_linking.link_connection(_user(), "unsigned-user-id=9001")

    assert raised.value.status_code == 401
    assert raised.value.code == "invalid_telegram_init_data"


def test_link_refresh_and_unlink_preserve_one_active_identity(monkeypatch):
    conn = _TelegramLinkConnection()
    audits = []
    monkeypatch.setattr(telegram_linking, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(telegram_linking, "telegram_user_from_init_data", lambda _value: {"id": 9001, "username": "demo_hod"})
    monkeypatch.setattr(telegram_linking.repository, "insert_account_audit_event", lambda *_args, **kwargs: audits.append(kwargs["event_type"]))
    monkeypatch.setattr(telegram_linking, "enqueue_linked_account_summary", lambda *_args, **_kwargs: None)

    linked = telegram_linking.link_connection(_user("head_of_department"), "verified")
    refreshed = telegram_linking.link_connection(_user("head_of_department"), "verified-again")
    unlinked = telegram_linking.unlink_connection(_user("head_of_department"))

    assert linked["connected"] is True
    assert linked["username"] == "demo_hod"
    assert refreshed["connected"] is True
    assert len(conn.links) == 1
    assert unlinked["connected"] is False
    assert audits == ["account.telegram_linked", "account.telegram_linked", "account.telegram_unlinked"]


def test_link_refuses_identity_owned_by_another_active_account(monkeypatch):
    conn = _TelegramLinkConnection()
    conn.links.append({
        "id": 1,
        "account_id": 99,
        "telegram_user_id": 9001,
        "telegram_username": "already_linked",
        "linked_at": "2026-07-15T12:00:00+00:00",
        "status": "active",
    })
    monkeypatch.setattr(telegram_linking, "connect_auth_db", _connection_factory(conn))
    monkeypatch.setattr(telegram_linking, "telegram_user_from_init_data", lambda _value: {"id": 9001, "username": "demo_hod"})

    with pytest.raises(telegram_linking.TelegramLinkError) as raised:
        telegram_linking.link_connection(_user(), "verified")

    assert raised.value.status_code == 409
    assert raised.value.code == "telegram_identity_in_use"
    assert conn.commits == 0
