from __future__ import annotations

from typing import Any

from backend.core.database import connect_auth_db
from backend.modules.reporting import repository


def _count_value(row: Any) -> int | None:
    if not row:
        return None
    try:
        value = row["total"]
    except (KeyError, TypeError):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _format_count(value: int | None, *, fallback: str = "Placeholder") -> str:
    if value is None:
        return fallback
    return f"{value:,}"


def _load_counts(keys) -> dict[str, int | None]:
    return {key: _count_value({"total": value}) for key, value in repository.load_counts(keys).items()}


def list_active_schools() -> list[tuple[str, str]]:
    with connect_auth_db() as conn:
        rows = repository.list_active_school_rows(conn)
    return [(str(row["code"]), str(row["name"])) for row in rows]


def list_active_group_names(school_filter="all") -> list[str]:
    with connect_auth_db() as conn:
        rows = repository.list_active_group_name_rows(conn, school_filter)
    return [str(row["name"]) for row in rows]


def list_active_group_school_mappings() -> list[tuple[str, str]]:
    with connect_auth_db() as conn:
        rows = repository.list_active_group_school_rows(conn)
    return [
        (str(row["group_name"]), str(row["school_code"]))
        for row in rows
    ]


def ceo_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts(["schools", "students", "teachers", "subjects"])
    return [
        {"label": "Schools", "value": _format_count(counts["schools"])},
        {"label": "Students", "value": _format_count(counts["students"])},
        {"label": "Teachers", "value": _format_count(counts["teachers"])},
        {"label": "Subjects", "value": _format_count(counts["subjects"])},
    ]


def academic_director_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts(["groups", "teachers", "subjects", "students"])
    return [
        {"label": "Groups", "value": _format_count(counts["groups"])},
        {"label": "Teachers", "value": _format_count(counts["teachers"])},
        {"label": "Subjects", "value": _format_count(counts["subjects"])},
        {"label": "Students", "value": _format_count(counts["students"])},
    ]


def customer_support_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts([
        "parents", "students", "pending_parent_accounts", "pending_parent_invites"
    ])
    pending_accounts = _format_count(counts["pending_parent_accounts"], fallback="-")
    pending_invites = _format_count(counts["pending_parent_invites"], fallback="-")
    return [
        {"label": "Parents", "value": _format_count(counts["parents"])},
        {"label": "Students", "value": _format_count(counts["students"])},
        {"label": "Pending Parents/Invites", "value": f"{pending_accounts} / {pending_invites}"},
        {"label": "Support/Payments", "value": "Placeholder"},
    ]


__all__ = [
    "academic_director_workspace_cards",
    "ceo_workspace_cards",
    "customer_support_workspace_cards",
    "list_active_group_names",
    "list_active_group_school_mappings",
    "list_active_schools",
]
