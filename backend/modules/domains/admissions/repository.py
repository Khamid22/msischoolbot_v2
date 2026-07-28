"""PostgreSQL persistence owned by the admissions domain."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any

from backend.core.unit_of_work import Connection


def list_group_option_rows(
    conn: Connection,
    *,
    school_ids: Iterable[int],
    all_schools: bool,
) -> list[Any]:
    return conn.execute(
        """
        SELECT g.id AS group_id, g.school_id, school.school_name,
               g.group_name, subject.id AS subject_id, subject.subject_name
        FROM msi_v2.groups g
        JOIN msi_v2.schools school ON school.id = g.school_id
        JOIN msi_v2.subject_programs program ON program.id = g.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE g.status = 'active'
          AND school.status = 'active'
          AND subject.status = 'active'
          AND (%s OR g.school_id = ANY(%s))
        ORDER BY school.school_name, subject.subject_name, g.group_name, g.id
        """,
        (bool(all_schools), list(school_ids)),
    ).fetchall()


def lock_group_selection_rows(
    conn: Connection,
    *,
    school_id: int,
    group_ids: Iterable[int],
) -> list[Any]:
    return conn.execute(
        """
        SELECT g.id AS group_id, g.school_id, g.group_name,
               subject.id AS subject_id, subject.subject_name
        FROM msi_v2.groups g
        JOIN msi_v2.subject_programs program ON program.id = g.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE g.id = ANY(%s)
          AND g.school_id = %s
          AND g.status = 'active'
          AND subject.status = 'active'
        ORDER BY subject.subject_name, g.group_name, g.id
        FOR SHARE OF g
        """,
        (list(group_ids), int(school_id)),
    ).fetchall()


def insert_admission(
    conn: Connection,
    *,
    school_id: int,
    student_full_name: str,
    student_phone: str,
    parent_full_name: str,
    parent_phone: str,
    parent_telegram_username: str,
    preferred_language: str,
    service_start_date: date | None,
    first_due_date: date,
    billing_day: int,
    created_by_staff_id: int | None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.admissions (
            school_id, student_full_name, student_phone,
            parent_full_name, parent_phone, parent_telegram_username,
            preferred_language, service_start_date, first_due_date,
            billing_day, currency, status, version, created_by_staff_id,
            created_at, updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            'UZS', 'draft', 1, %s, now(), now()
        )
        RETURNING id
        """,
        (
            int(school_id),
            student_full_name,
            student_phone,
            parent_full_name,
            parent_phone,
            parent_telegram_username,
            preferred_language,
            service_start_date,
            first_due_date,
            int(billing_day),
            created_by_staff_id,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_group_selections(
    conn: Connection,
    *,
    admission_id: int,
    group_rows: Iterable[Mapping[str, Any]],
    amount_by_group_id: Mapping[int, int],
) -> None:
    for group in group_rows:
        group_id = int(group["group_id"])
        conn.execute(
            """
            INSERT INTO msi_v2.admission_group_selections (
                admission_id, group_id, subject_id,
                monthly_amount_minor, created_at
            )
            VALUES (%s, %s, %s, %s, now())
            """,
            (
                int(admission_id),
                group_id,
                int(group["subject_id"]),
                int(amount_by_group_id[group_id]),
            ),
        )


def update_admission(
    conn: Connection,
    *,
    admission_id: int,
    expected_version: int,
    student_full_name: str,
    student_phone: str,
    parent_full_name: str,
    parent_phone: str,
    parent_telegram_username: str,
    preferred_language: str,
    service_start_date: date | None,
    first_due_date: date,
    billing_day: int,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.admissions
        SET student_full_name = %s,
            student_phone = %s,
            parent_full_name = %s,
            parent_phone = %s,
            parent_telegram_username = %s,
            preferred_language = %s,
            service_start_date = %s,
            first_due_date = %s,
            billing_day = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND version = %s
          AND status NOT IN ('active', 'cancelled', 'expired')
        RETURNING id
        """,
        (
            student_full_name,
            student_phone,
            parent_full_name,
            parent_phone,
            parent_telegram_username,
            preferred_language,
            service_start_date,
            first_due_date,
            int(billing_day),
            int(admission_id),
            int(expected_version),
        ),
    ).fetchone()
    return bool(row)


def insert_access_token(
    conn: Connection,
    *,
    admission_id: int,
    token_hash: str,
    expires_at: datetime,
    replace_active: bool,
) -> None:
    if replace_active:
        conn.execute(
            """
            UPDATE msi_v2.admission_access_tokens
            SET revoked_at = now()
            WHERE admission_id = %s AND revoked_at IS NULL
            """,
            (int(admission_id),),
        )
    conn.execute(
        """
        INSERT INTO msi_v2.admission_access_tokens (
            admission_id, token_hash, expires_at, created_at
        )
        VALUES (%s, %s, %s, now())
        """,
        (int(admission_id), token_hash, expires_at),
    )


def get_admission_row(
    conn: Connection,
    admission_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF admission" if for_update else ""
    return conn.execute(
        f"""
        SELECT admission.*, school.school_name
        FROM msi_v2.admissions admission
        JOIN msi_v2.schools school ON school.id = admission.school_id
        WHERE admission.id = %s
        {lock}
        """,
        (int(admission_id),),
    ).fetchone()


def get_admission_by_token_hash(
    conn: Connection,
    token_hash: str,
) -> Any:
    return conn.execute(
        """
        SELECT admission.*, school.school_name, token.expires_at
        FROM msi_v2.admission_access_tokens token
        JOIN msi_v2.admissions admission ON admission.id = token.admission_id
        JOIN msi_v2.schools school ON school.id = admission.school_id
        WHERE token.token_hash = %s
          AND token.revoked_at IS NULL
          AND token.expires_at > now()
        """,
        (token_hash,),
    ).fetchone()


def touch_admission_access_token(
    conn: Connection,
    token_hash: str,
    *,
    request_limit: int,
    window_seconds: int,
) -> str:
    """Atomically enforce a per-token rate window across all web processes."""
    row = conn.execute(
        """
        UPDATE msi_v2.admission_access_tokens
        SET last_accessed_at = now(),
            rate_window_started_at = CASE
                WHEN rate_window_started_at <=
                     now() - make_interval(secs => %s)
                    THEN now()
                ELSE rate_window_started_at
            END,
            rate_window_requests = CASE
                WHEN rate_window_started_at <=
                     now() - make_interval(secs => %s)
                    THEN 1
                ELSE rate_window_requests + 1
            END
        WHERE token_hash = %s
          AND revoked_at IS NULL
          AND expires_at > now()
          AND (
              rate_window_started_at <= now() - make_interval(secs => %s)
              OR rate_window_requests < %s
          )
        RETURNING id
        """,
        (
            int(window_seconds),
            int(window_seconds),
            token_hash,
            int(window_seconds),
            int(request_limit),
        ),
    ).fetchone()
    if row:
        return "ok"
    valid_row = conn.execute(
        """
        SELECT id
        FROM msi_v2.admission_access_tokens
        WHERE token_hash = %s
          AND revoked_at IS NULL
          AND expires_at > now()
        """,
        (token_hash,),
    ).fetchone()
    return "rate_limited" if valid_row else "invalid"


def list_admission_rows(
    conn: Connection,
    *,
    school_ids: Iterable[int],
    all_schools: bool,
    query: str,
    status: str,
    limit: int,
) -> list[Any]:
    return conn.execute(
        """
        SELECT admission.id AS admission_id, admission.school_id,
               school.school_name, admission.student_full_name,
               admission.parent_full_name, admission.parent_phone,
               admission.status, admission.first_due_date,
               admission.updated_at,
               contract.status AS contract_status,
               first_invoice.status AS first_invoice_status,
               count(*) OVER () AS total_count
        FROM msi_v2.admissions admission
        JOIN msi_v2.schools school ON school.id = admission.school_id
        LEFT JOIN LATERAL (
            SELECT current_contract.status
            FROM msi_v2.admission_contracts current_contract
            WHERE current_contract.admission_id = admission.id
              AND current_contract.superseded_at IS NULL
            ORDER BY current_contract.version DESC
            LIMIT 1
        ) contract ON true
        LEFT JOIN LATERAL (
            SELECT invoice.status
            FROM msi_v2.invoices invoice
            WHERE invoice.admission_id = admission.id
              AND invoice.invoice_kind = 'first'
              AND invoice.status <> 'voided'
            ORDER BY invoice.created_at DESC, invoice.id DESC
            LIMIT 1
        ) first_invoice ON true
        WHERE (%s OR admission.school_id = ANY(%s))
          AND (%s = 'all' OR admission.status = %s)
          AND (
              %s = ''
              OR admission.student_full_name ILIKE %s
              OR admission.parent_full_name ILIKE %s
              OR admission.parent_phone ILIKE %s
          )
        ORDER BY admission.updated_at DESC, admission.id DESC
        LIMIT %s
        """,
        (
            bool(all_schools),
            list(school_ids),
            status,
            status,
            query,
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            int(limit),
        ),
    ).fetchall()


def list_admission_group_rows(conn: Connection, admission_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT selection.group_id, group_row.group_name,
               selection.subject_id, subject.subject_name,
               selection.monthly_amount_minor
        FROM msi_v2.admission_group_selections selection
        JOIN msi_v2.groups group_row ON group_row.id = selection.group_id
        JOIN msi_v2.subjects subject ON subject.id = selection.subject_id
        WHERE selection.admission_id = %s
        ORDER BY subject.subject_name, group_row.group_name, selection.group_id
        """,
        (int(admission_id),),
    ).fetchall()


def list_admission_audit_rows(conn: Connection, admission_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT id, event_type, entity_type, entity_id, detail_json,
               actor_staff_id, created_at
        FROM msi_v2.audit_events
        WHERE (
                entity_type = 'admission'
                AND entity_id = %s
              )
           OR detail_json ->> 'admission_id' = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 100
        """,
        (int(admission_id), str(int(admission_id))),
    ).fetchall()


def get_current_contract_row(
    conn: Connection,
    admission_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT *
        FROM msi_v2.admission_contracts
        WHERE admission_id = %s AND superseded_at IS NULL
        ORDER BY version DESC
        LIMIT 1
        {lock}
        """,
        (int(admission_id),),
    ).fetchone()


def insert_contract(
    conn: Connection,
    *,
    admission_id: int,
    object_key: str,
    original_file_name: str,
    mime_type: str,
    size_bytes: int,
) -> int:
    current = get_current_contract_row(conn, admission_id, for_update=True)
    version = int(current["version"]) + 1 if current else 1
    if current:
        conn.execute(
            """
            UPDATE msi_v2.admission_contracts
            SET status = 'superseded', superseded_at = now()
            WHERE id = %s
            """,
            (int(current["id"]),),
        )
    row = conn.execute(
        """
        INSERT INTO msi_v2.admission_contracts (
            admission_id, version, status,
            original_object_key, original_file_name,
            original_mime_type, original_size_bytes, created_at
        )
        VALUES (%s, %s, 'draft', %s, %s, %s, %s, now())
        RETURNING id
        """,
        (
            int(admission_id),
            version,
            object_key,
            original_file_name,
            mime_type,
            int(size_bytes),
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def mark_contract_sent(conn: Connection, *, admission_id: int, contract_id: int) -> None:
    conn.execute(
        """
        UPDATE msi_v2.admission_contracts
        SET status = 'sent'
        WHERE id = %s AND admission_id = %s
        """,
        (int(contract_id), int(admission_id)),
    )
    conn.execute(
        """
        UPDATE msi_v2.admissions
        SET status = 'contract_sent', version = version + 1, updated_at = now()
        WHERE id = %s
        """,
        (int(admission_id),),
    )


def submit_signed_contract(
    conn: Connection,
    *,
    contract_id: int,
    object_key: str,
    original_file_name: str,
    mime_type: str,
    size_bytes: int,
) -> int:
    contract_row = conn.execute(
        """
        SELECT *
        FROM msi_v2.admission_contracts
        WHERE id = %s
        FOR UPDATE
        """,
        (int(contract_id),),
    ).fetchone()
    if not contract_row:
        return 0
    submitted_contract_id = int(contract_id)
    if str(contract_row["status"]) == "rejected":
        conn.execute(
            """
            UPDATE msi_v2.admission_contracts
            SET superseded_at = now()
            WHERE id = %s
            """,
            (int(contract_id),),
        )
        inserted = conn.execute(
            """
            INSERT INTO msi_v2.admission_contracts (
                admission_id, version, status,
                original_object_key, original_file_name,
                original_mime_type, original_size_bytes,
                signed_object_key, signed_file_name,
                signed_mime_type, signed_size_bytes,
                submitted_at, created_at
            )
            VALUES (
                %s, %s, 'submitted',
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                now(), now()
            )
            RETURNING id
            """,
            (
                int(contract_row["admission_id"]),
                int(contract_row["version"]) + 1,
                str(contract_row["original_object_key"]),
                str(contract_row["original_file_name"]),
                str(contract_row["original_mime_type"]),
                int(contract_row["original_size_bytes"]),
                object_key,
                original_file_name,
                mime_type,
                int(size_bytes),
            ),
        ).fetchone()
        submitted_contract_id = int(inserted["id"])
    else:
        conn.execute(
            """
            UPDATE msi_v2.admission_contracts
            SET status = 'submitted',
                signed_object_key = %s,
                signed_file_name = %s,
                signed_mime_type = %s,
                signed_size_bytes = %s,
                submitted_at = now(),
                reviewed_at = NULL,
                reviewed_by_staff_id = NULL,
                rejection_reason = ''
            WHERE id = %s
            """,
            (
                object_key,
                original_file_name,
                mime_type,
                int(size_bytes),
                int(contract_id),
            ),
        )
    conn.execute(
        """
        UPDATE msi_v2.admissions
        SET status = 'contract_submitted', version = version + 1, updated_at = now()
        WHERE id = (
            SELECT admission_id FROM msi_v2.admission_contracts WHERE id = %s
        )
        """,
        (submitted_contract_id,),
    )
    return submitted_contract_id


def review_contract(
    conn: Connection,
    *,
    admission_id: int,
    contract_id: int,
    accepted: bool,
    staff_id: int | None,
    reason: str,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.admission_contracts
        SET status = %s,
            reviewed_at = now(),
            reviewed_by_staff_id = %s,
            rejection_reason = %s
        WHERE id = %s AND admission_id = %s
        """,
        (
            "accepted" if accepted else "rejected",
            staff_id,
            "" if accepted else reason,
            int(contract_id),
            int(admission_id),
        ),
    )
    conn.execute(
        """
        UPDATE msi_v2.admissions
        SET status = %s, version = version + 1, updated_at = now()
        WHERE id = %s
        """,
        ("awaiting_payment" if accepted else "contract_sent", int(admission_id)),
    )


def next_invoice_number(conn: Connection) -> str:
    row = conn.execute(
        "SELECT nextval('msi_v2.admission_invoice_number_seq') AS number"
    ).fetchone()
    return f"INV-{int(row['number']):08d}"


def insert_invoice(
    conn: Connection,
    *,
    admission_id: int,
    invoice_number: str,
    invoice_kind: str,
    billing_period: date,
    total_minor: int,
    due_date: date,
    created_by_staff_id: int | None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoices (
            invoice_number, admission_id, invoice_kind, billing_period,
            currency, total_minor, paid_minor, status, due_date,
            issued_at, version, created_by_staff_id, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, %s, 'UZS', %s, 0, 'issued', %s,
            now(), 1, %s, now(), now()
        )
        RETURNING id
        """,
        (
            invoice_number,
            int(admission_id),
            invoice_kind,
            billing_period,
            int(total_minor),
            due_date,
            created_by_staff_id,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_invoice_lines_from_admission(
    conn: Connection,
    *,
    admission_id: int,
    invoice_id: int,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.invoice_lines (
            invoice_id, group_id, subject_id, description,
            amount_minor, created_at
        )
        SELECT %s, selection.group_id, selection.subject_id,
               subject.subject_name || ' · ' || group_row.group_name,
               selection.monthly_amount_minor, now()
        FROM msi_v2.admission_group_selections selection
        JOIN msi_v2.groups group_row ON group_row.id = selection.group_id
        JOIN msi_v2.subjects subject ON subject.id = selection.subject_id
        WHERE selection.admission_id = %s
        ORDER BY subject.subject_name, group_row.group_name
        """,
        (int(invoice_id), int(admission_id)),
    )


def find_invoice_for_period(
    conn: Connection,
    *,
    admission_id: int,
    billing_period: date,
    invoice_kind: str,
) -> Any:
    return conn.execute(
        """
        SELECT *
        FROM msi_v2.invoices
        WHERE admission_id = %s
          AND billing_period = %s
          AND invoice_kind = %s
          AND status <> 'voided'
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(admission_id), billing_period, invoice_kind),
    ).fetchone()


def get_invoice_row(
    conn: Connection,
    invoice_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"SELECT * FROM msi_v2.invoices WHERE id = %s{lock}",
        (int(invoice_id),),
    ).fetchone()


def get_first_invoice_row(
    conn: Connection,
    admission_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT *
        FROM msi_v2.invoices
        WHERE admission_id = %s
          AND invoice_kind = 'first'
          AND status <> 'voided'
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        {lock}
        """,
        (int(admission_id),),
    ).fetchone()


def list_invoice_rows(conn: Connection, admission_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT *
        FROM msi_v2.invoices
        WHERE admission_id = %s
        ORDER BY billing_period DESC, id DESC
        """,
        (int(admission_id),),
    ).fetchall()


def list_invoice_line_rows(conn: Connection, invoice_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT *
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


def get_invoice_payment_row(
    conn: Connection,
    payment_id: int,
    *,
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


def list_scoped_invoice_rows(
    conn: Connection,
    *,
    school_ids: Iterable[int],
    all_schools: bool,
    query: str,
    status: str,
    limit: int,
) -> list[Any]:
    return conn.execute(
        """
        SELECT invoice.*, admission.school_id, school.school_name,
               admission.student_full_name, admission.parent_full_name,
               admission.parent_phone,
               count(*) OVER () AS total_count
        FROM msi_v2.invoices invoice
        JOIN msi_v2.admissions admission ON admission.id = invoice.admission_id
        JOIN msi_v2.schools school ON school.id = admission.school_id
        WHERE (%s OR admission.school_id = ANY(%s))
          AND (%s = 'all' OR invoice.status = %s)
          AND (
              %s = ''
              OR invoice.invoice_number ILIKE %s
              OR admission.student_full_name ILIKE %s
              OR admission.parent_full_name ILIKE %s
              OR admission.parent_phone ILIKE %s
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
        """,
        (
            bool(all_schools),
            list(school_ids),
            status,
            status,
            query,
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            int(limit),
        ),
    ).fetchall()


def has_pending_payme_transaction(conn: Connection, invoice_id: int) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM msi_v2.payme_transactions
        WHERE invoice_id = %s AND state = 1
        LIMIT 1
        """,
        (int(invoice_id),),
    ).fetchone()
    return bool(row)


def insert_manual_payment(
    conn: Connection,
    *,
    invoice_id: int,
    amount_minor: int,
    method: str,
    paid_at: datetime,
    reference: str,
    reason: str,
    staff_id: int | None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoice_payments (
            invoice_id, source, method, amount_minor, currency, status,
            reference, reason, paid_at, recorded_by_staff_id, created_at
        )
        VALUES (
            %s, 'manual', %s, %s, 'UZS', 'completed',
            %s, %s, %s, %s, now()
        )
        RETURNING id
        """,
        (
            int(invoice_id),
            method,
            int(amount_minor),
            reference,
            reason,
            paid_at,
            staff_id,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_payme_payment(
    conn: Connection,
    *,
    invoice_id: int,
    amount_minor: int,
    provider_transaction_id: str,
    paid_at: datetime,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoice_payments (
            invoice_id, source, method, amount_minor, currency, status,
            provider_transaction_id, reference, reason, paid_at, created_at
        )
        VALUES (
            %s, 'payme', 'payme', %s, 'UZS', 'completed',
            %s, %s, 'Confirmed by Payme Merchant API', %s, now()
        )
        ON CONFLICT (source, provider_transaction_id)
            WHERE provider_transaction_id IS NOT NULL
        DO UPDATE SET provider_transaction_id = excluded.provider_transaction_id
        RETURNING id
        """,
        (
            int(invoice_id),
            int(amount_minor),
            provider_transaction_id,
            provider_transaction_id,
            paid_at,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_invoice_paid_amount(
    conn: Connection,
    *,
    invoice_id: int,
    expected_version: int,
    paid_minor: int,
    status: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.invoices
        SET paid_minor = %s,
            status = %s,
            paid_at = CASE WHEN %s = 'paid' THEN COALESCE(paid_at, now()) ELSE NULL END,
            version = version + 1,
            updated_at = now()
        WHERE id = %s AND version = %s
        RETURNING id
        """,
        (
            int(paid_minor),
            status,
            status,
            int(invoice_id),
            int(expected_version),
        ),
    ).fetchone()
    return bool(row)


def reverse_manual_payment(
    conn: Connection,
    *,
    payment_id: int,
    staff_id: int | None,
    reason: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.invoice_payments
        SET status = 'reversed',
            reversed_at = now(),
            reversed_by_staff_id = %s,
            reversal_reason = %s
        WHERE id = %s
          AND source = 'manual'
          AND status = 'completed'
        RETURNING id
        """,
        (staff_id, reason, int(payment_id)),
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
        SET status = 'voided',
            voided_at = now(),
            void_reason = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND version = %s
          AND paid_minor = 0
          AND status IN ('draft', 'issued', 'overdue')
        RETURNING id
        """,
        (reason, int(invoice_id), int(expected_version)),
    ).fetchone()
    return bool(row)


def set_admission_payment_review(
    conn: Connection,
    *,
    admission_id: int,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.admissions
        SET status = CASE
                WHEN service_start_date IS NULL OR service_start_date > CURRENT_DATE
                    THEN 'awaiting_payment'
                ELSE 'payment_review'
            END,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND status NOT IN ('cancelled', 'expired')
        """,
        (int(admission_id),),
    )


def link_invoice_to_people(
    conn: Connection,
    *,
    admission_id: int,
    student_id: int,
    parent_id: int,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.invoices
        SET student_id = %s, parent_id = %s, updated_at = now()
        WHERE admission_id = %s
        """,
        (int(student_id), int(parent_id), int(admission_id)),
    )


def activate_admission(
    conn: Connection,
    *,
    admission_id: int,
    student_id: int,
    parent_id: int,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.admissions
        SET status = 'active',
            activated_student_id = %s,
            activated_parent_id = %s,
            activated_at = COALESCE(activated_at, now()),
            version = version + 1,
            updated_at = now()
        WHERE id = %s
        """,
        (int(student_id), int(parent_id), int(admission_id)),
    )


def get_activation_notification_row(
    conn: Connection,
    *,
    admission_id: int,
    parent_id: int,
) -> Any:
    return conn.execute(
        """
        SELECT admission.student_full_name, admission.preferred_language,
               parent.telegram_user_id
        FROM msi_v2.admissions admission
        JOIN msi_v2.parents parent ON parent.id = %s
        WHERE admission.id = %s
        """,
        (int(parent_id), int(admission_id)),
    ).fetchone()


def cancel_admission(
    conn: Connection,
    *,
    admission_id: int,
    expected_version: int,
    reason: str,
) -> bool:
    row = conn.execute(
        """
        UPDATE msi_v2.admissions
        SET status = 'cancelled',
            cancelled_at = now(),
            cancellation_reason = %s,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
          AND version = %s
          AND status NOT IN ('active', 'cancelled')
        RETURNING id
        """,
        (reason, int(admission_id), int(expected_version)),
    ).fetchone()
    return bool(row)


def insert_audit_event(
    conn: Connection,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int,
    detail: Mapping[str, Any],
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
            staff_id,
            account_id,
            event_type,
            entity_type,
            int(entity_id),
            json.dumps(dict(detail), ensure_ascii=False, default=str),
        ),
    )


def list_due_recurring_admission_rows(conn: Connection, today: date) -> list[Any]:
    return conn.execute(
        """
        SELECT admission.id, admission.billing_day, admission.currency
        FROM msi_v2.admissions admission
        WHERE admission.status = 'active'
          AND admission.billing_day <= LEAST(EXTRACT(DAY FROM %s::date)::int, 28)
          AND (
              admission.service_start_date IS NULL
              OR admission.service_start_date <= %s::date
          )
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.invoices invoice
              WHERE invoice.admission_id = admission.id
                AND invoice.billing_period = date_trunc('month', %s::date)::date
                AND invoice.invoice_kind = 'monthly'
                AND invoice.status <> 'voided'
          )
        ORDER BY admission.id
        FOR UPDATE SKIP LOCKED
        """,
        (today, today, today),
    ).fetchall()


__all__ = [name for name in globals() if not name.startswith("_")]
