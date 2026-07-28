"""PostgreSQL persistence for invoice timers, household holds, and delivery records."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from backend.core.unit_of_work import Connection
from backend.modules.domains.finance.domain_types import (
    BillingEnforcementState,
    BillingHoldTarget,
    BillingNotificationStage,
)

OPEN_INVOICE_STATUSES = ("issued", "partially_paid", "overdue")


def list_bootstrap_invoice_rows(conn: Connection, *, limit: int = 500) -> list[Any]:
    return conn.execute(
        """
        SELECT invoice.id, invoice.student_id, invoice.due_date,
               COALESCE(invoice.issued_at, invoice.created_at) AS issued_at
        FROM msi_v2.invoices invoice
        JOIN msi_v2.students student ON student.id = invoice.student_id
        LEFT JOIN msi_v2.invoice_enforcement_schedules schedule
          ON schedule.invoice_id = invoice.id
        WHERE invoice.admission_id IS NULL
          AND invoice.student_id IS NOT NULL
          AND invoice.status IN ('issued', 'partially_paid', 'overdue')
          AND invoice.total_minor > invoice.paid_minor
          AND student.status = 'active'
          AND schedule.id IS NULL
        ORDER BY invoice.id
        FOR UPDATE OF invoice SKIP LOCKED
        LIMIT %s
        """,
        (max(1, min(int(limit), 1000)),),
    ).fetchall()


def insert_schedule(
    conn: Connection,
    *,
    invoice_id: int,
    student_id: int,
    countdown_started_at: datetime,
    deadline_at: datetime,
    bootstrap: bool = False,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoice_enforcement_schedules (
            invoice_id, student_id, state, countdown_started_at, deadline_at,
            policy_hours, policy_snapshot, version, created_at, updated_at
        )
        VALUES (
            %s, %s, 'scheduled', %s, %s, 48, %s::jsonb, 1, now(), now()
        )
        ON CONFLICT (invoice_id) DO NOTHING
        RETURNING id
        """,
        (
            int(invoice_id),
            int(student_id),
            countdown_started_at,
            deadline_at,
            json.dumps(
                {
                    "hours": 48,
                    "reminder_hours_remaining": [24, 6],
                    "household_scope": "direct_parents_and_their_students",
                    "bootstrap": bool(bootstrap),
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        ),
    ).fetchone()
    if row:
        return int(row["id"])
    existing = conn.execute(
        """
        SELECT id
        FROM msi_v2.invoice_enforcement_schedules
        WHERE invoice_id = %s
        """,
        (int(invoice_id),),
    ).fetchone()
    return int(existing["id"]) if existing else 0


def get_schedule_row(
    conn: Connection,
    schedule_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF schedule, invoice" if for_update else ""
    return conn.execute(
        f"""
        SELECT schedule.*,
               invoice.invoice_number, invoice.total_minor, invoice.paid_minor,
               invoice.currency, invoice.status AS invoice_status,
               invoice.student_id AS invoice_student_id,
               student.full_name AS student_name,
               student.student_code,
               school.school_name
        FROM msi_v2.invoice_enforcement_schedules schedule
        JOIN msi_v2.invoices invoice ON invoice.id = schedule.invoice_id
        JOIN msi_v2.students student ON student.id = schedule.student_id
        LEFT JOIN msi_v2.schools school ON school.id = student.school_id
        WHERE schedule.id = %s
        {lock}
        """,
        (int(schedule_id),),
    ).fetchone()


def get_schedule_by_invoice_row(
    conn: Connection,
    invoice_id: int,
    *,
    for_update: bool = False,
) -> Any:
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.invoice_enforcement_schedules
        WHERE invoice_id = %s
        """,
        (int(invoice_id),),
    ).fetchone()
    return (
        get_schedule_row(conn, int(row["id"]), for_update=for_update)
        if row
        else None
    )


def set_schedule_state(
    conn: Connection,
    *,
    schedule_id: int,
    state: BillingEnforcementState,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.invoice_enforcement_schedules
        SET state = %s,
            held_at = CASE WHEN %s = 'held' THEN COALESCE(held_at, now()) ELSE held_at END,
            cleared_at = CASE WHEN %s = 'cleared' THEN now() ELSE cleared_at END,
            cancelled_at = CASE WHEN %s = 'cancelled' THEN now() ELSE cancelled_at END,
            version = version + 1,
            updated_at = now()
        WHERE id = %s AND state <> %s
        """,
        (
            state.value,
            state.value,
            state.value,
            state.value,
            int(schedule_id),
            state.value,
        ),
    )


def list_household_target_rows(conn: Connection, student_id: int) -> list[Any]:
    """Return the debtor, direct parents, and those parents' other students."""

    return conn.execute(
        """
        WITH direct_parents AS (
            SELECT link.parent_id
            FROM msi_v2.parent_student_links link
            WHERE link.student_id = %s AND link.status = 'active'
        ),
        target_rows AS (
            SELECT
                'debtor_student'::text AS target_type,
                student.id AS person_id,
                profile.account_id,
                student.full_name AS display_name,
                student.student_code,
                COALESCE(telegram.telegram_user_id, student.telegram_user_id) AS telegram_user_id,
                'uz'::text AS language,
                0 AS target_rank
            FROM msi_v2.students student
            LEFT JOIN msi_v2.student_profiles profile
              ON profile.student_id = student.id
             AND profile.status = 'active'
            LEFT JOIN msi_v2.account_telegram_links telegram
              ON telegram.account_id = profile.account_id
             AND telegram.status = 'active'
            WHERE student.id = %s

            UNION ALL

            SELECT
                'linked_parent',
                parent.id,
                profile.account_id,
                parent.display_name,
                ''::text,
                COALESCE(telegram.telegram_user_id, parent.telegram_user_id),
                CASE WHEN parent.preferred_language = 'ru' THEN 'ru' ELSE 'uz' END,
                1
            FROM direct_parents direct
            JOIN msi_v2.parents parent ON parent.id = direct.parent_id
            LEFT JOIN msi_v2.parent_profiles profile
              ON profile.parent_id = parent.id
             AND profile.status = 'active'
            LEFT JOIN msi_v2.account_telegram_links telegram
              ON telegram.account_id = profile.account_id
             AND telegram.status = 'active'
            WHERE parent.status = 'active'

            UNION ALL

            SELECT
                'household_student',
                sibling.id,
                profile.account_id,
                sibling.full_name,
                sibling.student_code,
                COALESCE(telegram.telegram_user_id, sibling.telegram_user_id),
                'uz',
                2
            FROM direct_parents direct
            JOIN msi_v2.parent_student_links sibling_link
              ON sibling_link.parent_id = direct.parent_id
             AND sibling_link.status = 'active'
            JOIN msi_v2.students sibling ON sibling.id = sibling_link.student_id
            LEFT JOIN msi_v2.student_profiles profile
              ON profile.student_id = sibling.id
             AND profile.status = 'active'
            LEFT JOIN msi_v2.account_telegram_links telegram
              ON telegram.account_id = profile.account_id
             AND telegram.status = 'active'
            WHERE sibling.id <> %s AND sibling.status = 'active'
        )
        SELECT DISTINCT ON (
            COALESCE(account_id::text, target_type || ':' || person_id::text)
        )
               target_type, person_id, account_id, display_name, student_code,
               telegram_user_id, language
        FROM target_rows
        ORDER BY
            COALESCE(account_id::text, target_type || ':' || person_id::text),
            target_rank
        """,
        (int(student_id), int(student_id), int(student_id)),
    ).fetchall()


def activate_household_holds(
    conn: Connection,
    *,
    schedule_id: int,
    targets: Iterable[Any],
) -> None:
    for target in targets:
        if target["account_id"] is None:
            continue
        conn.execute(
            """
            INSERT INTO msi_v2.billing_access_holds (
                schedule_id, account_id, target_type, status,
                activated_at, released_at, release_reason, created_at, updated_at
            )
            VALUES (%s, %s, %s, 'active', now(), NULL, '', now(), now())
            ON CONFLICT (schedule_id, account_id) DO UPDATE
            SET target_type = EXCLUDED.target_type,
                status = 'active',
                activated_at = CASE
                    WHEN msi_v2.billing_access_holds.status = 'released'
                    THEN now()
                    ELSE msi_v2.billing_access_holds.activated_at
                END,
                released_at = NULL,
                release_reason = '',
                updated_at = now()
            """,
            (
                int(schedule_id),
                int(target["account_id"]),
                str(target["target_type"]),
            ),
        )


def release_schedule_holds(
    conn: Connection,
    *,
    schedule_id: int,
    reason: str,
) -> list[int]:
    rows = conn.execute(
        """
        UPDATE msi_v2.billing_access_holds
        SET status = 'released', released_at = now(),
            release_reason = %s, updated_at = now()
        WHERE schedule_id = %s AND status = 'active'
        RETURNING account_id
        """,
        (reason.strip(), int(schedule_id)),
    ).fetchall()
    return [int(row["account_id"]) for row in rows]


def release_removed_household_holds(
    conn: Connection,
    *,
    schedule_id: int,
    active_account_ids: Iterable[int],
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.billing_access_holds
        SET status = 'released', released_at = now(),
            release_reason = 'household_membership_changed', updated_at = now()
        WHERE schedule_id = %s
          AND status = 'active'
          AND NOT (account_id = ANY(%s::bigint[]))
        """,
        (int(schedule_id), list(active_account_ids)),
    )


def account_has_active_hold(conn: Connection, account_id: int) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM msi_v2.billing_access_holds
        WHERE account_id = %s AND status = 'active'
        LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()
    return bool(row)


def list_account_enforcement_rows(conn: Connection, account_id: int) -> list[Any]:
    return conn.execute(
        """
        WITH target_schedules AS (
            SELECT schedule.id AS schedule_id, 'debtor_student'::text AS target_type
            FROM msi_v2.invoice_enforcement_schedules schedule
            JOIN msi_v2.student_profiles profile
              ON profile.student_id = schedule.student_id
            WHERE profile.account_id = %s

            UNION

            SELECT schedule.id, 'linked_parent'
            FROM msi_v2.invoice_enforcement_schedules schedule
            JOIN msi_v2.parent_student_links link
              ON link.student_id = schedule.student_id
             AND link.status = 'active'
            JOIN msi_v2.parent_profiles profile
              ON profile.parent_id = link.parent_id
            WHERE profile.account_id = %s

            UNION

            SELECT schedule.id, 'household_student'
            FROM msi_v2.invoice_enforcement_schedules schedule
            JOIN msi_v2.parent_student_links debtor_parent
              ON debtor_parent.student_id = schedule.student_id
             AND debtor_parent.status = 'active'
            JOIN msi_v2.parent_student_links sibling
              ON sibling.parent_id = debtor_parent.parent_id
             AND sibling.status = 'active'
             AND sibling.student_id <> schedule.student_id
            JOIN msi_v2.student_profiles profile
              ON profile.student_id = sibling.student_id
            WHERE profile.account_id = %s
        )
        SELECT DISTINCT ON (schedule.id)
               schedule.*, target.target_type,
               invoice.invoice_number, invoice.total_minor, invoice.paid_minor,
               invoice.currency, invoice.status AS invoice_status,
               student.full_name AS student_name, student.student_code,
               student.legacy_student_row_id,
               hold.status AS hold_status
        FROM target_schedules target
        JOIN msi_v2.invoice_enforcement_schedules schedule
          ON schedule.id = target.schedule_id
        JOIN msi_v2.invoices invoice ON invoice.id = schedule.invoice_id
        JOIN msi_v2.students student ON student.id = schedule.student_id
        LEFT JOIN msi_v2.billing_access_holds hold
          ON hold.schedule_id = schedule.id
         AND hold.account_id = %s
         AND hold.status = 'active'
        WHERE schedule.state IN ('scheduled', 'countdown', 'held')
          AND (
              schedule.state <> 'scheduled'
              OR schedule.countdown_started_at <= now()
          )
          AND invoice.status IN ('issued', 'partially_paid', 'overdue')
          AND invoice.total_minor > invoice.paid_minor
        ORDER BY
            schedule.id,
            CASE target.target_type
                WHEN 'debtor_student' THEN 0
                WHEN 'linked_parent' THEN 1
                ELSE 2
            END
        """,
        (int(account_id), int(account_id), int(account_id), int(account_id)),
    ).fetchall()


def get_account_profile_row(conn: Connection, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT account.id, account.role,
               student_profile.student_id,
               parent_profile.parent_id
        FROM msi_v2.accounts account
        LEFT JOIN msi_v2.student_profiles student_profile
          ON student_profile.account_id = account.id
        LEFT JOIN msi_v2.parent_profiles parent_profile
          ON parent_profile.account_id = account.id
        WHERE account.id = %s
        """,
        (int(account_id),),
    ).fetchone()


def student_has_invoice_access(
    conn: Connection,
    *,
    student_id: int,
    invoice_id: int,
) -> bool:
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.invoices
        WHERE id = %s AND student_id = %s AND admission_id IS NULL
        """,
        (int(invoice_id), int(student_id)),
    ).fetchone()
    return bool(row)


def insert_notification_delivery(
    conn: Connection,
    *,
    schedule_id: int,
    stage: BillingNotificationStage,
    recipient_key: str,
    account_id: int | None,
    telegram_user_id: int | None,
    language: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.billing_notification_deliveries (
            schedule_id, stage, recipient_key, account_id, telegram_user_id,
            language, status, attempts, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'pending', 0, now(), now())
        ON CONFLICT (schedule_id, stage, recipient_key) DO NOTHING
        RETURNING id
        """,
        (
            int(schedule_id),
            stage.value,
            recipient_key,
            int(account_id) if account_id else None,
            int(telegram_user_id) if telegram_user_id else None,
            "ru" if language == "ru" else "uz",
        ),
    ).fetchone()
    if row:
        return int(row["id"])
    existing = conn.execute(
        """
        SELECT id
        FROM msi_v2.billing_notification_deliveries
        WHERE schedule_id = %s AND stage = %s AND recipient_key = %s
        """,
        (int(schedule_id), stage.value, recipient_key),
    ).fetchone()
    return int(existing["id"]) if existing else 0


def get_notification_delivery_row(
    conn: Connection,
    delivery_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF delivery" if for_update else ""
    return conn.execute(
        f"""
        SELECT delivery.*, schedule.invoice_id, schedule.student_id,
               schedule.deadline_at, schedule.state AS schedule_state,
               invoice.invoice_number, invoice.total_minor, invoice.paid_minor,
               invoice.currency, invoice.status AS invoice_status,
               student.full_name AS student_name, student.student_code
        FROM msi_v2.billing_notification_deliveries delivery
        JOIN msi_v2.invoice_enforcement_schedules schedule
          ON schedule.id = delivery.schedule_id
        JOIN msi_v2.invoices invoice ON invoice.id = schedule.invoice_id
        JOIN msi_v2.students student ON student.id = schedule.student_id
        WHERE delivery.id = %s
        {lock}
        """,
        (int(delivery_id),),
    ).fetchone()


def update_notification_delivery(
    conn: Connection,
    *,
    delivery_id: int,
    status: str,
    error: str = "",
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.billing_notification_deliveries
        SET status = %s,
            attempts = attempts + 1,
            sent_at = CASE WHEN %s = 'sent' THEN now() ELSE sent_at END,
            last_error = %s,
            updated_at = now()
        WHERE id = %s
        """,
        (status, status, error.strip()[:2000], int(delivery_id)),
    )


def list_active_schedule_rows(conn: Connection, *, limit: int = 500) -> list[Any]:
    return conn.execute(
        """
        SELECT id
        FROM msi_v2.invoice_enforcement_schedules
        WHERE state IN ('countdown', 'held')
        ORDER BY deadline_at, id
        LIMIT %s
        """,
        (max(1, min(int(limit), 1000)),),
    ).fetchall()


__all__ = [
    "OPEN_INVOICE_STATUSES",
    "account_has_active_hold",
    "activate_household_holds",
    "get_account_profile_row",
    "get_notification_delivery_row",
    "get_schedule_by_invoice_row",
    "get_schedule_row",
    "insert_notification_delivery",
    "insert_schedule",
    "list_account_enforcement_rows",
    "list_active_schedule_rows",
    "list_bootstrap_invoice_rows",
    "list_household_target_rows",
    "release_removed_household_holds",
    "release_schedule_holds",
    "set_schedule_state",
    "student_has_invoice_access",
    "update_notification_delivery",
]
