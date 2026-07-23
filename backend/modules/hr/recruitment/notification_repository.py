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
            %s, NULL, %s, now(), now()
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
            values.get("telegram_status", "cancelled"),
            values["dedupe_key"],
        ),
    )


def cancel_recruitment_notification_reminders(conn: Any, appointment_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'cancelled',
            telegram_next_attempt_at = NULL,
            read_at = COALESCE(read_at, now()),
            updated_at = now()
        WHERE appointment_id = %s
          AND notification_type IN (
              'appointment_reminder', 'demo_reminder_24h', 'demo_reminder_1h'
          )
          AND browser_delivered_at IS NULL
        """,
        (int(appointment_id),),
    )


def recruitment_reminder_config_row(conn: Any) -> Any:
    return conn.execute(
        """
        SELECT lead_minutes, version, updated_by_account_id,
               updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_reminder_config
        WHERE id = 1
        """
    ).fetchone()


def update_recruitment_reminder_config(
    conn: Any,
    *,
    lead_minutes: int,
    expected_version: int,
    actor_account_id: int | None,
    now: str,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_reminder_config
        SET lead_minutes = %s,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz,
            version = version + 1
        WHERE id = 1 AND version = %s
        RETURNING lead_minutes, version, updated_by_account_id,
                  updated_at::text AS updated_at
        """,
        (int(lead_minutes), actor_account_id, now, int(expected_version)),
    ).fetchone()


def recalculate_future_appointment_reminders(
    conn: Any,
    *,
    lead_minutes: int,
    config_version: int,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications notification
        SET telegram_status = 'cancelled', telegram_next_attempt_at = NULL,
            read_at = COALESCE(notification.read_at, now()), updated_at = now()
        FROM msi_v2.teacher_candidate_appointments appointment
        WHERE notification.appointment_id = appointment.id
          AND notification.notification_type = 'appointment_reminder'
          AND notification.browser_delivered_at IS NULL
          AND appointment.status = 'scheduled'
          AND appointment.starts_at > now()
        """
    )
    conn.execute(
        """
        WITH recipients AS (
            SELECT appointment.id AS appointment_id,
                   COALESCE(appointment.created_by_account_id, appointment.responsible_account_id) AS recipient_account_id
            FROM msi_v2.teacher_candidate_appointments appointment
            WHERE appointment.status = 'scheduled'
            UNION
            SELECT appointment.id, appointment.responsible_account_id
            FROM msi_v2.teacher_candidate_appointments appointment
            WHERE appointment.status = 'scheduled'
              AND appointment.appointment_type = 'demo_lesson'
        )
        INSERT INTO msi_v2.teacher_recruitment_notifications (
            recipient_account_id, candidate_id, appointment_id,
            notification_type, title, body, action_url, deliver_at,
            telegram_status, telegram_next_attempt_at, dedupe_key,
            created_at, updated_at
        )
        SELECT recipient.id,
               candidate.id,
               appointment.id,
               'appointment_reminder',
               CASE appointment.appointment_type
                   WHEN 'job_interview' THEN 'Job interview in ' || %s || ' minutes'
                   ELSE 'Demo lesson in ' || %s || ' minutes'
               END,
               candidate.full_name || ' · ' ||
                   to_char(appointment.starts_at AT TIME ZONE 'Asia/Tashkent', 'Mon DD, YYYY HH12:MI AM'),
               CASE recipient.role
                   WHEN 'hr_manager' THEN '/hr-manager/candidates/' || candidate.id || '?tab=evaluations'
                   WHEN 'head_of_department' THEN '/head-of-departments/recruitment/candidates/' || candidate.id || '?tab=evaluations'
                   ELSE '/academic-director/recruitment/candidates/' || candidate.id || '?tab=evaluations'
               END,
               appointment.starts_at - (%s || ' minutes')::interval,
               'cancelled', NULL,
               'appointment:' || appointment.id || ':appointment_reminder:' || appointment.version || ':' || recipient.id || ':lead:' || %s || ':config:' || %s,
               now(), now()
        FROM recipients target
        JOIN msi_v2.teacher_candidate_appointments appointment ON appointment.id = target.appointment_id
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        JOIN msi_v2.accounts recipient ON recipient.id = target.recipient_account_id
        WHERE target.recipient_account_id IS NOT NULL
          AND recipient.status = 'active'
          AND recipient.role IN ('hr_manager', 'academic_director', 'head_of_department')
          AND appointment.starts_at - (%s || ' minutes')::interval > now()
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.teacher_recruitment_notifications delivered
              WHERE delivered.appointment_id = appointment.id
                AND delivered.recipient_account_id = recipient.id
                AND delivered.notification_type = 'appointment_reminder'
                AND delivered.browser_delivered_at IS NOT NULL
          )
        ON CONFLICT (dedupe_key) DO NOTHING
        """,
        (
            str(int(lead_minutes)),
            str(int(lead_minutes)),
            str(int(lead_minutes)),
            str(int(lead_minutes)),
            str(int(config_version)),
            str(int(lead_minutes)),
        ),
    )


def browser_preference_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT account_id, enabled, version, updated_at::text AS updated_at
        FROM msi_v2.teacher_recruitment_browser_preferences
        WHERE account_id = %s
        """,
        (int(account_id),),
    ).fetchone()


def update_browser_preference(
    conn: Any,
    *,
    account_id: int,
    enabled: bool,
    expected_version: int,
    now: str,
) -> Any:
    if int(expected_version) == 0:
        return conn.execute(
            """
            INSERT INTO msi_v2.teacher_recruitment_browser_preferences (
                account_id, enabled, version, created_at, updated_at
            ) VALUES (%s, %s, 1, %s::timestamptz, %s::timestamptz)
            ON CONFLICT (account_id) DO NOTHING
            RETURNING account_id, enabled, version, updated_at::text AS updated_at
            """,
            (int(account_id), bool(enabled), now, now),
        ).fetchone()
    return conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_browser_preferences
        SET enabled = %s, version = version + 1,
            updated_at = %s::timestamptz
        WHERE account_id = %s AND version = %s
        RETURNING account_id, enabled, version, updated_at::text AS updated_at
        """,
        (bool(enabled), now, int(account_id), int(expected_version)),
    ).fetchone()


def claim_due_browser_alert_rows(
    conn: Any,
    *,
    account_id: int,
    limit: int,
) -> list[Any]:
    return conn.execute(
        """
        WITH due AS (
            SELECT notification.id
            FROM msi_v2.teacher_recruitment_notifications notification
            JOIN msi_v2.teacher_candidate_appointments appointment
              ON appointment.id = notification.appointment_id
            WHERE notification.recipient_account_id = %s
              AND notification.notification_type = 'appointment_reminder'
              AND notification.deliver_at <= now()
              AND notification.browser_delivered_at IS NULL
              AND notification.read_at IS NULL
              AND appointment.status = 'scheduled'
              AND appointment.starts_at > now()
              AND EXISTS (
                  SELECT 1
                  FROM msi_v2.teacher_recruitment_browser_preferences preference
                  WHERE preference.account_id = %s AND preference.enabled = true
              )
            ORDER BY notification.deliver_at, notification.id
            LIMIT %s
            FOR UPDATE OF notification SKIP LOCKED
        )
        UPDATE msi_v2.teacher_recruitment_notifications notification
        SET browser_delivered_at = now(), updated_at = now()
        FROM due
        WHERE notification.id = due.id
        RETURNING notification.id, notification.candidate_id,
                  notification.appointment_id, notification.title,
                  notification.body, notification.action_url,
                  notification.deliver_at::text AS deliver_at,
                  notification.created_at::text AS created_at
        """,
        (int(account_id), int(account_id), int(limit)),
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
    visible_filter = """
        AND (
            notification_type <> 'appointment_reminder'
            OR browser_delivered_at IS NOT NULL
        )
    """
    total_row = conn.execute(
        f"""
        SELECT count(*) AS total
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s AND deliver_at <= now()
        {visible_filter}
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
        {visible_filter}
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
        WHERE recipient_account_id = %s
          AND read_at IS NULL
          AND deliver_at <= now()
          AND (
              notification_type <> 'appointment_reminder'
              OR browser_delivered_at IS NOT NULL
          )
        """,
        (int(account_id),),
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def unreviewed_recruitment_candidate_ids(
    conn: Any,
    *,
    account_id: int,
    candidate_ids: list[int],
) -> set[int]:
    if not candidate_ids:
        return set()
    rows = conn.execute(
        """
        SELECT DISTINCT candidate_id
        FROM msi_v2.teacher_recruitment_notifications
        WHERE recipient_account_id = %s
          AND candidate_id = ANY(%s::bigint[])
          AND read_at IS NULL
          AND deliver_at <= now()
          AND (
              notification_type <> 'appointment_reminder'
              OR browser_delivered_at IS NOT NULL
          )
        """,
        (int(account_id), [int(candidate_id) for candidate_id in candidate_ids]),
    ).fetchall()
    return {int(row["candidate_id"]) for row in rows}


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


def mark_recruitment_candidate_notifications_read(
    conn: Any,
    *,
    account_id: int,
    candidate_id: int,
) -> int:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_recruitment_notifications
        SET read_at = COALESCE(read_at, now()), updated_at = now()
        WHERE recipient_account_id = %s
          AND candidate_id = %s
          AND read_at IS NULL
          AND deliver_at <= now()
          AND (
              notification_type <> 'appointment_reminder'
              OR browser_delivered_at IS NOT NULL
          )
        """,
        (int(account_id), int(candidate_id)),
    )
    return int(getattr(cursor, "rowcount", 0) or 0)


__all__ = [
    "browser_preference_row",
    "cancel_recruitment_notification_reminders",
    "claim_due_browser_alert_rows",
    "insert_recruitment_notification",
    "list_recruitment_notification_rows",
    "mark_recruitment_candidate_notifications_read",
    "mark_recruitment_notification_read",
    "recalculate_future_appointment_reminders",
    "recruitment_notification_unread_count",
    "recruitment_reminder_config_row",
    "unreviewed_recruitment_candidate_ids",
    "update_browser_preference",
    "update_recruitment_reminder_config",
]
