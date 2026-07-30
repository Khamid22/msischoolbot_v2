"""PostgreSQL persistence for the canonical invoice ledger."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from backend.core.unit_of_work import Connection
from backend.modules.domains.finance.domain_types import InvoiceKind, ManualPaymentMethod


def list_scoped_invoice_rows(
    conn: Connection,
    *,
    school_ids: Iterable[int],
    all_schools: bool,
    query: str,
    status: str,
    origin: str,
    enforcement: str = "all",
    school_id: int | None = None,
    billing_period: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Any]:
    search = f"%{query.strip()}%"
    return conn.execute(
        """
        SELECT invoice.*,
               enforcement.state AS enforcement_state,
               enforcement.countdown_started_at,
               enforcement.deadline_at AS payment_deadline_at,
               student.legacy_student_row_id,
               COALESCE(student.full_name, admission.student_full_name, '') AS student_name,
               COALESCE(student.student_code, '') AS student_code,
               COALESCE(parent.display_name, admission.parent_full_name, '') AS parent_name,
               COALESCE(student.school_id, admission.school_id) AS school_id,
               school.school_name,
               count(*) OVER () AS total_count
        FROM msi_v2.invoices invoice
        LEFT JOIN msi_v2.admissions admission ON admission.id = invoice.admission_id
        LEFT JOIN msi_v2.students student ON student.id = invoice.student_id
        LEFT JOIN msi_v2.parents parent ON parent.id = invoice.parent_id
        LEFT JOIN msi_v2.invoice_enforcement_schedules enforcement
          ON enforcement.invoice_id = invoice.id
        JOIN msi_v2.schools school
          ON school.id = COALESCE(student.school_id, admission.school_id)
        WHERE (%s OR school.id = ANY(%s::bigint[]))
          AND (%s::bigint IS NULL OR school.id = %s)
          AND (%s = 'all' OR invoice.status = %s)
          AND (%s = 'all' OR invoice.origin = %s)
          AND (%s::date IS NULL OR invoice.billing_period = %s)
          AND (
              %s = 'all'
              OR (%s = 'not_scheduled' AND enforcement.id IS NULL)
              OR enforcement.state = %s
          )
          AND (
              %s = ''
              OR invoice.invoice_number ILIKE %s
              OR COALESCE(student.full_name, admission.student_full_name, '') ILIKE %s
              OR COALESCE(parent.display_name, admission.parent_full_name, '') ILIKE %s
              OR COALESCE(student.student_code, '') ILIKE %s
          )
        ORDER BY
            CASE invoice.status
                WHEN 'overdue' THEN 0
                WHEN 'partially_paid' THEN 1
                WHEN 'issued' THEN 2
                WHEN 'paid' THEN 3
                ELSE 4
            END,
            invoice.due_date,
            invoice.id DESC
        LIMIT %s
        OFFSET %s
        """,
        (
            bool(all_schools),
            list(school_ids),
            school_id,
            school_id,
            status,
            status,
            origin,
            origin,
            billing_period,
            billing_period,
            enforcement,
            enforcement,
            enforcement,
            query.strip(),
            search,
            search,
            search,
            search,
            max(1, min(int(limit), 101)),
            max(0, int(offset)),
        ),
    ).fetchall()


def get_invoice_row(
    conn: Connection,
    *,
    invoice_id: int,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF invoice" if for_update else ""
    return conn.execute(
        f"""
        SELECT invoice.*,
               enforcement.state AS enforcement_state,
               enforcement.countdown_started_at,
               enforcement.deadline_at AS payment_deadline_at,
               student.legacy_student_row_id,
               COALESCE(student.full_name, admission.student_full_name, '') AS student_name,
               COALESCE(student.student_code, '') AS student_code,
               COALESCE(parent.display_name, admission.parent_full_name, '') AS parent_name,
               COALESCE(student.school_id, admission.school_id) AS school_id,
               school.school_name
        FROM msi_v2.invoices invoice
        LEFT JOIN msi_v2.admissions admission ON admission.id = invoice.admission_id
        LEFT JOIN msi_v2.students student ON student.id = invoice.student_id
        LEFT JOIN msi_v2.parents parent ON parent.id = invoice.parent_id
        LEFT JOIN msi_v2.invoice_enforcement_schedules enforcement
          ON enforcement.invoice_id = invoice.id
        JOIN msi_v2.schools school
          ON school.id = COALESCE(student.school_id, admission.school_id)
        WHERE invoice.id = %s
        {lock}
        """,
        (int(invoice_id),),
    ).fetchone()


def list_invoice_line_rows(conn: Connection, invoice_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT id, group_id, subject_id, description, amount_minor
        FROM msi_v2.invoice_lines
        WHERE invoice_id = %s
        ORDER BY id
        """,
        (int(invoice_id),),
    ).fetchall()


def list_invoice_payment_rows(conn: Connection, invoice_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT *
        FROM msi_v2.invoice_payments
        WHERE invoice_id = %s
        ORDER BY paid_at, id
        """,
        (int(invoice_id),),
    ).fetchall()


def get_scoped_student_row(
    conn: Connection,
    *,
    student_id: int,
    school_ids: Iterable[int],
    all_schools: bool,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT student.*, school.school_name
        FROM msi_v2.students student
        JOIN msi_v2.schools school ON school.id = student.school_id
        WHERE student.id = %s
          AND (%s OR student.school_id = ANY(%s::bigint[]))
        {lock}
        """,
        (int(student_id), bool(all_schools), list(school_ids)),
    ).fetchone()


def find_active_enrollment_row(
    conn: Connection,
    *,
    student_id: int,
    subject_id: int,
) -> Any:
    return conn.execute(
        """
        SELECT enrollment.group_id, group_row.group_name,
               subject.id AS subject_id, subject.subject_name
        FROM msi_v2.group_students enrollment
        JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
        JOIN msi_v2.subject_programs program ON program.id = group_row.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE enrollment.student_id = %s
          AND enrollment.enrollment_status = 'active'
          AND group_row.status = 'active'
          AND subject.id = %s
        ORDER BY enrollment.joined_at DESC, enrollment.group_id
        LIMIT 1
        """,
        (int(student_id), int(subject_id)),
    ).fetchone()


def find_active_group_enrollment_row(
    conn: Connection,
    *,
    student_id: int,
    group_id: int,
) -> Any:
    return conn.execute(
        """
        SELECT enrollment.group_id, subject.id AS subject_id,
               subject.subject_name, group_row.group_name
        FROM msi_v2.group_students enrollment
        JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
        JOIN msi_v2.subject_programs program ON program.id = group_row.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE enrollment.student_id = %s
          AND enrollment.group_id = %s
          AND enrollment.enrollment_status = 'active'
        """,
        (int(student_id), int(group_id)),
    ).fetchone()


def next_invoice_number(conn: Connection) -> str:
    row = conn.execute(
        """
        SELECT 'INV-' || to_char(CURRENT_DATE, 'YYYY') || '-' ||
               lpad(nextval('msi_v2.student_invoice_number_seq')::text, 8, '0')
               AS invoice_number
        """
    ).fetchone()
    return str(row["invoice_number"])


def insert_student_invoice(
    conn: Connection,
    *,
    student_id: int,
    parent_id: int | None,
    group_id: int,
    subject_id: int,
    description: str,
    amount_minor: int,
    due_date: date,
    billing_period: date,
    invoice_kind: InvoiceKind,
    staff_id: int | None,
) -> int:
    invoice_number = next_invoice_number(conn)
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoices (
            invoice_number, admission_id, student_id, parent_id,
            invoice_kind, billing_period, currency, total_minor, paid_minor,
            status, due_date, issued_at, version, created_by_staff_id,
            origin, created_at, updated_at
        )
        VALUES (
            %s, NULL, %s, %s, %s, %s, 'UZS', %s, 0,
            CASE WHEN %s < CURRENT_DATE THEN 'overdue' ELSE 'issued' END,
            %s, now(), 1, %s, 'student_billing', now(), now()
        )
        RETURNING id
        """,
        (
            invoice_number,
            int(student_id),
            int(parent_id) if parent_id else None,
            invoice_kind.value,
            billing_period,
            int(amount_minor),
            due_date,
            due_date,
            int(staff_id) if staff_id else None,
        ),
    ).fetchone()
    invoice_id = int(row["id"])
    conn.execute(
        """
        INSERT INTO msi_v2.invoice_lines (
            invoice_id, group_id, subject_id, description, amount_minor, created_at
        )
        VALUES (%s, %s, %s, %s, %s, now())
        """,
        (
            invoice_id,
            int(group_id),
            int(subject_id),
            description.strip(),
            int(amount_minor),
        ),
    )
    return invoice_id


def find_billing_parent_id(conn: Connection, student_id: int) -> int | None:
    rows = conn.execute(
        """
        SELECT parent_id
        FROM msi_v2.parent_student_links
        WHERE student_id = %s AND status = 'active'
        ORDER BY parent_id
        LIMIT 2
        """,
        (int(student_id),),
    ).fetchall()
    return int(rows[0]["parent_id"]) if len(rows) == 1 else None


def find_pending_payme_transaction(conn: Connection, invoice_id: int) -> Any:
    return conn.execute(
        """
        SELECT id
        FROM msi_v2.payme_transactions
        WHERE invoice_id = %s AND state = 1
        ORDER BY id
        LIMIT 1
        """,
        (int(invoice_id),),
    ).fetchone()


def find_invoice_id_by_legacy_payment(
    conn: Connection,
    legacy_payment_id: int,
) -> int | None:
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.invoices
        WHERE legacy_payment_id = %s
        """,
        (int(legacy_payment_id),),
    ).fetchone()
    return int(row["id"]) if row else None


def parent_has_invoice_access(
    conn: Connection,
    *,
    parent_id: int,
    invoice_id: int,
) -> bool:
    row = conn.execute(
        """
        SELECT invoice.id
        FROM msi_v2.invoices invoice
        JOIN msi_v2.parent_student_links link
          ON link.student_id = invoice.student_id
         AND link.status = 'active'
        WHERE invoice.id = %s AND link.parent_id = %s
        """,
        (int(invoice_id), int(parent_id)),
    ).fetchone()
    return bool(row)


def insert_manual_payment(
    conn: Connection,
    *,
    invoice_id: int,
    amount_minor: int,
    method: ManualPaymentMethod,
    paid_at: datetime,
    reference: str,
    reason: str,
    staff_id: int | None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoice_payments (
            invoice_id, source, method, amount_minor, currency, status,
            provider_transaction_id, reference, reason, paid_at,
            recorded_by_staff_id, created_at
        )
        VALUES (
            %s, 'manual', %s, %s, 'UZS', 'completed',
            NULL, %s, %s, %s, %s, now()
        )
        RETURNING id
        """,
        (
            int(invoice_id),
            method.value,
            int(amount_minor),
            reference.strip(),
            reason.strip(),
            paid_at,
            int(staff_id) if staff_id else None,
        ),
    ).fetchone()
    return int(row["id"])


def recompute_invoice_settlement(conn: Connection, invoice_id: int) -> Any:
    return conn.execute(
        """
        WITH settlement AS (
            SELECT COALESCE(
                SUM(amount_minor) FILTER (WHERE status = 'completed'),
                0
            )::bigint AS paid_minor
            FROM msi_v2.invoice_payments
            WHERE invoice_id = %s
        )
        UPDATE msi_v2.invoices invoice
        SET paid_minor = LEAST(settlement.paid_minor, invoice.total_minor),
            status = CASE
                WHEN settlement.paid_minor >= invoice.total_minor THEN 'paid'
                WHEN settlement.paid_minor > 0 THEN 'partially_paid'
                WHEN invoice.due_date < CURRENT_DATE THEN 'overdue'
                ELSE 'issued'
            END,
            paid_at = CASE
                WHEN settlement.paid_minor >= invoice.total_minor
                THEN COALESCE(invoice.paid_at, now())
                ELSE NULL
            END,
            version = invoice.version + 1,
            updated_at = now()
        FROM settlement
        WHERE invoice.id = %s
        RETURNING invoice.*
        """,
        (int(invoice_id), int(invoice_id)),
    ).fetchone()


def get_payment_row(
    conn: Connection,
    *,
    payment_id: int,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT *
        FROM msi_v2.invoice_payments
        WHERE id = %s
        {lock}
        """,
        (int(payment_id),),
    ).fetchone()


def reverse_payment(
    conn: Connection,
    *,
    payment_id: int,
    reason: str,
    staff_id: int | None,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.invoice_payments
        SET status = 'reversed',
            reversed_at = now(),
            reversed_by_staff_id = %s,
            reversal_reason = %s
        WHERE id = %s AND status = 'completed'
        RETURNING id
        """,
        (int(staff_id) if staff_id else None, reason.strip(), int(payment_id)),
    ).fetchone()
    return bool(row)


def void_invoice(
    conn: Connection,
    *,
    invoice_id: int,
    expected_version: int,
    reason: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.invoices
        SET status = 'voided', voided_at = now(), void_reason = %s,
            version = version + 1, updated_at = now()
        WHERE id = %s AND version = %s AND paid_minor = 0 AND status <> 'voided'
        RETURNING id
        """,
        (reason.strip(), int(invoice_id), int(expected_version)),
    ).fetchone()
    return bool(row)


def insert_audit_event(
    conn: Connection,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int,
    detail: dict[str, object],
    staff_id: int | None,
    account_id: int | None,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, actor_account_id, event_type,
            entity_type, entity_id, detail_json, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, now())
        """,
        (
            int(staff_id) if staff_id else None,
            int(account_id) if account_id else None,
            event_type,
            entity_type,
            int(entity_id),
            json.dumps(detail, ensure_ascii=False, default=str),
        ),
    )


__all__ = [
    "find_active_enrollment_row",
    "find_active_group_enrollment_row",
    "find_billing_parent_id",
    "find_invoice_id_by_legacy_payment",
    "find_pending_payme_transaction",
    "get_invoice_row",
    "get_payment_row",
    "get_scoped_student_row",
    "insert_audit_event",
    "insert_manual_payment",
    "insert_student_invoice",
    "list_invoice_line_rows",
    "list_invoice_payment_rows",
    "list_scoped_invoice_rows",
    "parent_has_invoice_access",
    "recompute_invoice_settlement",
    "reverse_payment",
    "next_invoice_number",
    "void_invoice",
]
