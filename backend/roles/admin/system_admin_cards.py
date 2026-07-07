"""Read-only System Admin card data for the legacy /admin workspace."""

from __future__ import annotations

from typing import Any

from backend.core.database import connect_auth_db


def _count_label(value: Any) -> str:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return "-"
    return f"{parsed:,}" if parsed >= 0 else "-"


def _placeholder_cards() -> list[dict[str, str]]:
    return [
        {
            "label": "Total Accounts",
            "value": "-",
            "detail": "shared login identities",
            "tone": "text-slate-900",
        },
        {
            "label": "Active Accounts",
            "value": "-",
            "detail": "usable accounts",
            "tone": "text-emerald-700",
        },
        {
            "label": "Pending Accounts",
            "value": "-",
            "detail": "waiting for activation/linking",
            "tone": "text-amber-700",
        },
        {
            "label": "Telegram Links",
            "value": "-",
            "detail": "active linked accounts",
            "tone": "text-blue-700",
        },
    ]


def _count_row(conn: Any, sql: str) -> int | None:
    row = conn.execute(sql).fetchone()
    if not row:
        return None
    try:
        return int(row["count"])
    except (KeyError, TypeError, ValueError):
        return None


def system_admin_workspace_cards() -> list[dict[str, str]]:
    """Return account-level System Admin cards, failing closed to placeholders."""
    cards = _placeholder_cards()
    try:
        with connect_auth_db() as conn:
            total_accounts = _count_row(conn, "SELECT COUNT(*) AS count FROM msi_v2.accounts")
            active_accounts = _count_row(
                conn,
                "SELECT COUNT(*) AS count FROM msi_v2.accounts WHERE status = 'active'",
            )
            pending_accounts = _count_row(
                conn,
                "SELECT COUNT(*) AS count FROM msi_v2.accounts WHERE status = 'pending'",
            )
            telegram_links = _count_row(
                conn,
                "SELECT COUNT(*) AS count FROM msi_v2.account_telegram_links WHERE status = 'active'",
            )
    except Exception:
        return cards

    cards[0]["value"] = _count_label(total_accounts)
    cards[1]["value"] = _count_label(active_accounts)
    cards[2]["value"] = _count_label(pending_accounts)
    cards[3]["value"] = _count_label(telegram_links)
    return cards


__all__ = ["system_admin_workspace_cards"]
