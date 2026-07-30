"""Persistence for current-student recurring billing profiles."""

from __future__ import annotations

from datetime import date
from typing import Any

from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import ledger_repository
from backend.modules.domains.finance.domain_types import BillingProfileStatus


def get_billing_profile_row(
    conn: Connection,
    student_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT *
        FROM msi_v2.student_billing_profiles
        WHERE student_id = %s
        {lock}
        """,
        (int(student_id),),
    ).fetchone()


def list_billing_item_rows(conn: Connection, profile_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT item.*, group_row.group_name, subject.subject_name
        FROM msi_v2.student_billing_items item
        JOIN msi_v2.groups group_row ON group_row.id = item.group_id
        JOIN msi_v2.subjects subject ON subject.id = item.subject_id
        WHERE item.profile_id = %s
          AND item.status = 'active'
          AND item.active_until IS NULL
        ORDER BY subject.subject_name, group_row.group_name, item.id
        """,
        (int(profile_id),),
    ).fetchall()


def upsert_billing_profile(
    conn: Connection,
    *,
    student_id: int,
    school_id: int,
    billing_parent_id: int | None,
    billing_day: int,
    starts_on: date,
    status: BillingProfileStatus,
    expected_version: int | None,
    staff_id: int | None,
) -> int:
    current = get_billing_profile_row(conn, student_id, for_update=True)
    if current:
        if expected_version is None or int(current["version"]) != int(expected_version):
            return 0
        row = conn.execute(
            """
            UPDATE msi_v2.student_billing_profiles
            SET school_id = %s, billing_parent_id = %s, billing_day = %s,
                starts_on = %s, status = %s, updated_by_staff_id = %s,
                version = version + 1, updated_at = now()
            WHERE id = %s AND version = %s
            RETURNING id
            """,
            (
                int(school_id),
                int(billing_parent_id) if billing_parent_id else None,
                int(billing_day),
                starts_on,
                status.value,
                int(staff_id) if staff_id else None,
                int(current["id"]),
                int(expected_version),
            ),
        ).fetchone()
        return int(row["id"]) if row else 0
    if expected_version is not None:
        return 0
    row = conn.execute(
        """
        INSERT INTO msi_v2.student_billing_profiles (
            student_id, school_id, billing_parent_id, billing_day, currency,
            starts_on, status, version, created_by_staff_id, updated_by_staff_id,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'UZS', %s, %s, 1, %s, %s, now(), now())
        RETURNING id
        """,
        (
            int(student_id),
            int(school_id),
            int(billing_parent_id) if billing_parent_id else None,
            int(billing_day),
            starts_on,
            status.value,
            int(staff_id) if staff_id else None,
            int(staff_id) if staff_id else None,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def replace_billing_items(
    conn: Connection,
    *,
    profile_id: int,
    starts_on: date,
    items: list[tuple[int, int, str, int]],
    staff_id: int | None,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.student_billing_items
        SET status = 'cancelled',
            cancelled_at = now(),
            cancelled_by_staff_id = %s,
            cancellation_reason = 'superseded_by_billing_profile',
            version = version + 1,
            updated_at = now()
        WHERE profile_id = %s
          AND status = 'active'
          AND active_from >= %s
        """,
        (
            int(staff_id) if staff_id else None,
            int(profile_id),
            starts_on,
        ),
    )
    conn.execute(
        """
        UPDATE msi_v2.student_billing_items
        SET active_until = %s - 1,
            version = version + 1,
            updated_at = now()
        WHERE profile_id = %s
          AND status = 'active'
          AND active_from < %s
          AND (active_until IS NULL OR active_until >= %s)
        """,
        (starts_on, int(profile_id), starts_on, starts_on),
    )
    for group_id, subject_id, description, amount_minor in items:
        conn.execute(
            """
            INSERT INTO msi_v2.student_billing_items (
                profile_id, group_id, subject_id, description,
                amount_minor, active_from, active_until, status,
                cancelled_at, cancelled_by_staff_id, cancellation_reason,
                version, created_at, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, NULL, 'active',
                NULL, NULL, '', 1, now(), now()
            )
            ON CONFLICT (profile_id, group_id, active_from)
            DO UPDATE SET
                subject_id = excluded.subject_id,
                description = excluded.description,
                amount_minor = excluded.amount_minor,
                active_until = NULL,
                status = 'active',
                cancelled_at = NULL,
                cancelled_by_staff_id = NULL,
                cancellation_reason = '',
                version = msi_v2.student_billing_items.version + 1,
                updated_at = now()
            """,
            (
                int(profile_id),
                int(group_id),
                int(subject_id),
                description.strip(),
                int(amount_minor),
                starts_on,
            ),
        )


def list_due_billing_profile_rows(conn: Connection, run_date: date) -> list[Any]:
    return conn.execute(
        """
        SELECT profile.*
        FROM msi_v2.student_billing_profiles profile
        JOIN msi_v2.students student ON student.id = profile.student_id
        WHERE profile.status = 'active'
          AND student.status = 'active'
          AND profile.starts_on <= %s
          AND (profile.ends_on IS NULL OR profile.ends_on >= %s)
          AND profile.billing_day <= LEAST(EXTRACT(DAY FROM %s::date)::int, 28)
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.invoices invoice
              WHERE invoice.student_id = profile.student_id
                AND invoice.billing_period = date_trunc('month', %s::date)::date
                AND invoice.invoice_kind = 'monthly'
                AND invoice.status <> 'voided'
          )
        ORDER BY profile.id
        FOR UPDATE OF profile SKIP LOCKED
        """,
        (run_date, run_date, run_date, run_date),
    ).fetchall()


def list_active_profile_item_rows(
    conn: Connection,
    *,
    profile_id: int,
    run_date: date,
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
        (int(profile_id), run_date, run_date),
    ).fetchall()


def insert_generated_monthly_invoice(
    conn: Connection,
    *,
    profile_row: Any,
    item_rows: list[Any],
    run_date: date,
) -> int:
    total_minor = sum(int(row["amount_minor"]) for row in item_rows)
    if total_minor <= 0:
        return 0
    invoice_number = ledger_repository.next_invoice_number(conn)
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoices (
            invoice_number, student_id, parent_id, invoice_kind, billing_period,
            currency, total_minor, paid_minor, status, due_date, issued_at,
            version, origin, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, 'monthly', date_trunc('month', %s::date)::date,
            'UZS', %s, 0, 'issued', %s, now(), 1, 'student_billing', now(), now()
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
            int(profile_row["student_id"]),
            (int(profile_row["billing_parent_id"]) if profile_row["billing_parent_id"] else None),
            run_date,
            total_minor,
            run_date,
        ),
    ).fetchone()
    if not row:
        return 0
    invoice_id = int(row["id"])
    for item in item_rows:
        conn.execute(
            """
            INSERT INTO msi_v2.invoice_lines (
                invoice_id, group_id, subject_id, description, amount_minor, created_at
            )
            VALUES (%s, %s, %s, %s, %s, now())
            """,
            (
                invoice_id,
                int(item["group_id"]),
                int(item["subject_id"]),
                str(item["description"]),
                int(item["amount_minor"]),
            ),
        )
    return invoice_id


__all__ = [
    "get_billing_profile_row",
    "insert_generated_monthly_invoice",
    "list_active_profile_item_rows",
    "list_billing_item_rows",
    "list_due_billing_profile_rows",
    "replace_billing_items",
    "upsert_billing_profile",
]
