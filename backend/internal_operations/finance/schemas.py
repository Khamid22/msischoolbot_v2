"""Request and response contracts for system-admin payment routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateStudentPaymentRequest(BaseModel):
    subject: str = ""
    currency: str = "UZS"
    paid_amount: float | None = None
    next_payment_amount: float | None = None
    remaining_debt: float | None = None
    amount: float | None = None
    month: str | None = None
    month_label: str | None = None
    status: str | None = None
    due_date: str | None = None
    paid_at: str | None = None
    paid_date: str | None = None
    next_payment_date: str | None = None
    notes: str | None = None


class MarkStudentPaymentRequest(BaseModel):
    paid: bool = True
    paid_at: str | None = None


class StudentPaymentPayload(BaseModel):
    student_row_id: int | None = None
    payment: dict[str, Any] | None = None
    payments: list[dict[str, Any]]
    summary: dict[str, Any]
