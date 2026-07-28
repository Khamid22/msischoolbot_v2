"""Stable admission, contract, invoice, and payment vocabulary."""

from enum import IntEnum, StrEnum

from backend.modules.domains.finance.domain_types import (
    InvoiceKind,
    InvoiceStatus,
    ManualPaymentMethod,
    PaymentSource,
    PaymentStatus,
)


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
