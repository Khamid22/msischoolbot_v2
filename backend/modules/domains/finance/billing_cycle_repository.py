"""PostgreSQL persistence for immutable monthly billing-cycle snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from backend.core.unit_of_work import Connection


def list_active_profile_rows(conn: Connection) -> list[Any]:
    return conn.execute(
        """
        SELECT profile.*
        FROM msi_v2.student_billing_profiles profile
        JOIN msi_v2.students student ON student.id = profile.student_id
        WHERE profile.status = 'active'
          AND student.status = 'active'
        ORDER BY profile.id
        """
    ).fetchall()


def list_snapshot_item_rows(
    conn: Connection,
    *,
    profile_id: int,
    effective_on: date,
) -> list[Any]:
    return conn.execute(
        """
        SELECT item.*
        FROM msi_v2.student_billing_items item
        JOIN msi_v2.group_students enrollment
          ON enrollment.student_id = (
              SELECT student_id
              FROM msi_v2.student_billing_profiles
              WHERE id = item.profile_id
          )
         AND enrollment.group_id = item.group_id
         AND enrollment.enrollment_status = 'active'
        WHERE item.profile_id = %s
          AND item.status = 'active'
          AND item.active_from <= %s
          AND (item.active_until IS NULL OR item.active_until >= %s)
        ORDER BY item.id
        """,
        (int(profile_id), effective_on, effective_on),
    ).fetchall()


def insert_cycle(
    conn: Connection,
    *,
    profile_id: int,
    student_id: int,
    school_id: int,
    billing_period: date,
    due_at: datetime,
    item_rows: list[Any],
) -> int:
    expected_minor = sum(int(item["amount_minor"]) for item in item_rows)
    if expected_minor <= 0:
        return 0
    row = conn.execute(
        """
        INSERT INTO msi_v2.student_billing_cycles (
            profile_id, student_id, school_id, billing_period, due_at,
            currency, expected_minor, allocated_minor, state,
            version, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, 'UZS', %s, 0, 'scheduled', 1, now(), now())
        ON CONFLICT (profile_id, billing_period) DO NOTHING
        RETURNING id
        """,
        (
            int(profile_id),
            int(student_id),
            int(school_id),
            billing_period,
            due_at,
            expected_minor,
        ),
    ).fetchone()
    if not row:
        existing = get_cycle_by_profile_period_row(
            conn,
            profile_id=profile_id,
            billing_period=billing_period,
        )
        return int(existing["id"]) if existing else 0
    cycle_id = int(row["id"])
    for item_order, item in enumerate(item_rows):
        conn.execute(
            """
            INSERT INTO msi_v2.student_billing_cycle_items (
                cycle_id, billing_item_id, group_id, subject_id,
                description, amount_minor, item_order, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                cycle_id,
                int(item["id"]),
                int(item["group_id"]),
                int(item["subject_id"]),
                str(item["description"]),
                int(item["amount_minor"]),
                item_order,
            ),
        )
    return cycle_id


def get_cycle_by_profile_period_row(
    conn: Connection,
    *,
    profile_id: int,
    billing_period: date,
) -> Any:
    return conn.execute(
        """
        SELECT *
        FROM msi_v2.student_billing_cycles
        WHERE profile_id = %s AND billing_period = %s
        """,
        (int(profile_id), billing_period),
    ).fetchone()


def get_cycle_row(
    conn: Connection,
    cycle_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF cycle" if for_update else ""
    return conn.execute(
        f"""
        SELECT cycle.*,
               student.legacy_student_row_id,
               student.full_name AS student_name,
               student.student_code,
               school.school_name,
               invoice.id AS invoice_id,
               invoice.invoice_number,
               invoice.total_minor AS invoice_total_minor,
               invoice.paid_minor AS invoice_paid_minor
        FROM msi_v2.student_billing_cycles cycle
        JOIN msi_v2.students student ON student.id = cycle.student_id
        JOIN msi_v2.schools school ON school.id = cycle.school_id
        LEFT JOIN msi_v2.invoices invoice
          ON invoice.billing_cycle_id = cycle.id
         AND invoice.status <> 'voided'
        WHERE cycle.id = %s
        {lock}
        """,
        (int(cycle_id),),
    ).fetchone()


def list_cycle_item_rows(conn: Connection, cycle_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT *
        FROM msi_v2.student_billing_cycle_items
        WHERE cycle_id = %s
        ORDER BY item_order, id
        """,
        (int(cycle_id),),
    ).fetchall()


def list_cycle_review_rows(conn: Connection, cycle_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT review.*, invoice.invoice_number
        FROM msi_v2.billing_cycle_invoice_reviews review
        JOIN msi_v2.invoices invoice ON invoice.id = review.invoice_id
        WHERE review.cycle_id = %s
        ORDER BY review.reviewed_at, review.id
        """,
        (int(cycle_id),),
    ).fetchall()


def list_manual_candidate_rows(conn: Connection, cycle_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT
            invoice.*,
            GREATEST(
                invoice.paid_minor - COALESCE(allocated.total_allocated_minor, 0),
                0
            ) AS available_minor
        FROM msi_v2.student_billing_cycles cycle
        JOIN msi_v2.invoices invoice
          ON invoice.student_id = cycle.student_id
         AND invoice.billing_period = cycle.billing_period
         AND invoice.billing_cycle_id IS NULL
         AND (
             invoice.invoice_kind = 'manual'
             OR invoice.origin = 'legacy_migration'
         )
         AND invoice.status <> 'voided'
         AND invoice.paid_minor > 0
        LEFT JOIN LATERAL (
            SELECT COALESCE(sum(review.allocated_minor), 0) AS total_allocated_minor
            FROM msi_v2.billing_cycle_invoice_reviews review
            WHERE review.invoice_id = invoice.id
              AND review.decision = 'apply'
              AND review.status = 'active'
        ) allocated ON TRUE
        WHERE cycle.id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.billing_cycle_invoice_reviews reviewed
              WHERE reviewed.cycle_id = cycle.id
                AND reviewed.invoice_id = invoice.id
                AND reviewed.status = 'active'
          )
          AND invoice.paid_minor > COALESCE(allocated.total_allocated_minor, 0)
        ORDER BY invoice.paid_at NULLS LAST, invoice.id
        """,
        (int(cycle_id),),
    ).fetchall()


def get_available_manual_invoice_row(
    conn: Connection,
    *,
    cycle_id: int,
    invoice_id: int,
    require_matching_period: bool,
) -> Any:
    return conn.execute(
        """
        SELECT
            invoice.*,
            GREATEST(
                invoice.paid_minor - COALESCE(allocated.total_allocated_minor, 0),
                0
            ) AS available_minor
        FROM msi_v2.student_billing_cycles cycle
        JOIN msi_v2.invoices invoice
          ON invoice.id = %s
         AND invoice.student_id = cycle.student_id
         AND invoice.billing_cycle_id IS NULL
         AND (
             invoice.invoice_kind = 'manual'
             OR invoice.origin = 'legacy_migration'
         )
         AND invoice.status <> 'voided'
         AND invoice.paid_minor > 0
        LEFT JOIN LATERAL (
            SELECT COALESCE(sum(review.allocated_minor), 0) AS total_allocated_minor
            FROM msi_v2.billing_cycle_invoice_reviews review
            WHERE review.invoice_id = invoice.id
              AND review.decision = 'apply'
              AND review.status = 'active'
        ) allocated ON TRUE
        WHERE cycle.id = %s
          AND (%s = FALSE OR invoice.billing_period = cycle.billing_period)
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.billing_cycle_invoice_reviews reviewed
              WHERE reviewed.cycle_id = cycle.id
                AND reviewed.invoice_id = invoice.id
                AND reviewed.status = 'active'
          )
          AND invoice.paid_minor > COALESCE(allocated.total_allocated_minor, 0)
        """,
        (int(invoice_id), int(cycle_id), bool(require_matching_period)),
    ).fetchone()


def list_scoped_cycle_rows(
    conn: Connection,
    *,
    school_ids: Iterable[int],
    all_schools: bool,
    student_id: int | None = None,
    limit: int = 100,
) -> list[Any]:
    return conn.execute(
        """
        SELECT cycle.*,
               student.legacy_student_row_id,
               student.full_name AS student_name,
               student.student_code,
               school.school_name,
               invoice.id AS invoice_id,
               invoice.invoice_number,
               invoice.total_minor AS invoice_total_minor,
               invoice.paid_minor AS invoice_paid_minor
        FROM msi_v2.student_billing_cycles cycle
        JOIN msi_v2.students student ON student.id = cycle.student_id
        JOIN msi_v2.schools school ON school.id = cycle.school_id
        LEFT JOIN msi_v2.invoices invoice
          ON invoice.billing_cycle_id = cycle.id
         AND invoice.status <> 'voided'
        WHERE (%s OR cycle.school_id = ANY(%s::bigint[]))
          AND (%s::bigint IS NULL OR cycle.student_id = %s)
        ORDER BY cycle.due_at, cycle.id
        LIMIT %s
        """,
        (
            bool(all_schools),
            list(school_ids),
            student_id,
            student_id,
            max(1, min(int(limit), 500)),
        ),
    ).fetchall()


def list_parent_cycle_rows(
    conn: Connection,
    *,
    parent_id: int,
    student_row_id: int | None,
) -> list[Any]:
    return conn.execute(
        """
        SELECT cycle.*,
               student.legacy_student_row_id,
               student.full_name AS student_name,
               student.student_code,
               school.school_name,
               invoice.id AS invoice_id,
               invoice.invoice_number,
               invoice.total_minor AS invoice_total_minor,
               invoice.paid_minor AS invoice_paid_minor,
               enforcement.deadline_at AS effective_deadline_at
        FROM msi_v2.parent_student_links link
        JOIN msi_v2.students student ON student.id = link.student_id
        JOIN msi_v2.student_billing_cycles cycle ON cycle.student_id = student.id
        JOIN msi_v2.schools school ON school.id = cycle.school_id
        LEFT JOIN msi_v2.invoices invoice
          ON invoice.billing_cycle_id = cycle.id
         AND invoice.status <> 'voided'
        LEFT JOIN msi_v2.invoice_enforcement_schedules enforcement
          ON enforcement.invoice_id = invoice.id
        WHERE link.parent_id = %s
          AND link.status = 'active'
          AND (
              %s::bigint IS NULL
              OR student.legacy_student_row_id = %s
          )
        ORDER BY cycle.billing_period DESC, student.full_name, cycle.id DESC
        """,
        (int(parent_id), student_row_id, student_row_id),
    ).fetchall()


def update_cycle_state(
    conn: Connection,
    *,
    cycle_id: int,
    state: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.student_billing_cycles
        SET state = %s, version = version + 1, updated_at = now()
        WHERE id = %s AND state <> %s
        """,
        (state, int(cycle_id), state),
    )


def sync_cycle_state_for_invoice(conn: Connection, invoice_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.student_billing_cycles cycle
        SET state = CASE
                WHEN invoice.status = 'paid' THEN 'satisfied'
                WHEN invoice.status = 'voided' THEN 'cancelled'
                ELSE 'invoiced'
            END,
            version = CASE
                WHEN cycle.state <> CASE
                    WHEN invoice.status = 'paid' THEN 'satisfied'
                    WHEN invoice.status = 'voided' THEN 'cancelled'
                    ELSE 'invoiced'
                END
                THEN cycle.version + 1
                ELSE cycle.version
            END,
            updated_at = CASE
                WHEN cycle.state <> CASE
                    WHEN invoice.status = 'paid' THEN 'satisfied'
                    WHEN invoice.status = 'voided' THEN 'cancelled'
                    ELSE 'invoiced'
                END
                THEN now()
                ELSE cycle.updated_at
            END
        FROM msi_v2.invoices invoice
        WHERE invoice.id = %s
          AND invoice.billing_cycle_id = cycle.id
        """,
        (int(invoice_id),),
    )


def recompute_cycle_allocation(conn: Connection, cycle_id: int) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.student_billing_cycles cycle
        SET allocated_minor = allocation.amount_minor,
            state = CASE
                WHEN allocation.amount_minor >= cycle.expected_minor THEN 'satisfied'
                WHEN cycle.state = 'satisfied' THEN 'scheduled'
                ELSE cycle.state
            END,
            version = cycle.version + 1,
            updated_at = now()
        FROM (
            SELECT
                %s::bigint AS cycle_id,
                COALESCE(sum(review.allocated_minor), 0)::bigint AS amount_minor
            FROM msi_v2.billing_cycle_invoice_reviews review
            WHERE review.cycle_id = %s
              AND review.decision = 'apply'
              AND review.status = 'active'
        ) allocation
        WHERE cycle.id = allocation.cycle_id
        RETURNING cycle.*
        """,
        (int(cycle_id), int(cycle_id)),
    ).fetchone()


def insert_review(
    conn: Connection,
    *,
    cycle_id: int,
    invoice_id: int,
    decision: str,
    allocated_minor: int,
    reason: str,
    staff_id: int | None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.billing_cycle_invoice_reviews (
            cycle_id, invoice_id, decision, allocated_minor, status,
            reason, reviewed_by_staff_id, reviewed_at, version,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'active', %s, %s, now(), 1, now(), now())
        RETURNING id
        """,
        (
            int(cycle_id),
            int(invoice_id),
            decision,
            int(allocated_minor),
            reason.strip(),
            int(staff_id) if staff_id else None,
        ),
    ).fetchone()
    return int(row["id"])


def get_review_row(
    conn: Connection,
    review_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF review" if for_update else ""
    return conn.execute(
        f"""
        SELECT review.*, cycle.school_id, cycle.state AS cycle_state
        FROM msi_v2.billing_cycle_invoice_reviews review
        JOIN msi_v2.student_billing_cycles cycle ON cycle.id = review.cycle_id
        WHERE review.id = %s
        {lock}
        """,
        (int(review_id),),
    ).fetchone()


def reverse_review(
    conn: Connection,
    *,
    review_id: int,
    expected_version: int,
    staff_id: int | None,
    reason: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.billing_cycle_invoice_reviews
        SET status = 'reversed',
            reversed_by_staff_id = %s,
            reversed_at = now(),
            reversal_reason = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND status = 'active'
          AND version = %s
        RETURNING id
        """,
        (
            int(staff_id) if staff_id else None,
            reason.strip(),
            int(review_id),
            int(expected_version),
        ),
    ).fetchone()
    return bool(row)


def insert_cycle_invoice(
    conn: Connection,
    *,
    cycle_row: Any,
    item_rows: list[Any],
    remaining_minor: int,
    due_date: date,
    parent_id: int | None,
    invoice_number: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoices (
            invoice_number, student_id, parent_id, billing_cycle_id,
            invoice_kind, billing_period, currency, total_minor, paid_minor,
            status, due_date, issued_at, version, origin, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, %s, 'monthly', %s, %s, %s, 0,
            'issued', %s, now(), 1, 'student_billing', now(), now()
        )
        ON CONFLICT (student_id, billing_period, invoice_kind)
            WHERE student_id IS NOT NULL
              AND invoice_kind = 'monthly'
              AND status <> 'voided'
        DO NOTHING
        RETURNING id
        """,
        (
            invoice_number,
            int(cycle_row["student_id"]),
            int(parent_id) if parent_id else None,
            int(cycle_row["id"]),
            cycle_row["billing_period"],
            str(cycle_row["currency"]),
            int(remaining_minor),
            due_date,
        ),
    ).fetchone()
    if not row:
        return 0
    invoice_id = int(row["id"])
    allocation_left = int(cycle_row["allocated_minor"])
    for item in item_rows:
        item_minor = int(item["amount_minor"])
        covered_minor = min(allocation_left, item_minor)
        allocation_left -= covered_minor
        line_minor = item_minor - covered_minor
        if line_minor <= 0:
            continue
        conn.execute(
            """
            INSERT INTO msi_v2.invoice_lines (
                invoice_id, group_id, subject_id, description, amount_minor, created_at
            )
            VALUES (%s, %s, %s, %s, %s, now())
            """,
            (
                invoice_id,
                item["group_id"],
                item["subject_id"],
                str(item["description"]),
                line_minor,
            ),
        )
    return invoice_id


__all__ = [
    "get_cycle_by_profile_period_row",
    "get_cycle_row",
    "get_available_manual_invoice_row",
    "get_review_row",
    "insert_cycle",
    "insert_cycle_invoice",
    "insert_review",
    "list_active_profile_rows",
    "list_cycle_item_rows",
    "list_cycle_review_rows",
    "list_manual_candidate_rows",
    "list_parent_cycle_rows",
    "list_scoped_cycle_rows",
    "list_snapshot_item_rows",
    "recompute_cycle_allocation",
    "reverse_review",
    "sync_cycle_state_for_invoice",
    "update_cycle_state",
]
