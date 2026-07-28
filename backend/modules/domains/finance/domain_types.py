"""Stable billing, invoice, and settlement vocabulary."""

from enum import StrEnum


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    VOIDED = "voided"


class InvoiceKind(StrEnum):
    FIRST = "first"
    MONTHLY = "monthly"
    MANUAL = "manual"


class InvoiceOrigin(StrEnum):
    ADMISSION = "admission"
    STUDENT_BILLING = "student_billing"
    LEGACY_MIGRATION = "legacy_migration"


class PaymentSource(StrEnum):
    PAYME = "payme"
    MANUAL = "manual"


class ManualPaymentMethod(StrEnum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD_TERMINAL = "card_terminal"
    OTHER = "other"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"
    REVERSED = "reversed"


class BillingProfileStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class BillingJobTopic(StrEnum):
    GENERATE_INVOICES = "finance.generate_invoices"
    RECONCILE_LEGACY_PAYMENTS = "finance.reconcile_legacy_payments"


__all__ = [
    "BillingJobTopic",
    "BillingProfileStatus",
    "InvoiceKind",
    "InvoiceOrigin",
    "InvoiceStatus",
    "ManualPaymentMethod",
    "PaymentSource",
    "PaymentStatus",
]
