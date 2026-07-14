"""Telegram sign-in resolved through canonical accounts and profiles."""

from __future__ import annotations

from typing import Any, Callable

from backend.modules.identity import repository
from backend.modules.identity.service import (
    ACCOUNT_AUTH_ROLES,
    build_session_payload,
    get_account_by_id,
    load_account_profile,
)
from backend.modules.identity.database import connect
from backend.core.access.roles import normalize_role


TELEGRAM_LOGIN_ALLOWED_STATUS = "active"
TELEGRAM_LINK_ALLOWED_STATUS = "active"
TELEGRAM_AUTH_ROLES = ACCOUNT_AUTH_ROLES


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


def _with_connection(conn: Any | None, callback: Callable[[Any], Any]) -> Any:
    if conn is not None:
        return callback(conn)
    with connect() as opened_conn:
        return callback(opened_conn)


def _normalize_link(row: Any) -> dict[str, Any] | None:
    if not row:
        return None
    normalized = dict(row)
    link_id = _to_int(normalized.get("id"))
    account_id = _to_int(normalized.get("account_id"))
    telegram_user_id = _to_int(normalized.get("telegram_user_id"))
    if link_id is None or account_id is None or telegram_user_id is None:
        return None
    return {
        "id": link_id,
        "account_id": account_id,
        "telegram_user_id": telegram_user_id,
        "telegram_username": _text(normalized.get("telegram_username")) or None,
        "status": _text(normalized.get("status")).casefold() or "revoked",
    }


def get_account_telegram_link(
    telegram_user_id: Any,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    parsed_user_id = normalize_telegram_user_id(telegram_user_id)
    if parsed_user_id is None:
        return None
    return _with_connection(
        conn,
        lambda active_conn: _normalize_link(
            repository.get_account_telegram_link_row(active_conn, parsed_user_id)
        ),
    )


def authenticate_account_telegram(
    telegram_user_id: Any,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    parsed_user_id = normalize_telegram_user_id(telegram_user_id)
    if parsed_user_id is None:
        return None

    def _authenticate(active_conn: Any) -> dict[str, Any] | None:
        link = get_account_telegram_link(parsed_user_id, conn=active_conn)
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
        if not profile or _text(profile.get("status")).casefold() != TELEGRAM_LOGIN_ALLOWED_STATUS:
            return None
        session_payload = build_session_payload(account, profile)
        if not session_payload:
            return None
        session_payload["telegram_user_id"] = parsed_user_id
        if conn is None or getattr(active_conn, "db_backend", "") == "postgres":
            repository.mark_account_login(active_conn, int(account["id"]))
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
