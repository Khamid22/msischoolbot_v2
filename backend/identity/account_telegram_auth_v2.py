"""Shared-account Telegram auth helpers for Phase 1C.

This module expects an already HMAC-verified Telegram user id. It is not wired
into ``/auth/telegram`` yet; it only resolves ``account_telegram_links`` and
builds the same legacy-compatible session payloads used by password Auth V2.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.identity.account_auth_v2 import (
    build_legacy_session_payload,
    load_account_profile,
)
from backend.identity.common import connect
from backend.identity.roles import normalize_role


TELEGRAM_AUTH_ROLES = {
    "system_admin",
    "ceo",
    "hr_manager",
    "customer_support",
    "student",
    "teacher",
    "parent",
    "academic_director",
}
TELEGRAM_LOGIN_ALLOWED_STATUS = "active"
TELEGRAM_LINK_ALLOWED_STATUS = "active"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int | None:
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


def normalize_telegram_user_id(value: Any) -> int | None:
    return _to_int(value)


def _row_to_dict(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    return dict(row)


def _with_connection(conn: Any | None, callback: Callable[[Any], Any]) -> Any:
    if conn is not None:
        return callback(conn)
    with connect() as opened_conn:
        return callback(opened_conn)


def _fetchone(conn: Any, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    return _row_to_dict(conn.execute(sql, params).fetchone())


def _normalize_link(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    link_id = _to_int(row.get("id"))
    account_id = _to_int(row.get("account_id"))
    telegram_user_id = _to_int(row.get("telegram_user_id"))
    if link_id is None or account_id is None or telegram_user_id is None:
        return None
    return {
        "id": link_id,
        "account_id": account_id,
        "telegram_user_id": telegram_user_id,
        "telegram_username": _text(row.get("telegram_username")) or None,
        "status": _text(row.get("status")).casefold() or "revoked",
    }


def _normalize_account(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    account_id = _to_int(row.get("id"))
    if account_id is None:
        return None
    role = normalize_role(row.get("role"))
    return {
        "id": account_id,
        "login": _text(row.get("login")) or None,
        "password_hash": _text(row.get("password_hash")) or None,
        "role": role,
        "raw_role": _text(row.get("role")),
        "status": _text(row.get("status")).casefold() or "disabled",
        "full_name": _text(row.get("full_name")),
        "phone": _text(row.get("phone")) or None,
        "legacy_source_table": _text(row.get("legacy_source_table")),
        "legacy_source_id": _to_int(row.get("legacy_source_id")),
    }


def get_account_telegram_link(
    telegram_user_id: Any,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    parsed_telegram_user_id = normalize_telegram_user_id(telegram_user_id)
    if parsed_telegram_user_id is None:
        return None

    def _load(active_conn: Any) -> dict[str, Any] | None:
        row = _fetchone(
            active_conn,
            """
            SELECT id, account_id, telegram_user_id, telegram_username, status
            FROM msi_v2.account_telegram_links
            WHERE telegram_user_id = %s
            LIMIT 1
            """,
            (parsed_telegram_user_id,),
        )
        return _normalize_link(row)

    return _with_connection(conn, _load)


def get_account_by_id(account_id: Any, conn: Any | None = None) -> dict[str, Any] | None:
    parsed_account_id = _to_int(account_id)
    if parsed_account_id is None:
        return None

    def _load(active_conn: Any) -> dict[str, Any] | None:
        row = _fetchone(
            active_conn,
            """
            SELECT id, login, password_hash, role, status, full_name, phone,
                   legacy_source_table, legacy_source_id
            FROM msi_v2.accounts
            WHERE id = %s
            LIMIT 1
            """,
            (parsed_account_id,),
        )
        return _normalize_account(row)

    return _with_connection(conn, _load)


def _profile_allows_telegram_login(profile: dict[str, Any] | None) -> bool:
    return bool(profile and _text(profile.get("status")).casefold() == TELEGRAM_LOGIN_ALLOWED_STATUS)


def authenticate_account_telegram(
    telegram_user_id: Any,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    parsed_telegram_user_id = normalize_telegram_user_id(telegram_user_id)
    if parsed_telegram_user_id is None:
        return None

    def _authenticate(active_conn: Any) -> dict[str, Any] | None:
        link = get_account_telegram_link(parsed_telegram_user_id, conn=active_conn)
        if not link or link.get("status") != TELEGRAM_LINK_ALLOWED_STATUS:
            return None

        account = get_account_by_id(link.get("account_id"), conn=active_conn)
        if not account:
            return None
        role = normalize_role(account.get("role"))
        if role not in TELEGRAM_AUTH_ROLES:
            return None
        if _text(account.get("status")).casefold() != TELEGRAM_LOGIN_ALLOWED_STATUS:
            return None

        profile = load_account_profile(account, conn=active_conn)
        if not _profile_allows_telegram_login(profile):
            return None

        session_payload = build_legacy_session_payload(account, profile)
        if not session_payload:
            return None
        session_payload["telegram_user_id"] = parsed_telegram_user_id

        return {
            "link": link,
            "account": account,
            "profile": profile,
            "session": session_payload,
        }

    return _with_connection(conn, _authenticate)


__all__ = [
    "authenticate_account_telegram",
    "get_account_by_id",
    "get_account_telegram_link",
    "normalize_telegram_user_id",
]
