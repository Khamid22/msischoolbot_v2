"""Payment SQL helpers backed by msi_v2.payments."""

from database.tables import ensure_payments_schema


def _payment_select():
    return """
        id,
        student_id AS student_row_id,
        '' AS subject,
        month_label,
        amount::float AS amount,
        currency,
        status,
        COALESCE(due_date::text, '') AS due_date,
        COALESCE(paid_at::text, '') AS paid_at,
        notes,
        created_by_staff_id AS created_by_admin_id,
        created_at::text AS created_at,
        updated_at::text AS updated_at
    """


def list_student_payment_rows(conn, student_row_id):
    return conn.execute(
        f"""
        SELECT {_payment_select()}
        FROM msi_v2.payments
        WHERE student_id = %s
        ORDER BY COALESCE(due_date, DATE '9999-12-31') ASC, id ASC
        """,
        (int(student_row_id),),
    ).fetchall()


def get_student_payment_row(conn, payment_id):
    return conn.execute(
        f"""
        SELECT {_payment_select()}
        FROM msi_v2.payments
        WHERE id = %s
        """,
        (int(payment_id),),
    ).fetchone()


def insert_student_payment_row(
    conn,
    *,
    student_row_id,
    subject,
    month_label,
    amount,
    currency,
    status,
    due_date,
    paid_at,
    notes,
    created_by_admin_id,
    created_at,
    updated_at,
):
    row = conn.execute(
        f"""
        INSERT INTO msi_v2.payments (
            student_id,
            month_label,
            amount,
            currency,
            status,
            due_date,
            paid_at,
            notes,
            created_by_staff_id,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, NULLIF(%s, '')::date, NULLIF(%s, '')::timestamptz,
            %s,
            (
                SELECT id
                FROM msi_v2.msi_staff
                WHERE id = %s OR legacy_admin_id = %s
                ORDER BY id
                LIMIT 1
            ),
            COALESCE(NULLIF(%s, '')::timestamptz, now()),
            COALESCE(NULLIF(%s, '')::timestamptz, now())
        )
        RETURNING {_payment_select()}
        """,
        (
            int(student_row_id),
            str(month_label or "").strip(),
            float(amount or 0),
            str(currency or "UZS").strip() or "UZS",
            str(status or "due").strip().casefold() or "due",
            str(due_date or "").strip(),
            str(paid_at or "").strip(),
            str(notes or "").strip(),
            int(created_by_admin_id) if created_by_admin_id else None,
            int(created_by_admin_id) if created_by_admin_id else None,
            str(created_at or "").strip(),
            str(updated_at or "").strip(),
        ),
    ).fetchone()
    return row


def update_student_payment_paid_row(conn, payment_id, *, paid_at, status, updated_at):
    conn.execute(
        """
        UPDATE msi_v2.payments
        SET paid_at = NULLIF(%s, '')::timestamptz,
            status = %s,
            updated_at = COALESCE(NULLIF(%s, '')::timestamptz, now())
        WHERE id = %s
        """,
        (
            str(paid_at or "").strip(),
            str(status or "due").strip().casefold() or "due",
            str(updated_at or "").strip(),
            int(payment_id),
        ),
    )


def delete_student_payment_row(conn, payment_id):
    deleted = conn.execute(
        """
        DELETE FROM msi_v2.payments
        WHERE id = %s
        """,
        (int(payment_id),),
    )
    return int(deleted.rowcount or 0)


__all__ = [
    "delete_student_payment_row",
    "ensure_payments_schema",
    "get_student_payment_row",
    "insert_student_payment_row",
    "list_student_payment_rows",
    "update_student_payment_paid_row",
]
