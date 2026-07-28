"""Stable admission, contract, invoice, and payment vocabulary."""

from enum import IntEnum, StrEnum


class AdmissionStatus(StrEnum):
    DRAFT = "draft"
    CONTRACT_SENT = "contract_sent"
    CONTRACT_SUBMITTED = "contract_submitted"
    AWAITING_PAYMENT = "awaiting_payment"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAYMENT_REVIEW = "payment_review"


class ContractStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


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


class PaymeTransactionState(IntEnum):
    CANCELLED_AFTER_COMPLETION = -2
    CANCELLED = -1
    CREATED = 1
    COMPLETED = 2


class AdmissionJobTopic(StrEnum):
    GENERATE_INVOICES = "admissions.generate_invoices"
    ACTIVATION_COMPLETED = "admissions.activation_completed"


__all__ = [
    "AdmissionJobTopic",
    "AdmissionStatus",
    "ContractStatus",
    "InvoiceKind",
    "InvoiceStatus",
    "ManualPaymentMethod",
    "PaymentSource",
    "PaymentStatus",
    "PaymeTransactionState",
]
