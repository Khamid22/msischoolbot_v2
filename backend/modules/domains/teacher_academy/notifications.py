"""Best-effort outbound Telegram notifications for Teacher Academy events."""

from __future__ import annotations

import html
import json
import re
from typing import Any
from urllib import error as urlerror
from urllib import request

from backend.core.runtime.config import get_app_settings


ACADEMY_EVENT_LABELS = {
    "teacher_created": "New Teacher Academy teacher",
    "lesson_assigned": "Academy lesson assigned",
    "lesson_time_changed": "Academy lesson time changed",
    "assessment_added": "Assessment report added",
    "academy_update": "Teacher Academy update",
}

TEACHER_ACADEMY_CHANNEL_ENV = "TEACHER_ACADEMY_CHANNEL_CHAT_ID"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed else None


def _escape(value: Any) -> str:
    return html.escape(_text(value))


def _subject_env_key(subject_name: Any) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", _text(subject_name).upper()).strip("_")
    return f"TEACHER_ACADEMY_{normalized}_CHAT_ID" if normalized else ""


def _channel_chat_id(academy_teacher: dict[str, Any] | None) -> str:
    settings = get_app_settings().telegram
    subject_key = _subject_env_key((academy_teacher or {}).get("subject"))
    if subject_key:
        value = _text(dict(settings.academy_subject_chat_ids).get(subject_key))
        if value:
            return value
    return _text(settings.academy_channel_chat_id)


def _bot_token() -> str:
    return _text(get_app_settings().telegram.bot_token)


def _portal_url() -> str:
    base_url = _text(get_app_settings().telegram.mini_app_url).rstrip("/")
    return f"{base_url}/teacher" if base_url else ""


def _has_telegram_link(academy_teacher: dict[str, Any] | None) -> bool:
    if not isinstance(academy_teacher, dict):
        return False
    return bool(_int_or_none(academy_teacher.get("telegram_user_id")))


def _send_telegram_message(chat_id: Any, text: str) -> tuple[bool, str]:
    token = _bot_token()
    normalized_chat_id = _text(chat_id)
    if not token:
        return False, "telegram_bot_token_missing"
    if not normalized_chat_id:
        return False, "telegram_chat_missing"
    payload = json.dumps(
        {
            "chat_id": normalized_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    req = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        timeout_seconds = get_app_settings().telegram.api_timeout_seconds
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return 200 <= int(response.status) < 300, ""
    except (OSError, urlerror.URLError, urlerror.HTTPError):
        return False, "telegram_send_failed"


def _teacher_display(academy_teacher: dict[str, Any] | None) -> str:
    if not isinstance(academy_teacher, dict):
        return "Teacher"
    return (
        _text(academy_teacher.get("full_name"))
        or _text(academy_teacher.get("name"))
        or _text(academy_teacher.get("telegram_username"))
        or "Teacher"
    )


def _lesson_display(assignment: dict[str, Any] | None) -> str:
    if not isinstance(assignment, dict):
        return ""
    lesson_number = _text(assignment.get("lesson_number"))
    lesson_topic = _text(assignment.get("lesson_topic") or assignment.get("topic"))
    if lesson_number and lesson_topic:
        return f"{lesson_number}: {lesson_topic}"
    return lesson_topic or lesson_number


def _channel_message(
    *,
    academy_teacher: dict[str, Any] | None,
    event_type: str,
    title: str,
    body: str,
    assignment: dict[str, Any] | None,
    assessment: dict[str, Any] | None,
    lessons_count: int,
    source: str,
) -> str:
    teacher_name = _teacher_display(academy_teacher)
    subject = _text((academy_teacher or {}).get("subject"))
    lines = [f"<b>{_escape(title)}</b>", ""]
    if event_type == "teacher_created":
        department = f" and the <b>{_escape(subject)}</b> department" if subject else ""
        lines.append(
            f"Hello <b>{_escape(teacher_name)}</b>, welcome to the MSI School family{department}."
        )
        lines.append("We are happy to have you with us.")
        lines.append(f"\nSource: {_escape(source)}")
        return "\n".join(lines)

    lines.append(f"Teacher: <b>{_escape(teacher_name)}</b>")
    if subject:
        lines.append(f"Department: <b>{_escape(subject)}</b>")
    lesson = _lesson_display(assignment)
    if lesson:
        lines.append(f"Lesson: <b>{_escape(lesson)}</b>")
    session_datetime = _text((assignment or {}).get("session_datetime"))
    if session_datetime:
        lines.append(f"Time: <b>{_escape(session_datetime)}</b>")
    decision = _text((assessment or {}).get("decision"))
    if decision:
        lines.append(f"Decision: <b>{_escape(decision.replace('_', ' ').title())}</b>")
    if body:
        lines.extend(["", _escape(body)])
    lines.append(f"\nSource: {_escape(source)}")
    return "\n".join(lines)


def _teacher_message(
    *,
    academy_teacher: dict[str, Any] | None,
    event_type: str,
    title: str,
    body: str,
    assignment: dict[str, Any] | None,
    assessment: dict[str, Any] | None,
    lessons_count: int,
) -> str:
    teacher_name = _teacher_display(academy_teacher)
    subject = _text((academy_teacher or {}).get("subject"))
    lines = [f"<b>{_escape(title)}</b>", ""]
    if event_type == "teacher_created":
        department = f" and the <b>{_escape(subject)}</b> department" if subject else ""
        lines.append(
            f"Hello <b>{_escape(teacher_name)}</b>, welcome to the MSI School family{department}."
        )
        lines.append("We are happy to have you with us.")
        portal_url = _portal_url()
        if portal_url:
            lines.extend(["", f"Open portal: {_escape(portal_url)}"])
        return "\n".join(lines)

    lesson = _lesson_display(assignment)
    if lesson:
        lines.append(f"Lesson: <b>{_escape(lesson)}</b>")
    session_datetime = _text((assignment or {}).get("session_datetime"))
    if session_datetime:
        lines.append(f"Time: <b>{_escape(session_datetime)}</b>")
    decision = _text((assessment or {}).get("decision"))
    if decision:
        lines.append(f"Decision: <b>{_escape(decision.replace('_', ' ').title())}</b>")
    if body:
        lines.extend(["", _escape(body)])
    portal_url = _portal_url()
    if portal_url:
        lines.extend(["", f"Open portal: {_escape(portal_url)}"])
    return "\n".join(lines)


def notify_academy_teacher_event(
    *,
    academy_teacher: dict[str, Any] | None = None,
    event_type: str,
    title: str = "",
    body: str = "",
    source: str = "Academic Department",
    assignment: dict[str, Any] | None = None,
    assessment: dict[str, Any] | None = None,
    lessons_count: int = 0,
) -> dict[str, Any]:
    """Return a safe in-app/Telegram notification result."""
    normalized_type = _text(event_type) or "academy_update"
    normalized_title = _text(title) or ACADEMY_EVENT_LABELS.get(normalized_type, "Teacher Academy update")
    normalized_body = _text(body)
    normalized_source = _text(source) or "Academic Department"

    channel_sent = False
    teacher_sent = False
    reasons: list[str] = []

    channel_chat_id = _channel_chat_id(academy_teacher)
    if channel_chat_id:
        channel_sent, channel_reason = _send_telegram_message(
            channel_chat_id,
            _channel_message(
                academy_teacher=academy_teacher,
                event_type=normalized_type,
                title=normalized_title,
                body=normalized_body,
                assignment=assignment,
                assessment=assessment,
                lessons_count=max(0, int(lessons_count or 0)),
                source=normalized_source,
            ),
        )
        if channel_reason:
            reasons.append(channel_reason)

    teacher_chat_id = _int_or_none((academy_teacher or {}).get("telegram_user_id"))
    if teacher_chat_id:
        teacher_sent, teacher_reason = _send_telegram_message(
            teacher_chat_id,
            _teacher_message(
                academy_teacher=academy_teacher,
                event_type=normalized_type,
                title=normalized_title,
                body=normalized_body,
                assignment=assignment,
                assessment=assessment,
                lessons_count=max(0, int(lessons_count or 0)),
            ),
        )
        if teacher_reason:
            reasons.append(teacher_reason)
    elif not _has_telegram_link(academy_teacher):
        reasons.append("telegram_link_missing")

    telegram_sent = bool(channel_sent or teacher_sent)
    return {
        "ok": True,
        "event_type": normalized_type,
        "title": normalized_title,
        "body": normalized_body,
        "source": normalized_source,
        "in_app_available": True,
        "telegram_sent": telegram_sent,
        "channel_sent": channel_sent,
        "teacher_sent": teacher_sent,
        "reason": "" if telegram_sent else (reasons[0] if reasons else "telegram_channel_missing"),
        "reasons": reasons,
    }


__all__ = [
    "ACADEMY_EVENT_LABELS",
    "TEACHER_ACADEMY_CHANNEL_ENV",
    "notify_academy_teacher_event",
]
