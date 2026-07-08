"""Safe notification helpers for Teacher Academy events.

This module intentionally stays best-effort. Telegram delivery can be wired to
the bot runtime later; for tomorrow-ready academy use, missing Telegram links or
senders must never block lesson assignment or assessment workflows.
"""

from __future__ import annotations

from typing import Any


ACADEMY_EVENT_LABELS = {
    "lesson_assigned": "Academy lesson assigned",
    "lesson_time_changed": "Academy lesson time changed",
    "assessment_added": "Assessment report added",
    "academy_update": "Teacher Academy update",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _has_telegram_link(academy_teacher: dict[str, Any] | None) -> bool:
    if not isinstance(academy_teacher, dict):
        return False
    return bool(_text(academy_teacher.get("telegram_username")) or academy_teacher.get("telegram_user_id"))


def notify_academy_teacher_event(
    *,
    academy_teacher: dict[str, Any] | None = None,
    event_type: str,
    title: str = "",
    body: str = "",
    source: str = "Academic Department",
) -> dict[str, Any]:
    """Return a safe in-app/Telegram notification result."""
    normalized_type = _text(event_type) or "academy_update"
    normalized_title = _text(title) or ACADEMY_EVENT_LABELS.get(normalized_type, "Teacher Academy update")
    normalized_body = _text(body)
    normalized_source = _text(source) or "Academic Department"

    has_telegram = _has_telegram_link(academy_teacher)
    return {
        "ok": True,
        "event_type": normalized_type,
        "title": normalized_title,
        "body": normalized_body,
        "source": normalized_source,
        "in_app_available": True,
        "telegram_sent": False,
        "reason": "telegram_sender_unavailable" if has_telegram else "telegram_link_missing",
    }


__all__ = ["ACADEMY_EVENT_LABELS", "notify_academy_teacher_event"]
