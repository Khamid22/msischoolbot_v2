"""Read-only summary cards for the Head of Department workspace."""

from __future__ import annotations

from backend.domains.teacher_academy.permissions import (
    hod_subject_ids_for_context,
    filter_rows_by_subject_scope,
)
from backend.domains.teacher_academy.service import list_academy_teachers
from backend.utils.context import session
from backend.utils.session import current_auth_role, current_staff_id


def _placeholder_cards():
    return [
        {"label": "Subject Scope", "value": "0", "detail": "assigned subjects"},
        {"label": "Academy Teachers", "value": "0", "detail": "visible trainees"},
        {"label": "Ready for Review", "value": "0", "detail": "subject scoped"},
        {"label": "Reports", "value": "0", "detail": "teacher journeys"},
    ]


def current_hod_subject_ids(conn=None):
    return hod_subject_ids_for_context(
        role=current_auth_role(),
        account_id=session.get("account_id"),
        staff_id=current_staff_id() or 0,
        conn=conn,
    )


def head_of_department_workspace_cards() -> list[dict[str, str]]:
    try:
        subject_ids = current_hod_subject_ids()
        scoped_teachers = filter_rows_by_subject_scope(list_academy_teachers(), subject_ids)
    except Exception:
        return _placeholder_cards()

    ready_count = sum(
        1
        for teacher in scoped_teachers
        if str(teacher.get("academy_status") or "").strip() == "ready_for_active_teacher"
    )
    return [
        {"label": "Subject Scope", "value": str(len(subject_ids)), "detail": "assigned subjects"},
        {"label": "Academy Teachers", "value": str(len(scoped_teachers)), "detail": "visible trainees"},
        {"label": "Ready for Review", "value": str(ready_count), "detail": "promotion review"},
        {"label": "Reports", "value": "Subject only", "detail": "teacher journeys"},
    ]


__all__ = ["head_of_department_workspace_cards"]
