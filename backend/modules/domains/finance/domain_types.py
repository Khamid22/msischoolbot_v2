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


class BillingAccountType(StrEnum):
    STUDENT = "student"
    ADMISSION = "admission"


class BillingScheduleStatus(StrEnum):
    MISSING = "missing"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class BillingAttentionFlag(StrEnum):
    PAYMENT_ONLY = "payment_only"
    OVERDUE = "overdue"
    DUE_WITHOUT_INVOICE = "due_without_invoice"
    MISSING_SCHEDULE = "missing_schedule"
    ENFORCEMENT_MISSING = "enforcement_missing"


class BillingItemStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class BillingJobTopic(StrEnum):
    GENERATE_INVOICES = "finance.generate_invoices"
    ISSUE_BILLING_CYCLE = "finance.issue_billing_cycle"
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


class BillingNotificationDeliveryStatus(StrEnum):
    SCHEDULED = "scheduled"
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BillingAutomationWorkerState(StrEnum):
    HEALTHY = "healthy"
    STALLED = "stalled"
    NOT_STARTED = "not_started"


class BillingHoldTarget(StrEnum):
    DEBTOR_STUDENT = "debtor_student"
    LINKED_PARENT = "linked_parent"
    HOUSEHOLD_STUDENT = "household_student"


class BillingCycleState(StrEnum):
    SCHEDULED = "scheduled"
    REVIEW_REQUIRED = "review_required"
    INVOICED = "invoiced"
    SATISFIED = "satisfied"
    CANCELLED = "cancelled"


class BillingCycleReviewDecision(StrEnum):
    APPLY = "apply"
    EXCLUDE = "exclude"


class BillingCycleReviewStatus(StrEnum):
    ACTIVE = "active"
    REVERSED = "reversed"


__all__ = [
    "BillingAccountType",
    "BillingCycleReviewDecision",
    "BillingCycleReviewStatus",
    "BillingCycleState",
    "BillingAttentionFlag",
    "BillingJobTopic",
    "BillingAccessMode",
    "BillingEnforcementState",
    "BillingHoldTarget",
    "BillingNotificationStage",
    "BillingNotificationDeliveryStatus",
    "BillingAutomationWorkerState",
    "BillingItemStatus",
    "BillingProfileStatus",
    "BillingScheduleStatus",
    "InvoiceKind",
    "InvoiceOrigin",
    "InvoiceStatus",
    "ManualPaymentMethod",
    "PaymentSource",
    "PaymentStatus",
]
