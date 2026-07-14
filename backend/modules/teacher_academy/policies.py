"""Subject-scoped Teacher Academy access helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from backend.core.database import connect_auth_db
from backend.modules.teacher_academy import repository as academy_repository

if TYPE_CHECKING:
    from backend.core.access import CurrentUser


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
            rows = academy_repository.list_hod_subject_scope_rows(
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


def hod_subject_ids_for_context(
    *,
    role: str,
    account_id: Any = 0,
    staff_id: Any = 0,
    conn: Any | None = None,
) -> set[int]:
    """Return active subject ids for an explicit HOD identity context.

    Missing scope tables or missing identity metadata fail closed to an empty
    scope, so HODs do not accidentally see every Teacher Academy record.
    """

    if str(role or "").strip() != "head_of_department":
        return set()
    return _safe_query_subject_ids(_to_int(account_id), _to_int(staff_id), conn=conn)


def hod_subject_ids_for_user(user: CurrentUser, conn: Any | None = None) -> set[int]:
    return hod_subject_ids_for_context(
        role=user.role,
        account_id=user.account_id,
        staff_id=user.staff_id,
        conn=conn,
    )


def filter_rows_by_subject_scope(rows: Iterable[dict[str, Any]], subject_ids: set[int]) -> list[dict[str, Any]]:
    if not subject_ids:
        return []
    return [row for row in rows if _to_int(row.get("subject_id")) in subject_ids]


def filter_academy_teachers_for_context(
    rows: Iterable[dict[str, Any]],
    *,
    role: str,
    account_id: Any = 0,
    staff_id: Any = 0,
) -> list[dict[str, Any]]:
    if str(role or "").strip() != "head_of_department":
        return list(rows)
    return filter_rows_by_subject_scope(
        rows,
        hod_subject_ids_for_context(role=role, account_id=account_id, staff_id=staff_id),
    )


def filter_academy_teachers_for_user(
    rows: Iterable[dict[str, Any]],
    user: CurrentUser,
) -> list[dict[str, Any]]:
    return filter_academy_teachers_for_context(
        rows,
        role=user.role,
        account_id=user.account_id,
        staff_id=user.staff_id,
    )


def _subject_id_for_academy_teacher(conn: Any, academy_teacher_id: Any) -> int:
    return _to_int(academy_repository.get_academy_teacher_subject_id(conn, _to_int(academy_teacher_id)))


def _subject_id_for_assignment(conn: Any, assignment_id: Any) -> int:
    return _to_int(academy_repository.get_assignment_subject_id(conn, _to_int(assignment_id)))


def can_context_manage_academy_teacher(
    academy_teacher_id: Any,
    *,
    role: str,
    account_id: Any = 0,
    staff_id: Any = 0,
) -> bool:
    if role in {"admin", "academic_director"}:
        return True
    if role != "head_of_department":
        return False
    with connect_auth_db() as conn:
        subject_ids = hod_subject_ids_for_context(
            role=role,
            account_id=account_id,
            staff_id=staff_id,
            conn=conn,
        )
        return _subject_id_for_academy_teacher(conn, academy_teacher_id) in subject_ids


def can_user_manage_academy_teacher(user: CurrentUser, academy_teacher_id: Any) -> bool:
    return can_context_manage_academy_teacher(
        academy_teacher_id,
        role=user.role,
        account_id=user.account_id,
        staff_id=user.staff_id,
    )


def can_context_manage_academy_assignment(
    assignment_id: Any,
    *,
    role: str,
    account_id: Any = 0,
    staff_id: Any = 0,
) -> bool:
    if role in {"admin", "academic_director"}:
        return True
    if role != "head_of_department":
        return False
    with connect_auth_db() as conn:
        subject_ids = hod_subject_ids_for_context(
            role=role,
            account_id=account_id,
            staff_id=staff_id,
            conn=conn,
        )
        return _subject_id_for_assignment(conn, assignment_id) in subject_ids


def can_user_manage_academy_assignment(user: CurrentUser, assignment_id: Any) -> bool:
    return can_context_manage_academy_assignment(
        assignment_id,
        role=user.role,
        account_id=user.account_id,
        staff_id=user.staff_id,
    )


def filter_admin_context_for_hod_scope(
    page_context: dict[str, Any],
    academic_context: dict[str, Any],
    *,
    role: str,
    account_id: Any = 0,
    staff_id: Any = 0,
) -> None:
    """Mutate admin/academic context to an explicit HOD subject scope."""

    if str(role or "").strip() != "head_of_department":
        return
    subject_ids = hod_subject_ids_for_context(role=role, account_id=account_id, staff_id=staff_id)
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
    "can_context_manage_academy_assignment",
    "can_context_manage_academy_teacher",
    "can_user_manage_academy_assignment",
    "can_user_manage_academy_teacher",
    "filter_academy_teachers_for_context",
    "filter_academy_teachers_for_user",
    "filter_admin_context_for_hod_scope",
    "filter_rows_by_subject_scope",
    "hod_subject_ids_for_context",
    "hod_subject_ids_for_user",
]
