"""Typed, transaction-bound read contract for parent payment views."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import repository
from backend.modules.domains.finance.service import payment_row_to_record


@dataclass(frozen=True)
class PaymentRecord:
    payment_id: int
    student_row_id: int
    subject: str
    month: str
    amount: float
    currency: str
    status: str
    state: str
    due_date: str
    paid_at: str
    notes: str


def list_payment_records(
    conn: Connection,
    *,
    student_row_id: int,
) -> tuple[PaymentRecord, ...]:
    records = []
    for row in repository.list_student_payment_rows(conn, student_row_id):
        item = payment_row_to_record(row)
        records.append(
            PaymentRecord(
                payment_id=int(item["id"]),
                student_row_id=int(item["student_row_id"]),
                subject=str(item["subject"]),
                month=str(item["month"]),
                amount=float(item["amount"]),
                currency=str(item["currency"]),
                status=str(item["status"]),
                state=str(item["state"]),
                due_date=str(item["due_date"]),
                paid_at=str(item["paid_at"]),
                notes=str(item["notes"]),
            )
        )
    return tuple(records)


__all__ = ["PaymentRecord", "list_payment_records"]
