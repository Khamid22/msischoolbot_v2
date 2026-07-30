"""School-scoped operational reads for billing automation."""

from __future__ import annotations

from datetime import date
from typing import Any

from backend.core.unit_of_work import Connection


def get_automation_status_row(
    conn: Connection,
    *,
    school_ids: frozenset[int],
    all_schools: bool,
    school_date: date,
) -> Any:
    return conn.execute(
        """
        WITH requested_scope AS (
            SELECT %s::boolean AS all_schools,
                   %s::bigint[] AS school_ids,
                   %s::date AS school_date
        ),
        scoped_students AS (
            SELECT student.id, student.school_id
            FROM msi_v2.students student
            CROSS JOIN requested_scope scope
            WHERE student.status = 'active'
              AND (
                  scope.all_schools
                  OR student.school_id = ANY(scope.school_ids)
              )
        ),
        active_profiles AS (
            SELECT profile.*
            FROM msi_v2.student_billing_profiles profile
            JOIN scoped_students student ON student.id = profile.student_id
            CROSS JOIN requested_scope scope
            WHERE profile.status = 'active'
              AND profile.starts_on <= scope.school_date
              AND (
                  profile.ends_on IS NULL
                  OR profile.ends_on >= scope.school_date
              )
        ),
        open_invoices AS (
            SELECT invoice.*
            FROM msi_v2.invoices invoice
            JOIN scoped_students student ON student.id = invoice.student_id
            WHERE invoice.status IN ('issued', 'partially_paid', 'overdue')
              AND invoice.total_minor > invoice.paid_minor
        ),
        billing_students AS (
            SELECT student_id FROM active_profiles
            UNION
            SELECT student_id FROM open_invoices
        ),
        direct_parents AS (
            SELECT billing.student_id, link.parent_id
            FROM billing_students billing
            JOIN msi_v2.parent_student_links link
              ON link.student_id = billing.student_id
             AND link.status = 'active'
        ),
        recipient_rows AS (
            SELECT
                'student:' || student.id::text AS recipient_key,
                COALESCE(telegram.telegram_user_id, student.telegram_user_id)
                    AS telegram_user_id
            FROM billing_students billing
            JOIN msi_v2.students student ON student.id = billing.student_id
            LEFT JOIN msi_v2.student_profiles profile
              ON profile.student_id = student.id
             AND profile.status = 'active'
            LEFT JOIN msi_v2.account_telegram_links telegram
              ON telegram.account_id = profile.account_id
             AND telegram.status = 'active'

            UNION

            SELECT
                'parent:' || parent.id::text,
                COALESCE(telegram.telegram_user_id, parent.telegram_user_id)
            FROM direct_parents direct
            JOIN msi_v2.parents parent ON parent.id = direct.parent_id
            LEFT JOIN msi_v2.parent_profiles profile
              ON profile.parent_id = parent.id
             AND profile.status = 'active'
            LEFT JOIN msi_v2.account_telegram_links telegram
              ON telegram.account_id = profile.account_id
             AND telegram.status = 'active'
            WHERE parent.status = 'active'

            UNION

            SELECT
                'student:' || sibling.id::text,
                COALESCE(telegram.telegram_user_id, sibling.telegram_user_id)
            FROM direct_parents direct
            JOIN msi_v2.parent_student_links sibling_link
              ON sibling_link.parent_id = direct.parent_id
             AND sibling_link.status = 'active'
            JOIN msi_v2.students sibling ON sibling.id = sibling_link.student_id
            JOIN scoped_students scoped_sibling ON scoped_sibling.id = sibling.id
            LEFT JOIN msi_v2.student_profiles profile
              ON profile.student_id = sibling.id
             AND profile.status = 'active'
            LEFT JOIN msi_v2.account_telegram_links telegram
              ON telegram.account_id = profile.account_id
             AND telegram.status = 'active'
        ),
        scoped_schedules AS (
            SELECT schedule.id
            FROM msi_v2.invoice_enforcement_schedules schedule
            JOIN scoped_students student ON student.id = schedule.student_id
        ),
        finance_jobs AS (
            SELECT
                max(completed_at) FILTER (
                    WHERE status = 'completed'
                ) AS last_completed_at,
                count(*) FILTER (
                    WHERE status IN ('pending', 'retry', 'running')
                )::bigint AS pending_job_count
            FROM msi_v2.outbox_jobs
            WHERE topic LIKE 'finance.%%'
        )
        SELECT
            (SELECT count(*) FROM active_profiles)::bigint
                AS active_billing_profiles,
            (
                SELECT count(*)
                FROM active_profiles profile
                CROSS JOIN requested_scope scope
                WHERE profile.billing_day <= LEAST(
                    EXTRACT(DAY FROM scope.school_date)::int,
                    28
                )
            )::bigint AS currently_due_billing_profiles,
            (SELECT count(*) FROM open_invoices)::bigint AS open_invoices,
            (
                SELECT count(*)
                FROM open_invoices invoice
                LEFT JOIN msi_v2.invoice_enforcement_schedules schedule
                  ON schedule.invoice_id = invoice.id
                WHERE schedule.id IS NULL
            )::bigint AS open_invoices_without_enforcement,
            (
                SELECT count(DISTINCT recipient_key)
                FROM recipient_rows
                WHERE telegram_user_id IS NOT NULL
            )::bigint AS linked_telegram_recipients,
            (
                SELECT count(DISTINCT recipient_key)
                FROM recipient_rows
                WHERE telegram_user_id IS NULL
            )::bigint AS unlinked_telegram_recipients,
            (
                SELECT count(*)
                FROM msi_v2.billing_notification_deliveries delivery
                JOIN scoped_schedules schedule ON schedule.id = delivery.schedule_id
                WHERE delivery.status = 'pending'
            )::bigint AS pending_notification_deliveries,
            (
                SELECT count(*)
                FROM msi_v2.billing_notification_deliveries delivery
                JOIN scoped_schedules schedule ON schedule.id = delivery.schedule_id
                WHERE delivery.status = 'failed'
            )::bigint AS failed_notification_deliveries,
            (
                SELECT count(*)
                FROM msi_v2.billing_access_holds hold
                JOIN scoped_schedules schedule ON schedule.id = hold.schedule_id
                WHERE hold.status = 'active'
            )::bigint AS active_payment_only_holds,
            finance_jobs.pending_job_count,
            finance_jobs.last_completed_at
        FROM finance_jobs
        """,
        (bool(all_schools), sorted(int(item) for item in school_ids), school_date),
    ).fetchone()


__all__ = ["get_automation_status_row"]
