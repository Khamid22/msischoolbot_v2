"""Persistent, browser-only Recruitment notifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.database import connect_auth_db
from backend.modules.hr.recruitment import repository
from backend.modules.hr.recruitment.errors import RecruitmentError


REMINDER_ROLES = frozenset(
    {"hr_manager", "academic_director", "head_of_department"}
)
DEFAULT_LEAD_MINUTES = 15


def _text(value: Any) -> str:
    return str(value or "").strip()


def _row_value(row: Any, key: str, default: Any = "") -> Any:
    if row is None:
        return default
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, TypeError):
        return default


def _as_utc(value: Any) -> datetime:
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso(value: Any) -> str:
    return _as_utc(value).isoformat() if value else ""


def _candidate_action_url(candidate_id: int, recipient_role: str = "") -> str:
    base = {
        "hr_manager": "/hr-manager",
        "head_of_department": "/head-of-departments/recruitment",
    }.get(recipient_role, "/academic-director/recruitment")
    return f"{base}/candidates/{int(candidate_id)}?tab=evaluations"


def _display_time(value: Any) -> str:
    try:
        from zoneinfo import ZoneInfo

        return _as_utc(value).astimezone(ZoneInfo("Asia/Tashkent")).strftime(
            "%d %b %Y, %H:%M"
        )
    except (TypeError, ValueError):
        return _text(value)


def _notification_copy(
    event_type: str,
    *,
    candidate_name: str,
    starts_at: Any,
    topic: str = "",
) -> tuple[str, str]:
    when = _display_time(starts_at)
    topic_suffix = f" · {topic}" if topic else ""
    copies = {
        "demo_assigned": ("Demo lesson assigned", f"{candidate_name} · {when}{topic_suffix}"),
        "demo_rescheduled": ("Demo lesson rescheduled", f"{candidate_name} · New time: {when}{topic_suffix}"),
        "demo_cancelled": ("Demo lesson cancelled", f"{candidate_name} · {when}"),
        "demo_no_show": ("Demo lesson marked no-show", f"{candidate_name} · {when}"),
        "demo_completed": ("Demo lesson completed", f"{candidate_name} · {when}"),
        "demo_evaluated": ("Demo lesson evaluated", f"{candidate_name} · {when}"),
    }
    return copies[event_type]


def _insert_notification(
    conn: Any,
    *,
    recipient_account_id: int,
    candidate_id: int,
    appointment_id: int,
    event_type: str,
    title: str,
    body: str,
    deliver_at: Any,
    dedupe_key: str,
    recipient_role: str = "",
) -> None:
    repository.insert_recruitment_notification(
        conn,
        values={
            "recipient_account_id": int(recipient_account_id),
            "candidate_id": int(candidate_id),
            "appointment_id": int(appointment_id),
            "notification_type": event_type,
            "title": title,
            "body": body,
            "action_url": _candidate_action_url(candidate_id, recipient_role),
            "deliver_at": _iso(deliver_at),
            "telegram_status": "cancelled",
            "dedupe_key": dedupe_key,
        },
    )


def cancel_appointment_reminders(conn: Any, appointment_id: int) -> None:
    if hasattr(conn, "execute"):
        repository.cancel_recruitment_notification_reminders(
            conn, int(appointment_id)
        )


def cancel_demo_reminders(conn: Any, appointment_id: int) -> None:
    """Compatibility alias retained for evaluation and handoff services."""

    cancel_appointment_reminders(conn, appointment_id)


def _reminder_config(conn: Any) -> dict[str, Any]:
    row = repository.recruitment_reminder_config_row(conn)
    if not row:
        return {"lead_minutes": DEFAULT_LEAD_MINUTES, "version": 1}
    return dict(row)


def reminder_config() -> dict[str, Any]:
    with connect_auth_db() as conn:
        return _reminder_config(conn)


def enqueue_appointment_reminders(
    conn: Any,
    *,
    appointment: Any,
    version_token: str | int,
) -> None:
    """Create one reminder per recipient unless this is a short-notice booking."""

    if not hasattr(conn, "execute"):
        return
    appointment_id = int(_row_value(appointment, "id", 0) or 0)
    candidate_id = int(_row_value(appointment, "candidate_id", 0) or 0)
    if appointment_id <= 0 or candidate_id <= 0:
        return
    cancel_appointment_reminders(conn, appointment_id)
    config = _reminder_config(conn)
    lead_minutes = int(config.get("lead_minutes") or DEFAULT_LEAD_MINUTES)
    starts_at = _as_utc(_row_value(appointment, "starts_at"))
    deliver_at = starts_at - timedelta(minutes=lead_minutes)
    now = datetime.now(UTC)
    if deliver_at <= now:
        return

    appointment_type = _text(_row_value(appointment, "appointment_type"))
    candidate_name = _text(_row_value(appointment, "candidate_name")) or "Candidate"
    subject = _text(_row_value(appointment, "subject"))
    topic = _text(_row_value(appointment, "topic"))
    body_parts = [candidate_name]
    if subject:
        body_parts.append(subject)
    body_parts.append(_display_time(starts_at))
    if appointment_type == "demo_lesson" and topic:
        body_parts.append(topic)
    title = (
        f"Job interview in {lead_minutes} minutes"
        if appointment_type == "job_interview"
        else f"Demo lesson in {lead_minutes} minutes"
    )

    recipient_roles: dict[int, str] = {}
    scheduler_id = int(
        _row_value(appointment, "created_by_account_id", 0)
        or _row_value(appointment, "responsible_account_id", 0)
        or 0
    )
    scheduler_role = _text(
        _row_value(appointment, "created_by_role")
        or (
            _row_value(appointment, "responsible_role")
            if scheduler_id
            == int(_row_value(appointment, "responsible_account_id", 0) or 0)
            else "hr_manager"
        )
    )
    if scheduler_id > 0:
        recipient_roles[scheduler_id] = scheduler_role or "hr_manager"
    if appointment_type == "demo_lesson":
        evaluator_id = int(_row_value(appointment, "responsible_account_id", 0) or 0)
        if evaluator_id > 0:
            recipient_roles[evaluator_id] = (
                _text(_row_value(appointment, "responsible_role"))
                or recipient_roles.get(evaluator_id, "academic_director")
            )

    for recipient_id, recipient_role in recipient_roles.items():
        if recipient_role not in REMINDER_ROLES:
            continue
        _insert_notification(
            conn,
            recipient_account_id=recipient_id,
            candidate_id=candidate_id,
            appointment_id=appointment_id,
            event_type="appointment_reminder",
            title=title,
            body=" · ".join(body_parts),
            deliver_at=deliver_at,
            dedupe_key=(
                f"appointment:{appointment_id}:appointment_reminder:"
                f"{version_token}:{recipient_id}:lead:{lead_minutes}"
            ),
            recipient_role=recipient_role,
        )


def enqueue_demo_event(
    conn: Any,
    *,
    appointment: Any,
    event_type: str,
    version_token: str | int,
    include_reminders: bool = False,
) -> None:
    if not hasattr(conn, "execute"):
        return
    if include_reminders:
        enqueue_appointment_reminders(
            conn, appointment=appointment, version_token=version_token
        )
    if _text(_row_value(appointment, "appointment_type")) != "demo_lesson":
        return
    recipient_id = int(_row_value(appointment, "responsible_account_id", 0) or 0)
    if recipient_id <= 0:
        return
    candidate_id = int(_row_value(appointment, "candidate_id", 0) or 0)
    appointment_id = int(_row_value(appointment, "id", 0) or 0)
    starts_at = _row_value(appointment, "starts_at")
    title, body = _notification_copy(
        event_type,
        candidate_name=_text(_row_value(appointment, "candidate_name")),
        starts_at=starts_at,
        topic=_text(_row_value(appointment, "topic")),
    )
    _insert_notification(
        conn,
        recipient_account_id=recipient_id,
        candidate_id=candidate_id,
        appointment_id=appointment_id,
        event_type=event_type,
        title=title,
        body=body,
        deliver_at=datetime.now(UTC),
        dedupe_key=f"appointment:{appointment_id}:{event_type}:{version_token}",
        recipient_role=_text(_row_value(appointment, "responsible_role")),
    )


def list_notifications(
    account_id: int,
    *,
    page: int = 1,
    per_page: int = 25,
    unread_only: bool = False,
) -> dict[str, Any]:
    offset = (max(1, page) - 1) * per_page
    with connect_auth_db() as conn:
        rows, total = repository.list_recruitment_notification_rows(
            conn,
            account_id=int(account_id),
            limit=int(per_page),
            offset=int(offset),
            unread_only=bool(unread_only),
        )
    return {
        "items": [dict(row) for row in rows],
        "page": max(1, page),
        "per_page": per_page,
        "total": total,
    }


def unread_count(account_id: int) -> int:
    with connect_auth_db() as conn:
        return repository.recruitment_notification_unread_count(conn, int(account_id))


def unreviewed_candidate_count(account_id: int) -> int:
    with connect_auth_db() as conn:
        return repository.recruitment_unreviewed_candidate_count(
            conn,
            int(account_id),
        )


def mark_notification_read(account_id: int, notification_id: int) -> bool:
    with connect_auth_db() as conn:
        updated = repository.mark_recruitment_notification_read(
            conn,
            account_id=int(account_id),
            notification_id=int(notification_id),
        )
        conn.commit()
    return updated


def mark_candidate_reviewed(account_id: int, candidate_id: int) -> int:
    with connect_auth_db() as conn:
        updated_count = repository.mark_recruitment_candidate_notifications_read(
            conn,
            account_id=int(account_id),
            candidate_id=int(candidate_id),
        )
        conn.commit()
    return updated_count


def browser_preference(account_id: int) -> dict[str, Any]:
    with connect_auth_db() as conn:
        row = repository.browser_preference_row(conn, int(account_id))
    return (
        dict(row)
        if row
        else {"account_id": int(account_id), "enabled": False, "version": 0}
    )


def update_browser_preference(
    account_id: int,
    *,
    enabled: bool,
    expected_version: int,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    with connect_auth_db() as conn:
        row = repository.update_browser_preference(
            conn,
            account_id=int(account_id),
            enabled=bool(enabled),
            expected_version=int(expected_version),
            now=now,
        )
        if not row:
            raise RecruitmentError(
                "Browser reminder settings changed elsewhere. Refresh and try again.",
                status_code=409,
            )
        conn.commit()
    return dict(row)


def claim_browser_alerts(account_id: int, *, limit: int = 10) -> dict[str, Any]:
    with connect_auth_db() as conn:
        rows = repository.claim_due_browser_alert_rows(
            conn,
            account_id=int(account_id),
            limit=max(1, min(int(limit), 25)),
        )
        conn.commit()
    return {"items": [dict(row) for row in rows]}


def browser_test_alert(lead_minutes: int = DEFAULT_LEAD_MINUTES) -> dict[str, Any]:
    return {
        "id": 0,
        "candidate_id": 0,
        "appointment_id": 0,
        "title": f"Demo lesson in {int(lead_minutes)} minutes",
        "body": "Test Candidate · IGCSE Mathematics A · 11:00 AM",
        "action_url": "",
        "is_test": True,
    }


__all__ = [
    "browser_preference",
    "browser_test_alert",
    "cancel_appointment_reminders",
    "cancel_demo_reminders",
    "claim_browser_alerts",
    "enqueue_appointment_reminders",
    "enqueue_demo_event",
    "list_notifications",
    "mark_candidate_reviewed",
    "mark_notification_read",
    "reminder_config",
    "unread_count",
    "unreviewed_candidate_count",
    "update_browser_preference",
]
