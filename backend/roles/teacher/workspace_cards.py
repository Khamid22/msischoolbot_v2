"""Read-only card data for the teacher workspace."""

from __future__ import annotations

from typing import Any


def _as_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _count_label(value: int | None) -> str:
    return f"{value:,}" if value is not None else "-"


def _placeholder_cards() -> list[dict[str, str]]:
    return [
        {
            "label": "Assigned Groups",
            "value": "-",
            "detail": "active teaching groups",
            "tone": "text-slate-900",
        },
        {
            "label": "Students",
            "value": "-",
            "detail": "in assigned groups",
            "tone": "text-slate-900",
        },
        {
            "label": "Resources",
            "value": "Placeholder",
            "detail": "teacher resources later",
            "tone": "text-blue-600",
        },
        {
            "label": "Attendance/Homework",
            "value": "Placeholder",
            "detail": "teacher actions later",
            "tone": "text-emerald-600",
        },
    ]


def build_teacher_workspace_cards(
    *,
    teacher_id: Any,
    teacher_staff_id: Any = None,
    workspace: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build safe summary cards from already-scoped teacher workspace data."""
    if _as_positive_int(teacher_id) is None:
        return _placeholder_cards()
    if not isinstance(workspace, dict):
        return _placeholder_cards()

    groups = _as_list(workspace.get("groups"))
    group_keys = set()
    student_keys = set()
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            continue
        group_info = group.get("group") if isinstance(group.get("group"), dict) else {}
        group_key = (
            _as_positive_int(group_info.get("id"))
            or str(group_info.get("name") or "").strip().casefold()
            or f"group-{index}"
        )
        group_keys.add(group_key)

        enrollments = _as_list(group.get("enrollments"))
        for enrollment_index, enrollment in enumerate(enrollments):
            if not isinstance(enrollment, dict):
                continue
            student_key = (
                _as_positive_int(enrollment.get("enrollmentId"))
                or str(enrollment.get("fullName") or "").strip().casefold()
                or f"{group_key}-student-{enrollment_index}"
            )
            student_keys.add(student_key)

    group_count = len(group_keys)
    student_count = len(student_keys)
    cards = _placeholder_cards()
    cards[0]["value"] = _count_label(group_count)
    cards[1]["value"] = _count_label(student_count)
    return cards


__all__ = ["build_teacher_workspace_cards"]
