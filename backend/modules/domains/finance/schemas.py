"""Typed commands and results for the canonical student billing ledger."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, field_validator

from backend.core.api import ApiModel
from backend.modules.domains.finance.domain_types import (
    BillingProfileStatus,
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


class InvoiceSummary(BillingModel):
    invoice_id: int
    invoice_number: str
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
    version: int


class InvoiceDetail(InvoiceSummary):
    lines: list[InvoiceLineResult] = Field(default_factory=list)
    payments: list[InvoicePaymentResult] = Field(default_factory=list)
    void_reason: str = ""


class InvoicePage(BillingModel):
    items: list[InvoiceSummary] = Field(default_factory=list)
    total: int = 0


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


__all__ = [
    "AddPaidStudentInvoiceCommand",
    "BillingItemInput",
    "BillingProfileItemResult",
    "BillingProfileResult",
    "ConfigureBillingProfileCommand",
    "InvoiceDetail",
    "InvoiceLineResult",
    "InvoicePage",
    "InvoicePaymentResult",
    "InvoiceSummary",
    "IssueStudentInvoiceCommand",
    "RecordManualInvoicePaymentCommand",
    "ReverseInvoicePaymentCommand",
    "VoidStudentInvoiceCommand",
]
