"""Read-only card data for the parent workspace."""

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


def _as_number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _count_label(value: int | None) -> str:
    return f"{value:,}" if value is not None else "-"


def _percent_label(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{round(value)}%"


def _placeholder_cards() -> list[dict[str, str]]:
    return [
        {
            "label": "Linked Children",
            "value": "-",
            "detail": "active child links",
            "tone": "text-slate-900",
        },
        {
            "label": "Progress",
            "value": "-",
            "detail": "attendance/progress summary",
            "tone": "text-blue-600",
        },
        {
            "label": "Payment Status",
            "value": "Placeholder",
            "detail": "payment policy later",
            "tone": "text-amber-700",
        },
        {
            "label": "Support",
            "value": "Placeholder",
            "detail": "Customer Support contact later",
            "tone": "text-emerald-700",
        },
    ]


def _summary_progress(children: list) -> tuple[str, str]:
    progress_values: list[float] = []
    attendance_values: list[float] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        for indicator in _as_list(child.get("academic_indicators")):
            if not isinstance(indicator, dict):
                continue
            progress = _as_number(indicator.get("program_completion_rate"))
            if progress is not None:
                progress_values.append(min(progress, 100))
            attendance = _as_number(indicator.get("ar"))
            if attendance is not None:
                attendance_values.append(min(attendance, 100))

    progress_average = _average(progress_values)
    if progress_average is not None:
        return _percent_label(progress_average), "average child progress"

    attendance_average = _average(attendance_values)
    if attendance_average is not None:
        return _percent_label(attendance_average), "average attendance"

    return "-", "attendance/progress summary"


def build_parent_workspace_cards(
    *,
    parent_id: Any,
    children: Any = None,
) -> list[dict[str, str]]:
    """Build safe parent summary cards from already-loaded child data."""
    if _as_positive_int(parent_id) is None:
        return _placeholder_cards()
    if not isinstance(children, list):
        return _placeholder_cards()

    cards = _placeholder_cards()
    cards[0]["value"] = _count_label(len(children))
    cards[1]["value"], cards[1]["detail"] = _summary_progress(children)
    return cards


__all__ = ["build_parent_workspace_cards"]
