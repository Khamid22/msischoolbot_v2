"""Typed commands and results for the canonical student billing ledger."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, field_validator

from backend.core.api import ApiModel
from backend.modules.domains.finance.domain_types import (
    BillingAccessMode,
    BillingAccountType,
    BillingAttentionFlag,
    BillingAutomationWorkerState,
    BillingCycleReviewDecision,
    BillingCycleReviewStatus,
    BillingCycleState,
    BillingEnforcementState,
    BillingHoldTarget,
    BillingItemStatus,
    BillingNotificationDeliveryStatus,
    BillingNotificationStage,
    BillingProfileStatus,
    BillingScheduleStatus,
    InvoiceKind,
    InvoiceOrigin,
    InvoiceStatus,
    ManualPaymentMethod,
    PaymentSource,
    PaymentStatus,
)


class BillingModel(ApiModel):
    model_config = ApiModel.model_config | {"extra": "forbid"}


class InvoiceLineResult(BillingModel):
    line_id: int
    group_id: int | None = None
    subject_id: int | None = None
    description: str
    amount_minor: int


class InvoicePaymentResult(BillingModel):
    payment_id: int
    source: PaymentSource
    method: str
    amount_minor: int
    currency: str
    status: PaymentStatus
    reference: str
    reason: str
    paid_at: datetime
    reversed_at: datetime | None = None
    reversal_reason: str = ""


class BillingNotificationTimelineEntry(BillingModel):
    stage: BillingNotificationStage
    scheduled_for: datetime
    status: BillingNotificationDeliveryStatus
    recipient_count: int = Field(default=0, ge=0)
    pending_count: int = Field(default=0, ge=0)
    sent_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)


class InvoiceSummary(BillingModel):
    invoice_id: int
    invoice_number: str
    billing_cycle_id: int | None = None
    admission_id: int | None = None
    student_id: int | None = None
    student_row_id: int | None = None
    student_name: str
    student_code: str
    parent_name: str = ""
    school_id: int
    school_name: str
    invoice_kind: InvoiceKind
    origin: InvoiceOrigin
    billing_period: date
    currency: str
    total_minor: int
    paid_minor: int
    balance_minor: int
    status: InvoiceStatus
    due_date: date
    issued_at: datetime | None = None
    paid_at: datetime | None = None
    enforcement_state: BillingEnforcementState | None = None
    countdown_started_at: datetime | None = None
    payment_deadline_at: datetime | None = None
    version: int


class InvoiceDetail(InvoiceSummary):
    lines: list[InvoiceLineResult] = Field(default_factory=list)
    payments: list[InvoicePaymentResult] = Field(default_factory=list)
    notification_timeline: list[BillingNotificationTimelineEntry] = Field(default_factory=list)
    void_reason: str = ""
    billing_cycle: "BillingCycleSummary | None" = None


class InvoicePage(BillingModel):
    items: list[InvoiceSummary] = Field(default_factory=list)
    total: int = 0
    next_cursor: str | None = None


class CurrencyBalance(BillingModel):
    currency: str
    balance_minor: int


class BillingAccountLatestInvoice(BillingModel):
    invoice_id: int
    invoice_number: str
    billing_period: date
    status: InvoiceStatus
    due_date: date


class BillingAccountSummary(BillingModel):
    account_type: BillingAccountType
    account_id: int
    student_id: int | None = None
    admission_id: int | None = None
    student_name: str
    student_code: str = ""
    parent_name: str = ""
    school_id: int
    school_name: str
    lifecycle_status: str
    schedule_status: BillingScheduleStatus
    billing_day: int | None = None
    effective_date: date | None = None
    currency: str
    monthly_amount_minor: int = 0
    billable_item_count: int = 0
    latest_invoice: BillingAccountLatestInvoice | None = None
    open_invoice_count: int = 0
    overdue_invoice_count: int = 0
    outstanding_balances: list[CurrencyBalance] = Field(default_factory=list)
    enforcement_state: BillingEnforcementState | None = None
    attention_flags: list[BillingAttentionFlag] = Field(default_factory=list)
    schedule_version: int | None = None


class BillingAccountScheduleItem(BillingModel):
    group_id: int
    group_name: str
    subject_id: int
    subject_name: str
    description: str
    amount_minor: int


class BillingEnrollmentOption(BillingModel):
    group_id: int
    group_name: str
    subject_id: int
    subject_name: str


class BillingAccountDetail(BillingAccountSummary):
    schedule_items: list[BillingAccountScheduleItem] = Field(default_factory=list)
    enrollment_options: list[BillingEnrollmentOption] = Field(default_factory=list)
    invoices: list[InvoiceSummary] = Field(default_factory=list)
    linked_telegram_recipients: int = 0
    unlinked_telegram_recipients: int = 0
    billing_cycles: list["BillingCycleSummary"] = Field(default_factory=list)


class BillingAccountPage(BillingModel):
    items: list[BillingAccountSummary] = Field(default_factory=list)
    total: int = 0
    next_cursor: str | None = None


class IssueStudentInvoiceCommand(BillingModel):
    student_id: int = Field(gt=0)
    subject_id: int = Field(gt=0)
    description: str = Field(min_length=2, max_length=200)
    amount_minor: int = Field(gt=0)
    due_date: date
    billing_period: date
    invoice_kind: InvoiceKind = InvoiceKind.MANUAL
    expected_student_version: int = Field(gt=0)


class AddPaidStudentInvoiceCommand(IssueStudentInvoiceCommand):
    method: ManualPaymentMethod
    paid_at: datetime
    reference: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)
    billing_treatment: BillingCycleReviewDecision | None = None
    billing_cycle_id: int | None = Field(default=None, gt=0)
    expected_cycle_version: int | None = Field(default=None, gt=0)

    @field_validator("paid_at")
    @classmethod
    def validate_paid_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Paid date must include a timezone.")
        return value


class RecordManualInvoicePaymentCommand(BillingModel):
    amount_minor: int = Field(gt=0)
    method: ManualPaymentMethod
    paid_at: datetime
    reference: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)
    expected_version: int = Field(gt=0)

    @field_validator("paid_at")
    @classmethod
    def validate_paid_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Paid date must include a timezone.")
        return value


class ReverseInvoicePaymentCommand(BillingModel):
    expected_invoice_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class VoidStudentInvoiceCommand(BillingModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class BillingItemInput(BillingModel):
    group_id: int = Field(gt=0)
    amount_minor: int = Field(gt=0)
    description: str = Field(default="", max_length=200)


class ConfigureBillingProfileCommand(BillingModel):
    student_id: int = Field(gt=0)
    billing_day: int = Field(ge=1, le=28)
    starts_on: date
    status: BillingProfileStatus = BillingProfileStatus.ACTIVE
    items: list[BillingItemInput] = Field(min_length=1, max_length=20)
    expected_version: int | None = Field(default=None, gt=0)


class BillingProfileItemResult(BillingModel):
    item_id: int
    group_id: int
    group_name: str
    subject_id: int
    subject_name: str
    description: str
    amount_minor: int
    active_from: date
    active_until: date | None = None
    status: BillingItemStatus = BillingItemStatus.ACTIVE
    cancelled_at: datetime | None = None
    cancellation_reason: str = ""


class BillingProfileResult(BillingModel):
    profile_id: int
    student_id: int
    school_id: int
    billing_parent_id: int | None = None
    billing_day: int
    currency: str
    starts_on: date
    ends_on: date | None = None
    status: BillingProfileStatus
    version: int
    items: list[BillingProfileItemResult] = Field(default_factory=list)


class BillingCycleItemResult(BillingModel):
    cycle_item_id: int
    group_id: int | None = None
    subject_id: int | None = None
    description: str
    amount_minor: int


class BillingCycleReviewResult(BillingModel):
    review_id: int
    cycle_id: int
    invoice_id: int
    invoice_number: str
    decision: BillingCycleReviewDecision
    allocated_minor: int
    status: BillingCycleReviewStatus
    reason: str
    reviewed_at: datetime
    reversed_at: datetime | None = None
    reversal_reason: str = ""
    version: int


class BillingCycleInvoiceCandidate(BillingModel):
    invoice_id: int
    invoice_number: str
    total_minor: int
    completed_minor: int
    available_minor: int
    currency: str
    origin: InvoiceOrigin
    status: InvoiceStatus
    paid_at: datetime | None = None


class BillingCycleSummary(BillingModel):
    cycle_id: int
    profile_id: int
    student_id: int
    student_row_id: int | None = None
    student_name: str
    student_code: str
    school_id: int
    school_name: str
    billing_period: date
    deadline_at: datetime
    issue_at: datetime
    currency: str
    expected_minor: int
    allocated_minor: int
    remaining_minor: int
    state: BillingCycleState
    invoice_id: int | None = None
    invoice_number: str = ""
    version: int
    is_preview: bool = False
    items: list[BillingCycleItemResult] = Field(default_factory=list)
    reviews: list[BillingCycleReviewResult] = Field(default_factory=list)
    review_candidates: list[BillingCycleInvoiceCandidate] = Field(default_factory=list)


class BillingCycleReadiness(BillingModel):
    generated_at: datetime
    effective_school_ids: list[int] = Field(default_factory=list)
    scheduled_cycles: int = 0
    review_required_cycles: int = 0
    ready_to_issue_cycles: int = 0
    satisfied_cycles: int = 0
    potential_hold_count: int = 0
    linked_telegram_recipients: int = 0
    unlinked_telegram_recipients: int = 0
    cycles: list[BillingCycleSummary] = Field(default_factory=list)


class ReviewBillingCycleInvoiceCommand(BillingModel):
    cycle_id: int = Field(gt=0)
    invoice_id: int = Field(gt=0)
    decision: BillingCycleReviewDecision
    allocated_minor: int = Field(default=0, ge=0)
    reason: str = Field(min_length=2, max_length=1000)
    expected_cycle_version: int = Field(gt=0)

    @field_validator("allocated_minor")
    @classmethod
    def validate_allocation(cls, value: int, info):
        decision = info.data.get("decision")
        if decision is BillingCycleReviewDecision.APPLY and value <= 0:
            raise ValueError("Applied reviews require a positive amount.")
        if decision is BillingCycleReviewDecision.EXCLUDE and value != 0:
            raise ValueError("Excluded reviews cannot allocate an amount.")
        return value


class ReverseBillingCycleReviewCommand(BillingModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class BillingAccessInvoice(BillingModel):
    invoice_id: int
    invoice_number: str
    student_id: int
    student_row_id: int | None = None
    student_name: str
    student_code: str
    total_minor: int
    paid_minor: int
    balance_minor: int
    currency: str
    deadline_at: datetime
    target_type: BillingHoldTarget | None = None
    can_view_invoice: bool
    can_pay_online: bool


class BillingAccessStudent(BillingModel):
    student_id: int
    student_name: str
    student_code: str
    target_type: BillingHoldTarget


class BillingAccessStatus(BillingModel):
    mode: BillingAccessMode = BillingAccessMode.NORMAL
    countdown_deadline_at: datetime | None = None
    remaining_seconds: int = Field(default=0, ge=0)
    blocking_invoice_count: int = Field(default=0, ge=0)
    invoices: list[BillingAccessInvoice] = Field(default_factory=list)
    affected_students: list[BillingAccessStudent] = Field(default_factory=list)


class BillingAutomationStatus(BillingModel):
    generated_at: datetime
    effective_school_ids: list[int] = Field(default_factory=list)
    all_schools: bool = False
    active_billing_profiles: int = Field(default=0, ge=0)
    currently_due_billing_profiles: int = Field(default=0, ge=0)
    open_invoices: int = Field(default=0, ge=0)
    open_invoices_without_enforcement: int = Field(default=0, ge=0)
    linked_telegram_recipients: int = Field(default=0, ge=0)
    unlinked_telegram_recipients: int = Field(default=0, ge=0)
    pending_notification_deliveries: int = Field(default=0, ge=0)
    failed_notification_deliveries: int = Field(default=0, ge=0)
    active_payment_only_holds: int = Field(default=0, ge=0)
    pending_finance_jobs: int = Field(default=0, ge=0)
    worker_state: BillingAutomationWorkerState
    last_successful_finance_worker_at: datetime | None = None


__all__ = [
    "AddPaidStudentInvoiceCommand",
    "BillingAccountDetail",
    "BillingAccountLatestInvoice",
    "BillingAccountPage",
    "BillingAccountScheduleItem",
    "BillingAccountSummary",
    "BillingItemInput",
    "BillingAccessInvoice",
    "BillingAccessStatus",
    "BillingAccessStudent",
    "BillingAutomationStatus",
    "BillingCycleInvoiceCandidate",
    "BillingCycleItemResult",
    "BillingCycleReadiness",
    "BillingCycleReviewResult",
    "BillingCycleSummary",
    "BillingEnrollmentOption",
    "BillingNotificationTimelineEntry",
    "BillingProfileItemResult",
    "BillingProfileResult",
    "ConfigureBillingProfileCommand",
    "CurrencyBalance",
    "InvoiceDetail",
    "InvoiceLineResult",
    "InvoicePage",
    "InvoicePaymentResult",
    "InvoiceSummary",
    "IssueStudentInvoiceCommand",
    "RecordManualInvoicePaymentCommand",
    "ReviewBillingCycleInvoiceCommand",
    "ReverseBillingCycleReviewCommand",
    "ReverseInvoicePaymentCommand",
    "VoidStudentInvoiceCommand",
]
