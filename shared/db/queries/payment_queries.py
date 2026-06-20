"""Student payment ledger SQL helpers."""


def list_student_payment_rows(conn, student_row_id):
    return conn.execute(
        """
        SELECT
            id,
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
            updated_at
        FROM student_payments
        WHERE student_row_id = %s
        ORDER BY
            CASE WHEN trim(COALESCE(due_date, '')) = '' THEN '9999-12-31' ELSE due_date END ASC,
            id ASC
        """,
        (int(student_row_id),),
    ).fetchall()


def get_student_payment_row(conn, payment_id):
    return conn.execute(
        """
        SELECT
            id,
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
            updated_at
        FROM student_payments
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
        """
        INSERT INTO student_payments (
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
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING
            id,
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
            updated_at
        """,
        (
            int(student_row_id),
            str(subject or "").strip(),
            str(month_label or "").strip(),
            float(amount or 0),
            str(currency or "UZS").strip() or "UZS",
            str(status or "due").strip().casefold() or "due",
            str(due_date or "").strip(),
            str(paid_at or "").strip(),
            str(notes or "").strip(),
            int(created_by_admin_id) if created_by_admin_id else None,
            str(created_at or "").strip(),
            str(updated_at or "").strip(),
        ),
    ).fetchone()
    return row


def update_student_payment_paid_row(conn, payment_id, *, paid_at, status, updated_at):
    conn.execute(
        """
        UPDATE student_payments
        SET paid_at = %s,
            status = %s,
            updated_at = %s
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
        DELETE FROM student_payments
        WHERE id = %s
        """,
        (int(payment_id),),
    )
    return int(deleted.rowcount or 0)


__all__ = [
    "delete_student_payment_row",
    "get_student_payment_row",
    "insert_student_payment_row",
    "list_student_payment_rows",
    "update_student_payment_paid_row",
]
