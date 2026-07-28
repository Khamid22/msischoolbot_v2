"""Payment SQL helpers backed by ``msi_v2.payments``.

``payments.student_id`` is a foreign key to the canonical ``students.id``.
Role workspaces still accept the migration-era ``legacy_student_row_id``;
the conversion happens at this repository boundary so legacy ids never leak
into foreign-key columns.
"""

NEW_INVOICE_PAYMENT_ID_OFFSET = 2_000_000_000_000


def _payment_select():
    return """
        p.id,
        st.legacy_student_row_id AS student_row_id,
        COALESCE(sub.subject_name, '') AS subject,
        p.month_label,
        p.amount::float AS amount,
        p.currency,
        p.status,
        COALESCE(p.due_date::text, '') AS due_date,
        COALESCE(p.paid_at::text, '') AS paid_at,
        p.notes,
        COALESCE(p.version, 1) AS version,
        COALESCE(p.voided_at::text, '') AS voided_at,
        COALESCE(p.void_reason, '') AS void_reason,
        p.created_by_staff_id AS created_by_admin_id,
        p.created_at::text AS created_at,
        p.updated_at::text AS updated_at
    """


def list_student_payment_rows(conn, student_row_id):
    return conn.execute(
        f"""
        WITH legacy_payments AS (
            SELECT {_payment_select()}
            FROM msi_v2.payments p
            JOIN msi_v2.students st ON st.id = p.student_id
            LEFT JOIN msi_v2.groups g ON g.id = p.group_id
            LEFT JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            LEFT JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            WHERE st.legacy_student_row_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM msi_v2.invoices migrated_invoice
                  WHERE migrated_invoice.legacy_payment_id = p.id
              )
        ),
        canonical_invoices AS (
            SELECT
                %s + invoice.id AS id,
                student.legacy_student_row_id AS student_row_id,
                COALESCE(
                    string_agg(
                        line.description,
                        ', '
                        ORDER BY line.id
                    ),
                    'School services'
                ) AS subject,
                to_char(invoice.billing_period, 'YYYY-MM') AS month_label,
                (
                    CASE
                        WHEN invoice.status = 'paid' THEN invoice.total_minor
                        ELSE invoice.total_minor - invoice.paid_minor
                    END::numeric / 100
                )::float AS amount,
                invoice.currency,
                invoice.status,
                invoice.due_date::text AS due_date,
                COALESCE(invoice.paid_at::text, '') AS paid_at,
                'Invoice ' || invoice.invoice_number AS notes,
                invoice.version,
                COALESCE(invoice.voided_at::text, '') AS voided_at,
                invoice.void_reason,
                invoice.created_by_staff_id AS created_by_admin_id,
                invoice.created_at::text AS created_at,
                invoice.updated_at::text AS updated_at
            FROM msi_v2.invoices invoice
            JOIN msi_v2.students student ON student.id = invoice.student_id
            LEFT JOIN msi_v2.invoice_lines line ON line.invoice_id = invoice.id
            WHERE student.legacy_student_row_id = %s
            GROUP BY invoice.id, student.legacy_student_row_id
        )
        SELECT *
        FROM (
            SELECT * FROM legacy_payments
            UNION ALL
            SELECT * FROM canonical_invoices
        ) payment_record
        ORDER BY COALESCE(NULLIF(payment_record.due_date, '')::date, DATE '9999-12-31'),
                 payment_record.id
        """,
        (
            int(student_row_id),
            NEW_INVOICE_PAYMENT_ID_OFFSET,
            int(student_row_id),
        ),
    ).fetchall()


def get_student_payment_row(conn, payment_id):
    return conn.execute(
        f"""
        SELECT {_payment_select()}
        FROM msi_v2.payments p
        JOIN msi_v2.students st ON st.id = p.student_id
        LEFT JOIN msi_v2.groups g ON g.id = p.group_id
        LEFT JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        LEFT JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        WHERE p.id = %s
        """,
        (int(payment_id),),
    ).fetchone()


def get_internal_student_id(conn, student_row_id):
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.students
        WHERE legacy_student_row_id = %s
        LIMIT 1
        """,
        (int(student_row_id),),
    ).fetchone()
    return int(row["id"]) if row else None


def get_internal_student_group_id(conn, student_row_id, subject):
    row = conn.execute(
        """
        SELECT gs.group_id
        FROM msi_v2.students st
        JOIN msi_v2.group_students gs
          ON gs.student_id = st.id
         AND gs.enrollment_status = 'active'
        JOIN msi_v2.groups g ON g.id = gs.group_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
        WHERE st.legacy_student_row_id = %s
          AND lower(btrim(sub.subject_name)) = lower(btrim(%s))
        ORDER BY gs.joined_at DESC, gs.group_id
        LIMIT 1
        """,
        (int(student_row_id), str(subject or "").strip()),
    ).fetchone()
    return int(row["group_id"]) if row else None


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
    internal_student_id = get_internal_student_id(conn, student_row_id)
    if internal_student_id is None:
        return None
    group_id = get_internal_student_group_id(conn, student_row_id, subject)
    if group_id is None:
        return None

    row = conn.execute(
        """
        INSERT INTO msi_v2.payments (
            student_id,
            group_id,
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
            %s,
            %s,
            %s, %s, %s, %s, NULLIF(%s, '')::date, NULLIF(%s, '')::timestamptz,
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
        RETURNING id
        """,
        (
            internal_student_id,
            group_id,
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
    return get_student_payment_row(conn, int(row["id"])) if row else None


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


__all__ = [
    "NEW_INVOICE_PAYMENT_ID_OFFSET",
    "get_student_payment_row",
    "get_internal_student_id",
    "get_internal_student_group_id",
    "insert_student_payment_row",
    "list_student_payment_rows",
    "update_student_payment_paid_row",
]
