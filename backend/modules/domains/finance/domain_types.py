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
    BOOTSTRAP_ENFORCEMENT = "finance.bootstrap_billing_enforcement"
    PROCESS_ENFORCEMENT_STAGE = "finance.process_billing_enforcement_stage"
    SEND_BILLING_NOTIFICATION = "finance.send_billing_notification"
    RECONCILE_ENFORCEMENT = "finance.reconcile_billing_enforcement"


class BillingEnforcementState(StrEnum):
    SCHEDULED = "scheduled"
    COUNTDOWN = "countdown"
    HELD = "held"
    CLEARED = "cleared"
    CANCELLED = "cancelled"


class BillingAccessMode(StrEnum):
    NORMAL = "normal"
    PAYMENT_ONLY = "payment_only"


class BillingNotificationStage(StrEnum):
    INITIAL = "initial"
    TWENTY_FOUR_HOURS = "twenty_four_hours"
    SIX_HOURS = "six_hours"
    HELD = "held"
    RESTORED = "restored"


class BillingHoldTarget(StrEnum):
    DEBTOR_STUDENT = "debtor_student"
    LINKED_PARENT = "linked_parent"
    HOUSEHOLD_STUDENT = "household_student"


__all__ = [
    "BillingJobTopic",
    "BillingAccessMode",
    "BillingEnforcementState",
    "BillingHoldTarget",
    "BillingNotificationStage",
    "BillingProfileStatus",
    "InvoiceKind",
    "InvoiceOrigin",
    "InvoiceStatus",
    "ManualPaymentMethod",
    "PaymentSource",
    "PaymentStatus",
]
