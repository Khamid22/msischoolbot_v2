"""Recent ticket and payment activity projection."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.unit_of_work import Connection
from backend.modules.domains.reporting.customer_support.schemas import (
    CustomerSupportActivitySummary,
)


def _datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def load_recent_activity(
    conn: Connection,
    parameters: dict[str, object],
) -> list[CustomerSupportActivitySummary]:
    rows = conn.execute(
        """
        WITH activity AS (
            SELECT
                'ticket:' || event.id::text AS activity_id,
                'ticket' AS activity_type,
                event.event_type,
                COALESCE(ticket.topic, 'Support ticket') AS summary,
                school.id AS school_id,
                school.school_name,
                ticket.id AS entity_id,
                event.actor_staff_id,
                COALESCE(staff.display_name, staff.login, '') AS actor_name,
                event.created_at AS occurred_at
            FROM msi_v2.audit_events event
            JOIN msi_v2.support_tickets ticket
              ON event.entity_type = 'support_ticket'
             AND event.entity_id = ticket.id
            JOIN msi_v2.students student ON student.id = ticket.student_id
            JOIN msi_v2.schools school ON school.id = student.school_id
            LEFT JOIN msi_v2.msi_staff staff ON staff.id = event.actor_staff_id
            WHERE event.created_at >= %(period_started_at)s
              AND event.created_at <= %(period_ended_at)s
              AND (
                %(all_schools)s
                OR school.id = ANY(%(school_ids)s::bigint[])
              )

            UNION ALL

            SELECT
                'payment:' || invoice.id::text AS activity_id,
                'payment' AS activity_type,
                CASE
                    WHEN invoice.status = 'voided' THEN 'payment.voided'
                    WHEN invoice.status = 'paid' THEN 'payment.paid'
                    ELSE 'payment.updated'
                END AS event_type,
                student.full_name || ' · ' ||
                    (
                        CASE
                            WHEN invoice.status = 'paid' THEN invoice.total_minor
                            ELSE invoice.total_minor - invoice.paid_minor
                        END::numeric / 100
                    )::text
                    || ' ' || invoice.currency AS summary,
                school.id AS school_id,
                school.school_name,
                invoice.id AS entity_id,
                invoice.created_by_staff_id AS actor_staff_id,
                COALESCE(staff.display_name, staff.login, '') AS actor_name,
                invoice.updated_at AS occurred_at
            FROM msi_v2.invoices invoice
            JOIN msi_v2.students student ON student.id = invoice.student_id
            JOIN msi_v2.schools school ON school.id = student.school_id
            LEFT JOIN msi_v2.msi_staff staff ON staff.id = invoice.created_by_staff_id
            WHERE invoice.updated_at >= %(period_started_at)s
              AND invoice.updated_at <= %(period_ended_at)s
              AND (
                %(all_schools)s
                OR school.id = ANY(%(school_ids)s::bigint[])
              )
        )
        SELECT *
        FROM activity
        ORDER BY occurred_at DESC, activity_id DESC
        LIMIT %(activity_limit)s
        """,
        parameters,
    ).fetchall()
    return [
        CustomerSupportActivitySummary(
            activity_id=str(row["activity_id"]),
            activity_type=str(row["activity_type"]),
            event_type=str(row["event_type"]),
            summary=str(row["summary"]),
            school_id=int(row["school_id"]),
            school_name=str(row["school_name"]),
            entity_id=int(row["entity_id"]),
            actor_staff_id=int(row["actor_staff_id"]) if row["actor_staff_id"] else None,
            actor_name=str(row["actor_name"] or ""),
            occurred_at=_datetime(row["occurred_at"]),
        )
        for row in rows
    ]


__all__ = ["load_recent_activity"]
