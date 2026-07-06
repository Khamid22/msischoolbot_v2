"""Read-only summary cards for the Head of Department workspace."""

from __future__ import annotations

from backend.roles.head_of_department.academy_scope import (
    current_hod_subject_ids,
    filter_rows_by_subject_scope,
)
from backend.roles.admin.services.teacher_academy_service import list_academy_teachers


def _placeholder_cards():
    return [
        {"label": "Subject Scope", "value": "0", "detail": "assigned subjects"},
        {"label": "Academy Teachers", "value": "0", "detail": "visible trainees"},
        {"label": "Ready for Review", "value": "0", "detail": "subject scoped"},
        {"label": "Reports", "value": "0", "detail": "teacher journeys"},
    ]


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
