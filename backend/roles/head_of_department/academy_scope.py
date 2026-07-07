"""Subject-scoped Teacher Academy access for Head of Department users."""

from __future__ import annotations

from typing import Any, Iterable

from backend.core.database import connect_auth_db
from backend.domains.teacher_academy import queries as academy_queries
from backend.utils.context import session
from backend.utils.session import current_auth_role, current_staff_id


def _to_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _row_subject_ids(rows: Iterable[Any]) -> set[int]:
    return {_to_int(row.get("subject_id") if isinstance(row, dict) else row["subject_id"]) for row in rows} - {0}


def _safe_query_subject_ids(account_id: int, staff_id: int, conn: Any | None = None) -> set[int]:
    if account_id <= 0 and staff_id <= 0:
        return set()

    def _load(active_conn: Any) -> set[int]:
        try:
            rows = academy_queries.list_hod_subject_scope_rows(
                active_conn,
                account_id=account_id,
                staff_id=staff_id,
            )
        except Exception:
            return set()
        return _row_subject_ids(rows)

    if conn is not None:
        return _load(conn)
    with connect_auth_db() as opened_conn:
        return _load(opened_conn)


def current_hod_subject_ids(conn: Any | None = None) -> set[int]:
    """Return active subject ids for the current HOD session.

    Missing scope tables or missing session metadata fail closed to an empty
    scope, so HODs do not accidentally see every Teacher Academy record.
    """

    if current_auth_role() != "head_of_department":
        return set()
    return _safe_query_subject_ids(_to_int(session.get("account_id")), current_staff_id() or 0, conn=conn)


def filter_rows_by_subject_scope(rows: Iterable[dict[str, Any]], subject_ids: set[int]) -> list[dict[str, Any]]:
    if not subject_ids:
        return []
    return [row for row in rows if _to_int(row.get("subject_id")) in subject_ids]


def filter_academy_teachers_for_current_scope(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if current_auth_role() != "head_of_department":
        return list(rows)
    return filter_rows_by_subject_scope(rows, current_hod_subject_ids())


def _subject_id_for_academy_teacher(conn: Any, academy_teacher_id: Any) -> int:
    return _to_int(academy_queries.get_academy_teacher_subject_id(conn, _to_int(academy_teacher_id)))


def _subject_id_for_assignment(conn: Any, assignment_id: Any) -> int:
    return _to_int(academy_queries.get_assignment_subject_id(conn, _to_int(assignment_id)))


def can_current_user_manage_academy_teacher(academy_teacher_id: Any) -> bool:
    role = current_auth_role()
    if role in {"admin", "academic_director"}:
        return True
    if role != "head_of_department":
        return False
    with connect_auth_db() as conn:
        subject_ids = current_hod_subject_ids(conn=conn)
        return _subject_id_for_academy_teacher(conn, academy_teacher_id) in subject_ids


def can_current_user_manage_academy_assignment(assignment_id: Any) -> bool:
    role = current_auth_role()
    if role in {"admin", "academic_director"}:
        return True
    if role != "head_of_department":
        return False
    with connect_auth_db() as conn:
        subject_ids = current_hod_subject_ids(conn=conn)
        return _subject_id_for_assignment(conn, assignment_id) in subject_ids


def filter_admin_context_for_current_hod(page_context: dict[str, Any], academic_context: dict[str, Any]) -> None:
    """Mutate admin/academic context to the current HOD subject scope."""

    if current_auth_role() != "head_of_department":
        return
    subject_ids = current_hod_subject_ids()
    page_context["admin_teacher_academy"] = filter_rows_by_subject_scope(
        page_context.get("admin_teacher_academy") or [],
        subject_ids,
    )

    if not subject_ids:
        page_context["admin_teachers"] = []
        for key in ("subjects", "groups", "lessons", "schedules", "sessions", "curriculum_programs", "curriculum_items"):
            if isinstance(academic_context.get(key), list):
                academic_context[key] = []
        return

    subject_name_scope = {
        str(row.get("subject") or row.get("subject_name") or "").strip().casefold()
        for row in page_context["admin_teacher_academy"]
        if str(row.get("subject") or row.get("subject_name") or "").strip()
    }
    if subject_name_scope:
        page_context["admin_teachers"] = [
            row for row in page_context.get("admin_teachers") or []
            if str(row.get("subject") or row.get("subject_name") or "").strip().casefold() in subject_name_scope
        ]

    for key in ("subjects", "groups", "lessons", "schedules", "sessions", "curriculum_programs", "curriculum_items"):
        values = academic_context.get(key)
        if not isinstance(values, list):
            continue
        filtered = []
        for row in values:
            subject_id = _to_int(row.get("subject_id") or row.get("subjectId"))
            if subject_id and subject_id in subject_ids:
                filtered.append(row)
            elif not subject_id and str(row.get("subject_name") or row.get("subject") or "").strip().casefold() in subject_name_scope:
                filtered.append(row)
        academic_context[key] = filtered


__all__ = [
    "can_current_user_manage_academy_assignment",
    "can_current_user_manage_academy_teacher",
    "current_hod_subject_ids",
    "filter_academy_teachers_for_current_scope",
    "filter_admin_context_for_current_hod",
    "filter_rows_by_subject_scope",
]
