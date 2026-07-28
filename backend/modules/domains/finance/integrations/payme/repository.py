"""PostgreSQL persistence for Payme Merchant API."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from backend.core.unit_of_work import Connection


def get_payable_invoice_row(
    conn: Connection,
    invoice_id: int,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE OF invoice, admission" if for_update else ""
    return conn.execute(
        f"""
        SELECT invoice.*, admission.status AS admission_status,
               admission.school_id, admission.service_start_date,
               contract.status AS contract_status,
               COALESCE(group_state.selected_count, 0) AS selected_group_count,
               COALESCE(group_state.available_count, 0) AS available_group_count
        FROM msi_v2.invoices invoice
        JOIN msi_v2.admissions admission ON admission.id = invoice.admission_id
        LEFT JOIN LATERAL (
            SELECT current_contract.status
            FROM msi_v2.admission_contracts current_contract
            WHERE current_contract.admission_id = admission.id
              AND current_contract.superseded_at IS NULL
            ORDER BY current_contract.version DESC
            LIMIT 1
        ) contract ON true
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) AS selected_count,
                COUNT(*) FILTER (
                    WHERE group_row.status = 'active'
                      AND group_row.school_id = admission.school_id
                      AND subject.status = 'active'
                ) AS available_count
            FROM msi_v2.admission_group_selections selection
            JOIN msi_v2.groups group_row ON group_row.id = selection.group_id
            JOIN msi_v2.subjects subject ON subject.id = selection.subject_id
            WHERE selection.admission_id = admission.id
        ) group_state ON true
        WHERE invoice.id = %s
        {lock}
        """,
        (int(invoice_id),),
    ).fetchone()


def get_transaction_row(
    conn: Connection,
    provider_transaction_id: str,
    *,
    for_update: bool = False,
) -> Any:
    lock = " FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT *
        FROM msi_v2.payme_transactions
        WHERE provider_transaction_id = %s
        {lock}
        """,
        (provider_transaction_id,),
    ).fetchone()


def find_pending_invoice_transaction_row(
    conn: Connection,
    invoice_id: int,
) -> Any:
    return conn.execute(
        """
        SELECT *
        FROM msi_v2.payme_transactions
        WHERE invoice_id = %s AND state = 1
        ORDER BY id
        LIMIT 1
        """,
        (int(invoice_id),),
    ).fetchone()


def insert_transaction(
    conn: Connection,
    *,
    provider_transaction_id: str,
    invoice_id: int,
    provider_created_at_ms: int,
    amount_minor: int,
    create_time_ms: int,
) -> Any:
    return conn.execute(
        """
        INSERT INTO msi_v2.payme_transactions (
            provider_transaction_id, invoice_id, provider_created_at_ms,
            amount_minor, state, reason, create_time_ms,
            perform_time_ms, cancel_time_ms, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 1, NULL, %s, 0, 0, now(), now())
        ON CONFLICT (provider_transaction_id) DO NOTHING
        RETURNING *
        """,
        (
            provider_transaction_id,
            int(invoice_id),
            int(provider_created_at_ms),
            int(amount_minor),
            int(create_time_ms),
        ),
    ).fetchone()


def perform_transaction(
    conn: Connection,
    *,
    provider_transaction_id: str,
    perform_time_ms: int,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.payme_transactions
        SET state = 2, perform_time_ms = %s, updated_at = now()
        WHERE provider_transaction_id = %s AND state = 1
        RETURNING *
        """,
        (int(perform_time_ms), provider_transaction_id),
    ).fetchone()


def cancel_transaction(
    conn: Connection,
    *,
    provider_transaction_id: str,
    state: int,
    reason: int,
    cancel_time_ms: int,
) -> Any:
    return conn.execute(
        """
        UPDATE msi_v2.payme_transactions
        SET state = %s, reason = %s, cancel_time_ms = %s, updated_at = now()
        WHERE provider_transaction_id = %s AND state IN (1, 2)
        RETURNING *
        """,
        (
            int(state),
            int(reason),
            int(cancel_time_ms),
            provider_transaction_id,
        ),
    ).fetchone()


def insert_completed_invoice_payment(
    conn: Connection,
    *,
    invoice_id: int,
    amount_minor: int,
    provider_transaction_id: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.invoice_payments (
            invoice_id, source, method, amount_minor, currency, status,
            provider_transaction_id, reference, reason, paid_at, created_at
        )
        VALUES (
            %s, 'payme', 'payme', %s, 'UZS', 'completed',
            %s, %s, 'Confirmed by Payme Merchant API', now(), now()
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
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def set_invoice_paid(
    conn: Connection,
    *,
    invoice_id: int,
    amount_minor: int,
) -> None:
    conn.execute(
        """
        UPDATE msi_v2.invoices
        SET paid_minor = paid_minor + %s,
            status = CASE
                WHEN paid_minor + %s >= total_minor THEN 'paid'
                ELSE 'partially_paid'
            END,
            paid_at = CASE
                WHEN paid_minor + %s >= total_minor THEN COALESCE(paid_at, now())
                ELSE paid_at
            END,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
        """,
        (
            int(amount_minor),
            int(amount_minor),
            int(amount_minor),
            int(invoice_id),
        ),
    )


def refund_invoice_payment(
    conn: Connection,
    *,
    provider_transaction_id: str,
    reason: int,
) -> int:
    row = conn.execute(
        """
        UPDATE msi_v2.invoice_payments
        SET status = 'refunded',
            reversed_at = now(),
            reversal_reason = %s
        WHERE source = 'payme'
          AND provider_transaction_id = %s
          AND status = 'completed'
        RETURNING invoice_id, amount_minor
        """,
        (f"Payme cancellation reason {int(reason)}", provider_transaction_id),
    ).fetchone()
    if not row:
        return 0
    conn.execute(
        """
        UPDATE msi_v2.invoices
        SET paid_minor = GREATEST(0, paid_minor - %s),
            status = CASE
                WHEN GREATEST(0, paid_minor - %s) = 0 THEN 'issued'
                ELSE 'partially_paid'
            END,
            paid_at = NULL,
            version = version + 1,
            updated_at = now()
        WHERE id = %s
        """,
        (
            int(row["amount_minor"]),
            int(row["amount_minor"]),
            int(row["invoice_id"]),
        ),
    )
    return int(row["invoice_id"])


def set_admission_after_refund(
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


def list_statement_rows(
    conn: Connection,
    *,
    from_ms: int,
    to_ms: int,
) -> list[Any]:
    return conn.execute(
        """
        SELECT transaction.*, invoice.invoice_number
        FROM msi_v2.payme_transactions transaction
        JOIN msi_v2.invoices invoice ON invoice.id = transaction.invoice_id
        WHERE transaction.provider_created_at_ms BETWEEN %s AND %s
        ORDER BY transaction.provider_created_at_ms, transaction.id
        """,
        (int(from_ms), int(to_ms)),
    ).fetchall()


def insert_payme_audit_event(
    conn: Connection,
    *,
    event_type: str,
    transaction_id: int,
    detail: Mapping[str, Any],
) -> None:
    """Record a provider transition without exposing credentials."""
    conn.execute(
        """
        INSERT INTO msi_v2.audit_events (
            actor_staff_id, actor_account_id, event_type,
            entity_type, entity_id, detail_json, created_at
        )
        VALUES (NULL, NULL, %s, 'payme_transaction', %s, %s::jsonb, now())
        """,
        (
            event_type,
            int(transaction_id),
            json.dumps(dict(detail), ensure_ascii=False, default=str),
        ),
    )


__all__ = [
    "cancel_transaction",
    "find_pending_invoice_transaction_row",
    "get_payable_invoice_row",
    "get_transaction_row",
    "insert_completed_invoice_payment",
    "insert_payme_audit_event",
    "insert_transaction",
    "list_statement_rows",
    "perform_transaction",
    "refund_invoice_payment",
    "set_admission_after_refund",
    "set_invoice_paid",
]
