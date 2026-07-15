"""Explicit, signed Telegram Mini App account linking."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.hr.recruitment.notifications import enqueue_linked_account_summary
from backend.modules.identity import repository
from backend.modules.identity import telegram_link_repository
from backend.platform.telegram.init_data import telegram_user_from_init_data


LINKABLE_ROLES = {"hr_manager", "academic_director", "head_of_department"}


class TelegramLinkError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400, code: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _text(value: Any) -> str:
    return str(value or "").strip()


def _connection_payload(row: Any | None) -> dict[str, Any]:
    username = _text(row["telegram_username"]) if row else ""
    linked_at = row["linked_at"] if row else None
    if isinstance(linked_at, (date, datetime)):
        linked_at = linked_at.isoformat()
    bot_username = _text(os.getenv("TELEGRAM_BOT_USERNAME") or os.getenv("BOT_USERNAME")).lstrip("@")
    return {
        "connected": bool(row),
        "username": username,
        "linked_at": linked_at,
        "open_telegram_url": f"https://t.me/{bot_username}?start=link_account" if bot_username else "",
        "bot_configured": bool(bot_username and _text(os.getenv("BOT_TOKEN"))),
    }


def get_connection(user: CurrentUser) -> dict[str, Any]:
    if user.role not in LINKABLE_ROLES or not user.account_id:
        raise TelegramLinkError("Telegram linking is not available for this account.", status_code=403)
    with connect_auth_db() as conn:
        row = telegram_link_repository.get_active_link_for_account(conn, int(user.account_id))
    return _connection_payload(row)


def link_connection(user: CurrentUser, init_data: str) -> dict[str, Any]:
    if user.role not in LINKABLE_ROLES or not user.account_id:
        raise TelegramLinkError("Telegram linking is not available for this account.", status_code=403)
    telegram_user = telegram_user_from_init_data(init_data)
    if not telegram_user:
        raise TelegramLinkError(
            "Open this page inside the Telegram Mini App and try again.",
            status_code=401,
            code="invalid_telegram_init_data",
        )
    telegram_id = int(telegram_user["id"])
    username = _text(telegram_user.get("username"))
    account_id = int(user.account_id)
    with connect_auth_db() as conn:
        repository.get_account_by_id_row(conn, account_id, for_update=True)
        identity = telegram_link_repository.get_active_link_for_identity(
            conn,
            telegram_id,
            for_update=True,
        )
        if identity and int(identity["account_id"]) != account_id:
            raise TelegramLinkError(
                "This Telegram account is already linked to another active MSI account.",
                status_code=409,
                code="telegram_identity_in_use",
            )
        telegram_link_repository.revoke_other_active_links(
            conn,
            account_id=account_id,
            keep_telegram_user_id=telegram_id,
        )
        if identity:
            telegram_link_repository.refresh_active_link(
                conn,
                link_id=int(identity["id"]),
                username=username,
            )
        else:
            inserted = telegram_link_repository.insert_active_link(
                conn,
                account_id=account_id,
                telegram_user_id=telegram_id,
                username=username,
            )
            if not inserted:
                raise TelegramLinkError(
                    "This Telegram account is already linked to another active MSI account.",
                    status_code=409,
                    code="telegram_identity_in_use",
                )
        repository.insert_account_audit_event(
            conn,
            actor_account_id=account_id,
            event_type="account.telegram_linked",
            entity_account_id=account_id,
            detail={"telegram_username": username, "telegram_user_id": telegram_id},
        )
        telegram_link_repository.requeue_waiting_recruitment_notifications(conn, account_id)
        enqueue_linked_account_summary(conn, account_id)
        conn.commit()
    return get_connection(user)


def unlink_connection(user: CurrentUser) -> dict[str, Any]:
    if user.role not in LINKABLE_ROLES or not user.account_id:
        raise TelegramLinkError("Telegram linking is not available for this account.", status_code=403)
    account_id = int(user.account_id)
    with connect_auth_db() as conn:
        telegram_user_ids = telegram_link_repository.revoke_active_links(conn, account_id)
        if telegram_user_ids:
            repository.insert_account_audit_event(
                conn,
                actor_account_id=account_id,
                event_type="account.telegram_unlinked",
                entity_account_id=account_id,
                detail={"telegram_user_ids": telegram_user_ids},
            )
        conn.commit()
    return get_connection(user)


__all__ = [
    "TelegramLinkError",
    "get_connection",
    "link_connection",
    "unlink_connection",
]
