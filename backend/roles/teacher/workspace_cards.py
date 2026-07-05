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


def _academy_cards(workspace: dict[str, Any]) -> list[dict[str, str]]:
    summary = workspace.get("academy_summary") if isinstance(workspace.get("academy_summary"), dict) else {}
    progress = workspace.get("academy", {}).get("progress") if isinstance(workspace.get("academy"), dict) else {}
    if not isinstance(progress, dict):
        progress = {}

    assigned_count = _as_positive_int(summary.get("assigned_count")) or _as_positive_int(progress.get("assigned_count"))
    completed_count = (
        _as_positive_int(summary.get("completed_count"))
        or _as_positive_int(summary.get("assessed_count"))
        or _as_positive_int(progress.get("assessed_count"))
        or 0
    )
    remaining_count = summary.get("remaining_count")
    try:
        remaining_count = int(remaining_count)
    except (TypeError, ValueError):
        remaining_count = max((assigned_count or 0) - completed_count, 0)
    progress_percent = summary.get("progress_percent")
    try:
        progress_percent = max(0, min(100, int(progress_percent)))
    except (TypeError, ValueError):
        progress_percent = 0
    average_score = summary.get("average_score", progress.get("average_score"))
    try:
        average_label = f"{float(average_score):.1f}"
    except (TypeError, ValueError):
        average_label = "-"

    return [
        {
            "label": "Assigned Lessons",
            "value": _count_label(assigned_count),
            "detail": "academy lesson sequence",
            "tone": "text-slate-900",
        },
        {
            "label": "Completed/Assessed",
            "value": _count_label(completed_count),
            "detail": "reports received",
            "tone": "text-emerald-600",
        },
        {
            "label": "Remaining Lessons",
            "value": _count_label(max(remaining_count, 0)),
            "detail": f"{progress_percent}% complete",
            "tone": "text-blue-600",
        },
        {
            "label": "Average Score",
            "value": average_label,
            "detail": "academy assessment average",
            "tone": "text-slate-900",
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
    if isinstance(workspace.get("academy"), dict):
        return _academy_cards(workspace)

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
