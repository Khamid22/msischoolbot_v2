"""Billing lifecycle and money policies."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from backend.core.time import SCHOOL_TIMEZONE
from backend.modules.domains.finance.domain_types import InvoiceStatus, PaymentStatus

UZS_MINOR_FACTOR = 100
PAYMENT_WINDOW_HOURS = 48
TWENTY_FOUR_HOUR_REMINDER = timedelta(hours=24)
SIX_HOUR_REMINDER = timedelta(hours=6)


class BillingError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "billing_error",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def major_to_minor(value: object) -> int:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BillingError("Payment amount must be a number.") from exc
    minor = int((amount * UZS_MINOR_FACTOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if minor <= 0:
        raise BillingError("Payment amount must be greater than zero.")
    return minor


def minor_to_major(value: int) -> float:
    return float(Decimal(int(value)) / UZS_MINOR_FACTOR)


def invoice_status_for_balance(
    *,
    total_minor: int,
    paid_minor: int,
    due_is_past: bool = False,
) -> InvoiceStatus:
    if paid_minor >= total_minor:
        return InvoiceStatus.PAID
    if paid_minor > 0:
        return InvoiceStatus.PARTIALLY_PAID
    return InvoiceStatus.OVERDUE if due_is_past else InvoiceStatus.ISSUED


def ensure_invoice_accepts_payment(status: InvoiceStatus) -> None:
    if status not in {
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    }:
        raise BillingError("This invoice cannot accept a payment.")


def ensure_invoice_can_be_voided(status: InvoiceStatus, paid_minor: int) -> None:
    if status is InvoiceStatus.VOIDED:
        raise BillingError("This invoice is already voided.")
    if paid_minor > 0 or status is InvoiceStatus.PAID:
        raise BillingError("Reverse completed payments before voiding this invoice.")


def ensure_payment_can_be_reversed(status: PaymentStatus) -> None:
    if status is not PaymentStatus.COMPLETED:
        raise BillingError("Only a completed payment can be reversed.")


def enforcement_deadline(*, issued_at: datetime, due_date: date) -> datetime:
    """Give every enforceable invoice a complete 48-hour payment window."""

    normalized_issued_at = issued_at.astimezone(UTC)
    requested_deadline = datetime.combine(
        due_date,
        time(hour=23, minute=59, second=59),
        tzinfo=SCHOOL_TIMEZONE,
    ).astimezone(UTC)
    return max(
        normalized_issued_at + timedelta(hours=PAYMENT_WINDOW_HOURS),
        requested_deadline,
    )


def enforcement_start(deadline_at: datetime) -> datetime:
    return deadline_at.astimezone(UTC) - timedelta(hours=PAYMENT_WINDOW_HOURS)


__all__ = [
    "BillingError",
    "PAYMENT_WINDOW_HOURS",
    "SIX_HOUR_REMINDER",
    "TWENTY_FOUR_HOUR_REMINDER",
    "UZS_MINOR_FACTOR",
    "enforcement_deadline",
    "enforcement_start",
    "ensure_invoice_accepts_payment",
    "ensure_invoice_can_be_voided",
    "ensure_payment_can_be_reversed",
    "invoice_status_for_balance",
    "major_to_minor",
    "minor_to_major",
]
