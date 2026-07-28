"""PostgreSQL projections for the Customer Support operational dashboard."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from backend.core.time import SCHOOL_TIMEZONE
from backend.core.unit_of_work import Connection
from backend.modules.domains.reporting.customer_support.activity_repository import (
    load_recent_activity,
)
from backend.modules.domains.reporting.customer_support.repository import (
    CustomerSupportDashboardReadScope,
)
from backend.modules.domains.reporting.customer_support.schemas import (
    AccountExceptionSummary,
    CurrencyAmount,
    CustomerSupportDashboardData,
    CustomerSupportDashboardMetrics,
    CustomerSupportSchool,
    CustomerSupportTicketSummary,
    DailyTicketFlow,
    OverduePaymentAccount,
    PaymentExceptionSummary,
    SchoolTicketWorkload,
    StudentWithoutParentLink,
    TicketAgeBucket,
    TicketCategoryVolume,
)
from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketCategory,
    TicketPriority,
    TicketSlaState,
    TicketStatus,
    normalize_ticket_category,
    normalize_ticket_priority,
    normalize_ticket_status,
)

SCHOOL_TIME_ZONE_NAME = SCHOOL_TIMEZONE.key

_SLA_STATE_SQL = """
    CASE
        WHEN ticket.status = 'resolved' THEN
            CASE
                WHEN ticket.resolved_at IS NOT NULL
                 AND ticket.resolution_due_at IS NOT NULL
                 AND ticket.resolved_at <= ticket.resolution_due_at
                THEN 'met'
                ELSE 'breached'
            END
        WHEN ticket.waiting_on_requester_at IS NOT NULL
         AND ticket.first_responded_at IS NOT NULL THEN 'paused'
        WHEN (
            ticket.first_responded_at IS NULL
            AND %(dashboard_now)s >= ticket.first_response_due_at
        ) OR %(dashboard_now)s >= ticket.resolution_due_at THEN 'breached'
        WHEN (
            ticket.first_responded_at IS NULL
            AND ticket.first_response_due_at - %(dashboard_now)s
                <= make_interval(mins => ticket.first_response_target_minutes / 4)
        ) OR (
            ticket.first_responded_at IS NOT NULL
            AND ticket.resolution_due_at - %(dashboard_now)s
                <= make_interval(mins => ticket.resolution_target_minutes / 4)
        ) THEN 'due_soon'
        ELSE 'on_track'
    END
"""


def _datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _optional_datetime(value: object) -> datetime | None:
    return _datetime(value) if value not in (None, "") else None


def _date(value: object) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _scope_parameters(scope: CustomerSupportDashboardReadScope) -> dict[str, object]:
    return {
        "all_schools": scope.all_schools,
        "school_ids": list(scope.school_ids),
        "available_all_schools": scope.has_all_school_access,
        "available_school_ids": list(scope.available_school_ids),
        "period_started_at": scope.started_at,
        "period_ended_at": scope.ended_at,
        "dashboard_now": scope.ended_at,
        "school_today": scope.ended_at.astimezone(SCHOOL_TIMEZONE).date(),
        "ticket_limit": scope.ticket_limit,
        "activity_limit": scope.activity_limit,
        "actor_staff_id": scope.actor_staff_id,
    }


def _ticket_summary(row) -> CustomerSupportTicketSummary:
    return CustomerSupportTicketSummary(
        ticket_id=int(row["ticket_id"]),
        parent_id=int(row["parent_id"]) if row["parent_id"] else None,
        student_id=int(row["student_id"]) if row["student_id"] else None,
        student_row_id=int(row["student_row_id"]) if row["student_row_id"] else None,
        student_code=str(row["student_code"] or ""),
        title=str(row["topic"] or "Untitled ticket"),
        requester_name=str(row["requester_name"] or ""),
        school_id=int(row["school_id"]),
        school_name=str(row["school_name"] or ""),
        category=TicketCategory(normalize_ticket_category(row["category"])),
        status=TicketStatus(normalize_ticket_status(row["status"])),
        priority=TicketPriority(normalize_ticket_priority(row["priority"])),
        sla_state=TicketSlaState(str(row["sla_state"])),
        assigned_staff_id=(int(row["assigned_staff_id"]) if row["assigned_staff_id"] else None),
        assigned_staff_name=str(row["assigned_staff_name"] or ""),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        first_response_due_at=_optional_datetime(row["first_response_due_at"]),
        resolution_due_at=_optional_datetime(row["resolution_due_at"]),
        is_waiting_on_requester=bool(row["waiting_on_requester_at"]),
    )


class PostgresCustomerSupportDashboardRepository:
    """Load a complete, consistent dashboard snapshot from one connection."""

    def load_dashboard(
        self,
        conn: Connection,
        scope: CustomerSupportDashboardReadScope,
    ) -> CustomerSupportDashboardData:
        parameters = _scope_parameters(scope)
        return CustomerSupportDashboardData(
            available_schools=self._schools(conn, parameters),
            metrics=self._metrics(conn, parameters),
            daily_ticket_flow=self._daily_flow(conn, parameters),
            ticket_age_buckets=self._age_buckets(conn, parameters),
            ticket_categories=self._categories(conn, parameters),
            school_workload=self._school_workload(conn, parameters),
            action_required_tickets=self._tickets(
                conn,
                parameters,
                action_required=True,
            ),
            oldest_open_tickets=self._tickets(
                conn,
                parameters,
                action_required=False,
            ),
            payment_exceptions=self._payment_exceptions(conn, parameters),
            account_exceptions=self._account_exceptions(conn, parameters),
            recent_activity=load_recent_activity(conn, parameters),
        )

    @staticmethod
    def _schools(conn: Connection, parameters: dict[str, object]) -> list[CustomerSupportSchool]:
        rows = conn.execute(
            """
            SELECT school.id AS school_id, school.school_name
            FROM msi_v2.schools school
            WHERE (
                %(available_all_schools)s
                OR school.id = ANY(%(available_school_ids)s::bigint[])
            )
            ORDER BY school.school_name, school.id
            """,
            parameters,
        ).fetchall()
        return [
            CustomerSupportSchool(
                school_id=int(row["school_id"]),
                school_name=str(row["school_name"]),
            )
            for row in rows
        ]

    @staticmethod
    def _metrics(
        conn: Connection,
        parameters: dict[str, object],
    ) -> CustomerSupportDashboardMetrics:
        row = conn.execute(
            """
            WITH scoped_tickets AS (
                SELECT ticket.*
                FROM msi_v2.support_tickets ticket
                JOIN msi_v2.students student ON student.id = ticket.student_id
                WHERE (
                    %(all_schools)s
                    OR student.school_id = ANY(%(school_ids)s::bigint[])
                )
            ),
            scoped_students AS (
                SELECT student.*
                FROM msi_v2.students student
                WHERE (
                    %(all_schools)s
                    OR student.school_id = ANY(%(school_ids)s::bigint[])
                )
            )
            SELECT
                COUNT(*) FILTER (
                    WHERE ticket.status <> 'resolved'
                ) AS open_tickets,
                COUNT(*) FILTER (
                    WHERE ticket.status <> 'resolved'
                      AND ticket.assigned_to_staff_id = %(actor_staff_id)s
                ) AS assigned_to_me,
                COUNT(*) FILTER (
                    WHERE ticket.status <> 'resolved'
                      AND ticket.assigned_to_staff_id IS NULL
                ) AS unassigned_tickets,
                COUNT(*) FILTER (
                    WHERE ticket.status = 'escalated'
                ) AS escalated_tickets,
                COUNT(*) FILTER (
                    WHERE ticket.status <> 'resolved'
                      AND (
                        (
                            ticket.first_responded_at IS NULL
                            AND ticket.first_response_due_at < %(dashboard_now)s
                        )
                        OR (
                            ticket.waiting_on_requester_at IS NULL
                            AND ticket.resolution_due_at < %(dashboard_now)s
                        )
                      )
                ) AS sla_breached_tickets,
                COUNT(*) FILTER (
                    WHERE ticket.status <> 'resolved'
                      AND ticket.waiting_on_requester_at IS NOT NULL
                ) AS waiting_on_requester_tickets,
                (
                    SELECT COUNT(DISTINCT invoice.student_id)
                    FROM msi_v2.invoices invoice
                    JOIN scoped_students student ON student.id = invoice.student_id
                    WHERE invoice.status IN ('issued', 'partially_paid', 'overdue')
                      AND invoice.due_date < %(school_today)s
                ) AS overdue_payment_accounts,
                (
                    SELECT COUNT(*)
                    FROM scoped_students student
                    WHERE student.status = 'active'
                      AND NOT EXISTS (
                        SELECT 1
                        FROM msi_v2.parent_student_links link
                        WHERE link.student_id = student.id
                          AND link.status = 'active'
                      )
                ) AS students_without_active_parent_link
            FROM scoped_tickets ticket
            """,
            parameters,
        ).fetchone()
        return CustomerSupportDashboardMetrics(**dict(row or {}))

    @staticmethod
    def _daily_flow(
        conn: Connection,
        parameters: dict[str, object],
    ) -> list[DailyTicketFlow]:
        rows = conn.execute(
            f"""
            WITH days AS (
                SELECT generate_series(
                    (%(period_started_at)s AT TIME ZONE '{SCHOOL_TIME_ZONE_NAME}')::date,
                    (%(period_ended_at)s AT TIME ZONE '{SCHOOL_TIME_ZONE_NAME}')::date,
                    INTERVAL '1 day'
                )::date AS day
            ),
            scoped AS (
                SELECT ticket.created_at, ticket.resolved_at
                FROM msi_v2.support_tickets ticket
                JOIN msi_v2.students student ON student.id = ticket.student_id
                WHERE (
                    %(all_schools)s
                    OR student.school_id = ANY(%(school_ids)s::bigint[])
                )
            )
            SELECT
                days.day,
                COUNT(scoped.created_at) FILTER (
                    WHERE (scoped.created_at AT TIME ZONE '{SCHOOL_TIME_ZONE_NAME}')::date
                        = days.day
                ) AS opened,
                COUNT(scoped.resolved_at) FILTER (
                    WHERE (scoped.resolved_at AT TIME ZONE '{SCHOOL_TIME_ZONE_NAME}')::date
                        = days.day
                ) AS resolved
            FROM days
            LEFT JOIN scoped ON (
                (scoped.created_at AT TIME ZONE '{SCHOOL_TIME_ZONE_NAME}')::date = days.day
                OR (scoped.resolved_at AT TIME ZONE '{SCHOOL_TIME_ZONE_NAME}')::date = days.day
            )
            GROUP BY days.day
            ORDER BY days.day
            """,
            parameters,
        ).fetchall()
        return [
            DailyTicketFlow(
                day=_date(row["day"]),
                opened=int(row["opened"] or 0),
                resolved=int(row["resolved"] or 0),
            )
            for row in rows
        ]

    @staticmethod
    def _age_buckets(
        conn: Connection,
        parameters: dict[str, object],
    ) -> list[TicketAgeBucket]:
        row = conn.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE %(dashboard_now)s - ticket.created_at < INTERVAL '24 hours'
                ) AS under_24h,
                COUNT(*) FILTER (
                    WHERE %(dashboard_now)s - ticket.created_at >= INTERVAL '24 hours'
                      AND %(dashboard_now)s - ticket.created_at < INTERVAL '4 days'
                ) AS one_to_three_days,
                COUNT(*) FILTER (
                    WHERE %(dashboard_now)s - ticket.created_at >= INTERVAL '4 days'
                      AND %(dashboard_now)s - ticket.created_at < INTERVAL '8 days'
                ) AS four_to_seven_days,
                COUNT(*) FILTER (
                    WHERE %(dashboard_now)s - ticket.created_at >= INTERVAL '8 days'
                ) AS eight_plus_days
            FROM msi_v2.support_tickets ticket
            JOIN msi_v2.students student ON student.id = ticket.student_id
            WHERE ticket.status <> 'resolved'
              AND (
                %(all_schools)s
                OR student.school_id = ANY(%(school_ids)s::bigint[])
              )
            """,
            parameters,
        ).fetchone()
        values = dict(row or {})
        return [
            TicketAgeBucket(
                bucket="under_24h", label="<24h", count=int(values.get("under_24h", 0))
            ),
            TicketAgeBucket(
                bucket="one_to_three_days",
                label="1–3d",
                count=int(values.get("one_to_three_days", 0)),
            ),
            TicketAgeBucket(
                bucket="four_to_seven_days",
                label="4–7d",
                count=int(values.get("four_to_seven_days", 0)),
            ),
            TicketAgeBucket(
                bucket="eight_plus_days",
                label="8d+",
                count=int(values.get("eight_plus_days", 0)),
            ),
        ]

    @staticmethod
    def _categories(
        conn: Connection,
        parameters: dict[str, object],
    ) -> list[TicketCategoryVolume]:
        rows = conn.execute(
            """
            SELECT ticket.category, COUNT(*) AS ticket_count
            FROM msi_v2.support_tickets ticket
            JOIN msi_v2.students student ON student.id = ticket.student_id
            WHERE (
                    %(all_schools)s
                    OR student.school_id = ANY(%(school_ids)s::bigint[])
                  )
              AND ticket.created_at >= %(period_started_at)s
              AND ticket.created_at <= %(period_ended_at)s
            GROUP BY ticket.category
            ORDER BY ticket_count DESC, ticket.category
            """,
            parameters,
        ).fetchall()
        return [
            TicketCategoryVolume(
                category=TicketCategory(normalize_ticket_category(row["category"])),
                count=int(row["ticket_count"]),
            )
            for row in rows
        ]

    @staticmethod
    def _school_workload(
        conn: Connection,
        parameters: dict[str, object],
    ) -> list[SchoolTicketWorkload]:
        rows = conn.execute(
            f"""
            SELECT
                school.id AS school_id,
                school.school_name,
                COUNT(ticket.id) FILTER (
                    WHERE ticket.status <> 'resolved'
                ) AS open_tickets,
                COUNT(ticket.id) FILTER (
                    WHERE ticket.status <> 'resolved'
                      AND ticket.assigned_to_staff_id IS NULL
                ) AS unassigned_tickets,
                COUNT(ticket.id) FILTER (
                    WHERE ticket.status <> 'resolved'
                      AND ({_SLA_STATE_SQL}) = 'breached'
                ) AS sla_breached_tickets
            FROM msi_v2.schools school
            LEFT JOIN msi_v2.students student ON student.school_id = school.id
            LEFT JOIN msi_v2.support_tickets ticket ON ticket.student_id = student.id
            WHERE (
                %(all_schools)s
                OR school.id = ANY(%(school_ids)s::bigint[])
            )
            GROUP BY school.id, school.school_name
            ORDER BY open_tickets DESC, school.school_name
            """,
            parameters,
        ).fetchall()
        return [SchoolTicketWorkload(**dict(row)) for row in rows]

    @staticmethod
    def _tickets(
        conn: Connection,
        parameters: dict[str, object],
        *,
        action_required: bool,
    ) -> list[CustomerSupportTicketSummary]:
        order_by = (
            f"""
            CASE WHEN ({_SLA_STATE_SQL}) = 'breached' THEN 0 ELSE 1 END,
            CASE WHEN ticket.status = 'escalated' THEN 0 ELSE 1 END,
            CASE WHEN ticket.assigned_to_staff_id IS NULL THEN 0 ELSE 1 END,
            CASE ticket.priority
                WHEN 'urgent' THEN 0
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                ELSE 3
            END,
            ticket.created_at,
            ticket.id
            """
            if action_required
            else "ticket.created_at, ticket.id"
        )
        rows = conn.execute(
            f"""
            SELECT
                ticket.id AS ticket_id,
                ticket.parent_id,
                ticket.student_id,
                student.legacy_student_row_id AS student_row_id,
                student.student_code,
                ticket.topic,
                COALESCE(parent.display_name, student.full_name, '') AS requester_name,
                school.id AS school_id,
                school.school_name,
                ticket.category,
                ticket.status,
                ticket.priority,
                ({_SLA_STATE_SQL}) AS sla_state,
                ticket.assigned_to_staff_id AS assigned_staff_id,
                COALESCE(staff.display_name, staff.login, '') AS assigned_staff_name,
                ticket.created_at,
                ticket.updated_at,
                ticket.first_response_due_at,
                ticket.resolution_due_at,
                ticket.waiting_on_requester_at
            FROM msi_v2.support_tickets ticket
            JOIN msi_v2.students student ON student.id = ticket.student_id
            JOIN msi_v2.schools school ON school.id = student.school_id
            LEFT JOIN msi_v2.parents parent ON parent.id = ticket.parent_id
            LEFT JOIN msi_v2.msi_staff staff ON staff.id = ticket.assigned_to_staff_id
            WHERE ticket.status <> 'resolved'
              AND (
                %(all_schools)s
                OR school.id = ANY(%(school_ids)s::bigint[])
              )
            ORDER BY {order_by}
            LIMIT %(ticket_limit)s
            """,
            parameters,
        ).fetchall()
        return [_ticket_summary(row) for row in rows]

    @staticmethod
    def _payment_exceptions(
        conn: Connection,
        parameters: dict[str, object],
    ) -> PaymentExceptionSummary:
        total_rows = conn.execute(
            """
            SELECT
                CASE
                    WHEN invoice.due_date < %(school_today)s THEN 'overdue'
                    ELSE 'due_soon'
                END AS exception_kind,
                invoice.currency,
                SUM(invoice.total_minor - invoice.paid_minor)::numeric / 100 AS amount,
                COUNT(DISTINCT invoice.student_id) AS account_count
            FROM msi_v2.invoices invoice
            JOIN msi_v2.students student ON student.id = invoice.student_id
            WHERE invoice.status IN ('issued', 'partially_paid', 'overdue')
              AND invoice.due_date <= %(school_today)s + INTERVAL '7 days'
              AND (
                %(all_schools)s
                OR student.school_id = ANY(%(school_ids)s::bigint[])
              )
            GROUP BY exception_kind, invoice.currency
            ORDER BY exception_kind, invoice.currency
            """,
            parameters,
        ).fetchall()
        totals: dict[str, list[CurrencyAmount]] = {
            "overdue": [],
            "due_soon": [],
        }
        for row in total_rows:
            totals[str(row["exception_kind"])].append(
                CurrencyAmount(
                    currency=str(row["currency"]),
                    amount=_decimal(row["amount"]),
                    account_count=int(row["account_count"]),
                )
            )

        rows = conn.execute(
            """
            SELECT
                invoice.id AS payment_id,
                student.id AS student_id,
                student.legacy_student_row_id AS student_row_id,
                student.student_code,
                student.full_name AS student_name,
                school.id AS school_id,
                school.school_name,
                invoice.due_date,
                (invoice.total_minor - invoice.paid_minor)::numeric / 100 AS amount,
                invoice.currency,
                %(school_today)s - invoice.due_date AS days_overdue
            FROM msi_v2.invoices invoice
            JOIN msi_v2.students student ON student.id = invoice.student_id
            JOIN msi_v2.schools school ON school.id = student.school_id
            WHERE invoice.status IN ('issued', 'partially_paid', 'overdue')
              AND invoice.due_date < %(school_today)s
              AND (
                %(all_schools)s
                OR school.id = ANY(%(school_ids)s::bigint[])
              )
            ORDER BY invoice.due_date,
                     (invoice.total_minor - invoice.paid_minor) DESC,
                     invoice.id
            LIMIT %(ticket_limit)s
            """,
            parameters,
        ).fetchall()
        overdue_accounts = [
            OverduePaymentAccount(
                payment_id=int(row["payment_id"]),
                student_id=int(row["student_id"]),
                student_row_id=(int(row["student_row_id"]) if row["student_row_id"] else None),
                student_code=str(row["student_code"]),
                student_name=str(row["student_name"]),
                school_id=int(row["school_id"]),
                school_name=str(row["school_name"]),
                due_date=_date(row["due_date"]),
                amount=_decimal(row["amount"]),
                currency=str(row["currency"]),
                days_overdue=int(row["days_overdue"]),
            )
            for row in rows
        ]
        return PaymentExceptionSummary(
            overdue_totals=totals["overdue"],
            due_soon_totals=totals["due_soon"],
            top_overdue_accounts=overdue_accounts,
        )

    @staticmethod
    def _account_exceptions(
        conn: Connection,
        parameters: dict[str, object],
    ) -> AccountExceptionSummary:
        rows = conn.execute(
            """
            SELECT
                student.id AS student_id,
                student.legacy_student_row_id AS student_row_id,
                student.student_code,
                student.full_name AS student_name,
                school.id AS school_id,
                school.school_name
            FROM msi_v2.students student
            JOIN msi_v2.schools school ON school.id = student.school_id
            WHERE student.status = 'active'
              AND (
                %(all_schools)s
                OR school.id = ANY(%(school_ids)s::bigint[])
              )
              AND NOT EXISTS (
                SELECT 1
                FROM msi_v2.parent_student_links link
                WHERE link.student_id = student.id
                  AND link.status = 'active'
              )
            ORDER BY school.school_name, student.full_name, student.id
            LIMIT %(ticket_limit)s
            """,
            parameters,
        ).fetchall()
        return AccountExceptionSummary(
            students_without_active_parent_link=[
                StudentWithoutParentLink(
                    student_id=int(row["student_id"]),
                    student_row_id=(int(row["student_row_id"]) if row["student_row_id"] else None),
                    student_code=str(row["student_code"]),
                    student_name=str(row["student_name"]),
                    school_id=int(row["school_id"]),
                    school_name=str(row["school_name"]),
                )
                for row in rows
            ]
        )


__all__ = ["PostgresCustomerSupportDashboardRepository"]
