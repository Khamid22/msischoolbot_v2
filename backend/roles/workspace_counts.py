"""Read-only aggregate cards for role workspace shells."""

from __future__ import annotations

from typing import Any

from backend.core.database import connect


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


def _load_counts(queries: dict[str, str]) -> dict[str, int | None]:
    counts = {key: None for key in queries}
    try:
        with connect() as conn:
            for key, sql in queries.items():
                try:
                    counts[key] = _count_value(conn.execute(sql).fetchone())
                except Exception:
                    counts[key] = None
                    try:
                        conn.rollback()
                    except Exception:
                        pass
    except Exception:
        return counts
    return counts


def ceo_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts(
        {
            "schools": """
                SELECT count(*) AS total
                FROM msi_v2.schools
                WHERE status = 'active'
            """,
            "students": """
                SELECT count(*) AS total
                FROM msi_v2.students
                WHERE status = 'active'
            """,
            "teachers": """
                SELECT count(*) AS total
                FROM msi_v2.teachers
                WHERE status = 'active'
            """,
            "subjects": """
                SELECT count(*) AS total
                FROM msi_v2.subjects
                WHERE status = 'active'
            """,
        }
    )
    return [
        {"label": "Schools", "value": _format_count(counts["schools"])},
        {"label": "Students", "value": _format_count(counts["students"])},
        {"label": "Teachers", "value": _format_count(counts["teachers"])},
        {"label": "Subjects", "value": _format_count(counts["subjects"])},
    ]


def academic_director_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts(
        {
            "groups": """
                SELECT count(*) AS total
                FROM msi_v2.groups
                WHERE status = 'active'
            """,
            "teachers": """
                SELECT count(*) AS total
                FROM msi_v2.teachers
                WHERE status = 'active'
            """,
            "subjects": """
                SELECT count(*) AS total
                FROM msi_v2.subjects
                WHERE status = 'active'
            """,
            "students": """
                SELECT count(*) AS total
                FROM msi_v2.students
                WHERE status = 'active'
            """,
        }
    )
    return [
        {"label": "Groups", "value": _format_count(counts["groups"])},
        {"label": "Teachers", "value": _format_count(counts["teachers"])},
        {"label": "Subjects", "value": _format_count(counts["subjects"])},
        {"label": "Students", "value": _format_count(counts["students"])},
    ]


def customer_support_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts(
        {
            "parents": """
                SELECT count(*) AS total
                FROM msi_v2.parents
                WHERE status = 'active'
            """,
            "students": """
                SELECT count(*) AS total
                FROM msi_v2.students
                WHERE status = 'active'
            """,
            "pending_parent_accounts": """
                SELECT count(*) AS total
                FROM msi_v2.accounts
                WHERE role = 'parent'
                  AND status = 'pending'
            """,
            "pending_parent_invites": """
                SELECT count(*) AS total
                FROM msi_v2.account_invites
                WHERE invite_type = 'parent'
                  AND status = 'pending'
                  AND (expires_at IS NULL OR expires_at > now())
            """,
        }
    )
    pending_accounts = _format_count(counts["pending_parent_accounts"], fallback="-")
    pending_invites = _format_count(counts["pending_parent_invites"], fallback="-")
    return [
        {"label": "Parents", "value": _format_count(counts["parents"])},
        {"label": "Students", "value": _format_count(counts["students"])},
        {"label": "Pending Parents/Invites", "value": f"{pending_accounts} / {pending_invites}"},
        {"label": "Support/Payments", "value": "Placeholder"},
    ]


def hr_manager_workspace_cards() -> list[dict[str, str]]:
    counts = _load_counts(
        {
            "teachers": """
                SELECT count(*) AS total
                FROM msi_v2.teachers
                WHERE status = 'active'
            """,
            "candidates": """
                SELECT count(*) AS total
                FROM msi_v2.teacher_candidates
            """,
        }
    )
    return [
        {"label": "Teachers", "value": _format_count(counts["teachers"])},
        {"label": "Candidates", "value": _format_count(counts["candidates"])},
        {"label": "Teacher Academy", "value": "Placeholder"},
    ]


__all__ = [
    "academic_director_workspace_cards",
    "ceo_workspace_cards",
    "customer_support_workspace_cards",
    "hr_manager_workspace_cards",
]
