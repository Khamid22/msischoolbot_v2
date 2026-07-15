"""Persistent Recruitment notifications and best-effort Telegram delivery."""

from __future__ import annotations

import html
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib import error as urlerror
from urllib import request

from backend.core.database import connect_auth_db
from backend.modules.hr.recruitment import repository


LOGGER = logging.getLogger(__name__)
TELEGRAM_TIMEOUT_SECONDS = 5
RETRY_DELAYS_MINUTES = (1, 5, 15, 60, 180, 720)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return _text(value)


def _portal_base_url() -> str:
    return _text(os.getenv("MINI_APP_URL") or os.getenv("APP_BASE_URL")).rstrip("/")


def _candidate_action_url(candidate_id: int, recipient_role: str = "") -> str:
    base = "/head-of-departments/recruitment" if recipient_role == "head_of_department" else "/academic-director/recruitment"
    return f"{base}/candidates/{int(candidate_id)}?tab=evaluations"


def _display_time(value: Any) -> str:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
        from zoneinfo import ZoneInfo

        return parsed.astimezone(ZoneInfo("Asia/Tashkent")).strftime("%d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return _text(value)


def _notification_copy(event_type: str, *, candidate_name: str, starts_at: Any, topic: str = "") -> tuple[str, str]:
    when = _display_time(starts_at)
    topic_suffix = f" · {topic}" if topic else ""
    copies = {
        "demo_assigned": ("Demo lesson assigned", f"{candidate_name} · {when}{topic_suffix}"),
        "demo_rescheduled": ("Demo lesson rescheduled", f"{candidate_name} · New time: {when}{topic_suffix}"),
        "demo_cancelled": ("Demo lesson cancelled", f"{candidate_name} · {when}"),
        "demo_no_show": ("Demo lesson marked no-show", f"{candidate_name} · {when}"),
        "demo_completed": ("Demo lesson completed", f"{candidate_name} · {when}"),
        "demo_evaluated": ("Demo lesson evaluated", f"{candidate_name} · {when}"),
        "demo_reminder_24h": ("Demo lesson tomorrow", f"{candidate_name} · {when}{topic_suffix}"),
        "demo_reminder_1h": ("Demo lesson in one hour", f"{candidate_name} · {when}{topic_suffix}"),
        "demo_link_summary": ("Upcoming assigned demo", f"{candidate_name} · {when}{topic_suffix}"),
    }
    return copies[event_type]


def _insert_notification(
    conn: Any,
    *,
    recipient_account_id: int,
    candidate_id: int,
    appointment_id: int,
    event_type: str,
    candidate_name: str,
    starts_at: Any,
    topic: str,
    deliver_at: Any,
    dedupe_key: str,
    recipient_role: str = "",
) -> None:
    title, body = _notification_copy(
        event_type,
        candidate_name=candidate_name,
        starts_at=starts_at,
        topic=topic,
    )
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
            "dedupe_key": dedupe_key,
        },
    )


def cancel_demo_reminders(conn: Any, appointment_id: int) -> None:
    if not hasattr(conn, "execute"):
        return
    repository.cancel_recruitment_notification_reminders(conn, int(appointment_id))


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
    recipient_id = int(appointment["responsible_account_id"] or 0)
    if recipient_id <= 0 or _text(appointment["appointment_type"]) != "demo_lesson":
        return
    appointment_id = int(appointment["id"])
    candidate_id = int(appointment["candidate_id"])
    starts_at = appointment["starts_at"]
    candidate_name = _text(appointment.get("candidate_name") if hasattr(appointment, "get") else appointment["candidate_name"])
    topic = _text(appointment.get("topic") if hasattr(appointment, "get") else appointment["topic"])
    now = datetime.now(UTC)
    _insert_notification(
        conn,
        recipient_account_id=recipient_id,
        candidate_id=candidate_id,
        appointment_id=appointment_id,
        event_type=event_type,
        candidate_name=candidate_name,
        starts_at=starts_at,
        topic=topic,
        deliver_at=now,
        dedupe_key=f"appointment:{appointment_id}:{event_type}:{version_token}",
        recipient_role=_text(appointment.get("responsible_role") if hasattr(appointment, "get") else appointment["responsible_role"]),
    )
    if not include_reminders:
        return
    cancel_demo_reminders(conn, appointment_id)
    parsed_start = starts_at if isinstance(starts_at, datetime) else datetime.fromisoformat(_text(starts_at).replace("Z", "+00:00"))
    if parsed_start.tzinfo is None:
        parsed_start = parsed_start.replace(tzinfo=UTC)
    for hours, reminder_type in ((24, "demo_reminder_24h"), (1, "demo_reminder_1h")):
        deliver_at = parsed_start.astimezone(UTC) - timedelta(hours=hours)
        if deliver_at <= now:
            continue
        _insert_notification(
            conn,
            recipient_account_id=recipient_id,
            candidate_id=candidate_id,
            appointment_id=appointment_id,
            event_type=reminder_type,
            candidate_name=candidate_name,
            starts_at=starts_at,
            topic=topic,
            deliver_at=deliver_at,
            dedupe_key=f"appointment:{appointment_id}:{reminder_type}:{version_token}",
            recipient_role=_text(appointment.get("responsible_role") if hasattr(appointment, "get") else appointment["responsible_role"]),
        )


def enqueue_linked_account_summary(conn: Any, account_id: int) -> None:
    rows = repository.list_future_demo_appointments_for_recipient(conn, int(account_id))
    for row in rows:
        _insert_notification(
            conn,
            recipient_account_id=int(account_id),
            candidate_id=int(row["candidate_id"]),
            appointment_id=int(row["id"]),
            event_type="demo_link_summary",
            candidate_name=_text(row["candidate_name"]),
            starts_at=row["starts_at"],
            topic=_text(row["topic"]),
            deliver_at=datetime.now(UTC),
            dedupe_key=f"appointment:{int(row['id'])}:demo_link_summary:{int(account_id)}",
            recipient_role=_text(row["responsible_role"]),
        )


def list_notifications(account_id: int, *, page: int = 1, per_page: int = 25) -> dict[str, Any]:
    offset = (max(1, page) - 1) * per_page
    with connect_auth_db() as conn:
        rows, total = repository.list_recruitment_notification_rows(
            conn,
            account_id=int(account_id),
            limit=int(per_page),
            offset=int(offset),
        )
    return {
        "items": [
            {
                **dict(row),
                **{key: value.isoformat() for key, value in dict(row).items() if isinstance(value, datetime)},
            }
            for row in rows
        ],
        "page": max(1, page),
        "per_page": per_page,
        "total": total,
    }


def unread_count(account_id: int) -> int:
    with connect_auth_db() as conn:
        return repository.recruitment_notification_unread_count(conn, int(account_id))


def mark_notification_read(account_id: int, notification_id: int) -> bool:
    with connect_auth_db() as conn:
        updated = repository.mark_recruitment_notification_read(
            conn,
            account_id=int(account_id),
            notification_id=int(notification_id),
        )
        conn.commit()
    return updated


def _send_telegram(chat_id: int, *, title: str, body: str, action_url: str) -> tuple[bool, str]:
    token = _text(os.getenv("BOT_TOKEN"))
    if not token:
        return False, "telegram_bot_token_missing"
    absolute_url = f"{_portal_base_url()}{action_url}" if _portal_base_url() and action_url else ""
    lines = [f"<b>{html.escape(title)}</b>", html.escape(body)]
    if absolute_url:
        lines.extend(["", f'<a href="{html.escape(absolute_url)}">Open Recruitment</a>'])
    payload = json.dumps(
        {
            "chat_id": int(chat_id),
            "text": "\n".join(lines),
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
        with request.urlopen(req, timeout=TELEGRAM_TIMEOUT_SECONDS) as response:
            return (200 <= int(response.status) < 300), ""
    except (OSError, urlerror.URLError, urlerror.HTTPError) as exc:
        return False, f"telegram_send_failed:{type(exc).__name__}"


def process_due_notifications(*, limit: int = 25) -> int:
    """Claim and deliver due rows. SKIP LOCKED makes concurrent workers safe."""

    claimed: list[dict[str, Any]] = []
    with connect_auth_db() as conn:
        repository.recover_stale_recruitment_notification_deliveries(conn)
        rows = repository.claimable_recruitment_notification_rows(conn, int(limit))
        for row in rows:
            if not row["telegram_user_id"]:
                repository.mark_recruitment_notification_waiting_link(conn, int(row["id"]))
                continue
            repository.mark_recruitment_notification_sending(conn, int(row["id"]))
            claimed.append(dict(row))
        conn.commit()

    delivered = 0
    for row in claimed:
        ok, error = _send_telegram(
            int(row["telegram_user_id"]),
            title=_text(row["title"]),
            body=_text(row["body"]),
            action_url=_text(row["action_url"]),
        )
        attempts = int(row["telegram_attempts"] or 0) + 1
        delay = RETRY_DELAYS_MINUTES[min(attempts - 1, len(RETRY_DELAYS_MINUTES) - 1)]
        with connect_auth_db() as conn:
            if ok:
                repository.mark_recruitment_notification_sent(
                    conn,
                    notification_id=int(row["id"]),
                    attempts=attempts,
                )
                delivered += 1
            else:
                repository.mark_recruitment_notification_failed(
                    conn,
                    notification_id=int(row["id"]),
                    attempts=attempts,
                    retry_delay_minutes=delay,
                    error=error,
                )
                LOGGER.warning("Recruitment Telegram delivery failed notification_id=%s error=%s", row["id"], error)
            conn.commit()
    return delivered


__all__ = [
    "cancel_demo_reminders",
    "enqueue_demo_event",
    "enqueue_linked_account_summary",
    "list_notifications",
    "mark_notification_read",
    "process_due_notifications",
    "unread_count",
]
