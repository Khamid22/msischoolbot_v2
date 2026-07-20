"""PostgreSQL persistence for Recruitment notifications."""

from __future__ import annotations

from typing import Any


def insert_recruitment_notification(conn: Any, *, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_recruitment_notifications (
            recipient_account_id, candidate_id, appointment_id,
            notification_type, title, body, action_url, deliver_at,
            telegram_status, telegram_next_attempt_at, dedupe_key,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s::timestamptz,
            'pending', %s::timestamptz, %s, now(), now()
        )
        ON CONFLICT (dedupe_key) DO NOTHING
        """,
        (
            int(values["recipient_account_id"]),
            int(values["candidate_id"]),
            int(values["appointment_id"]),
            values["notification_type"],
            values["title"],
            values["body"],
            values["action_url"],
            values["deliver_at"],
            values["deliver_at"],
            values["dedupe_key"],
        ),
    )


def cancel_recruitment_notification_reminders(conn: Any, appointment_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'cancelled', updated_at = now()
        WHERE appointment_id = %s
          AND notification_type IN ('demo_reminder_24h', 'demo_reminder_1h')
          AND telegram_status IN ('pending', 'waiting_link', 'failed')
        """,
        (int(appointment_id),),
    )


def list_future_demo_appointments_for_recipient(
    conn: Any, account_id: int
) -> list[Any]:
    return conn.execute(
        """
        SELECT appointment.id, appointment.candidate_id, appointment.appointment_type,
               appointment.starts_at, appointment.topic,
               appointment.responsible_account_id, candidate.full_name AS candidate_name,
               account.role AS responsible_role
        FROM msi_v2.teacher_candidate_appointments appointment
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        JOIN msi_v2.accounts account ON account.id = appointment.responsible_account_id
        WHERE appointment.responsible_account_id = %s
          AND appointment.appointment_type = 'demo_lesson'
          AND appointment.status = 'scheduled'
          AND appointment.starts_at > now()
        ORDER BY appointment.starts_at ASC
        """,
        (int(account_id),),
    ).fetchall()


def list_recruitment_notification_rows(
    conn: Any,
    *,
    account_id: int,
    limit: int,
    offset: int,
    unread_only: bool = False,
) -> tuple[list[Any], int]:
    unread_filter = " AND read_at IS NULL" if unread_only else ""
    total_row = conn.execute(
        f"""
        SELECT count(*) AS total
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND deliver_at <= now()
        {unread_filter}
        """,
        (int(account_id),),
    ).fetchone()
    rows = conn.execute(
        f"""
        SELECT id, candidate_id, appointment_id, notification_type, title,
               body, action_url, deliver_at, read_at, created_at
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND deliver_at <= now()
        {unread_filter}
        ORDER BY created_at DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        (int(account_id), int(limit), int(offset)),
    ).fetchall()
    return rows, int(total_row["total"] or 0) if total_row else 0


def recruitment_notification_unread_count(conn: Any, account_id: int) -> int:
    row = conn.execute(
        """
        SELECT count(*) AS total
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND read_at IS NULL AND deliver_at <= now()
        """,
        (int(account_id),),
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def mark_recruitment_notification_read(
    conn: Any, *, account_id: int, notification_id: int
) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET read_at = COALESCE(read_at, now()), updated_at = now()
        WHERE id = %s AND recipient_account_id = %s
        """,
        (int(notification_id), int(account_id)),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def recover_stale_recruitment_notification_deliveries(conn: Any) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'failed', telegram_locked_at = NULL,
            telegram_next_attempt_at = now(),
            telegram_last_error = 'delivery_worker_recovered_after_restart',
            updated_at = now()
        WHERE telegram_status = 'sending'
          AND telegram_locked_at < now() - interval '10 minutes'
        """
    )


def claimable_recruitment_notification_rows(conn: Any, limit: int) -> list[Any]:
    return conn.execute(
        """
        SELECT notification.id, notification.title, notification.body,
               notification.action_url, notification.telegram_attempts,
               link.telegram_user_id
        FROM msi_v2.teacher_recruitment_notifications notification
        LEFT JOIN msi_v2.account_telegram_links link
          ON link.account_id = notification.recipient_account_id
         AND link.status = 'active'
        WHERE notification.telegram_status IN ('pending', 'failed', 'waiting_link')
          AND COALESCE(notification.telegram_next_attempt_at, notification.deliver_at) <= now()
          AND notification.deliver_at <= now()
        ORDER BY COALESCE(notification.telegram_next_attempt_at, notification.deliver_at), notification.id
        LIMIT %s
        FOR UPDATE OF notification SKIP LOCKED
        """,
        (int(limit),),
    ).fetchall()


def mark_recruitment_notification_waiting_link(conn: Any, notification_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'waiting_link',
            telegram_next_attempt_at = now() + interval '6 hours',
            telegram_last_error = 'telegram_account_not_linked', updated_at = now()
        WHERE id = %s
        """,
        (int(notification_id),),
    )


def mark_recruitment_notification_sending(conn: Any, notification_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'sending', telegram_locked_at = now(), updated_at = now()
        WHERE id = %s
        """,
        (int(notification_id),),
    )


def mark_recruitment_notification_sent(
    conn: Any, *, notification_id: int, attempts: int
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'sent', telegram_attempts = %s,
            telegram_sent_at = now(), telegram_next_attempt_at = NULL,
            telegram_last_error = '', telegram_locked_at = NULL, updated_at = now()
        WHERE id = %s AND telegram_status = 'sending'
        """,
        (int(attempts), int(notification_id)),
    )


def mark_recruitment_notification_failed(
    conn: Any,
    *,
    notification_id: int,
    attempts: int,
    retry_delay_minutes: int,
    error: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'failed', telegram_attempts = %s,
            telegram_next_attempt_at = now() + (%s || ' minutes')::interval,
            telegram_last_error = %s, telegram_locked_at = NULL, updated_at = now()
        WHERE id = %s AND telegram_status = 'sending'
        """,
        (int(attempts), str(retry_delay_minutes), error[:500], int(notification_id)),
    )


__all__ = [
    "cancel_recruitment_notification_reminders",
    "claimable_recruitment_notification_rows",
    "insert_recruitment_notification",
    "list_future_demo_appointments_for_recipient",
    "list_recruitment_notification_rows",
    "mark_recruitment_notification_failed",
    "mark_recruitment_notification_read",
    "mark_recruitment_notification_sending",
    "mark_recruitment_notification_sent",
    "mark_recruitment_notification_waiting_link",
    "recover_stale_recruitment_notification_deliveries",
    "recruitment_notification_unread_count",
]
