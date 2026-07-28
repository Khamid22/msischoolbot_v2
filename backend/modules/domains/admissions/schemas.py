"""Typed admission domain commands and read models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.core.api import ApiModel
from backend.modules.domains.admissions.domain_types import (
    AdmissionStatus,
    ContractStatus,
    InvoiceKind,
    InvoiceStatus,
    ManualPaymentMethod,
    PaymentSource,
    PaymentStatus,
)


class AdmissionDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdmissionGroupInput(ApiModel):
    group_id: int = Field(gt=0)
    monthly_amount_minor: int = Field(gt=0)


class CreateAdmissionCommand(ApiModel):
    school_id: int = Field(gt=0)
    student_full_name: str = Field(min_length=2, max_length=180)
    student_phone: str = Field(default="", max_length=80)
    parent_full_name: str = Field(min_length=2, max_length=180)
    parent_phone: str = Field(min_length=5, max_length=80)
    parent_telegram_username: str = Field(default="", max_length=80)
    preferred_language: str = Field(default="uz", pattern="^(uz|ru)$")
    service_start_date: date | None = None
    first_due_date: date
    billing_day: int = Field(ge=1, le=28)
    groups: list[AdmissionGroupInput] = Field(min_length=1, max_length=20)


class UpdateAdmissionCommand(ApiModel):
    student_full_name: str = Field(min_length=2, max_length=180)
    student_phone: str = Field(default="", max_length=80)
    parent_full_name: str = Field(min_length=2, max_length=180)
    parent_phone: str = Field(min_length=5, max_length=80)
    parent_telegram_username: str = Field(default="", max_length=80)
    preferred_language: str = Field(default="uz", pattern="^(uz|ru)$")
    service_start_date: date | None = None
    first_due_date: date
    billing_day: int = Field(ge=1, le=28)
    expected_version: int = Field(gt=0)


class AdmissionGroup(ApiModel):
    group_id: int
    group_name: str
    subject_id: int
    subject_name: str
    monthly_amount_minor: int


class AdmissionContract(ApiModel):
    contract_id: int
    version: int
    status: ContractStatus
    original_file_name: str
    original_mime_type: str
    original_size_bytes: int
    signed_file_name: str = ""
    signed_mime_type: str = ""
    signed_size_bytes: int | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str = ""


class AdmissionAuditEvent(ApiModel):
    event_id: int
    event_type: str
    entity_type: str
    entity_id: int
    detail_summary: str
    actor_staff_id: int | None = None
    created_at: datetime


class InvoiceLine(ApiModel):
    line_id: int
    group_id: int | None = None
    subject_id: int | None = None
    description: str
    amount_minor: int


class InvoicePayment(ApiModel):
    payment_id: int
    source: PaymentSource
    method: str
    amount_minor: int
    currency: str
    status: PaymentStatus
    reference: str
    reason: str
    paid_at: datetime


class Invoice(ApiModel):
    invoice_id: int
    invoice_number: str
    invoice_kind: InvoiceKind
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
    lines: list[InvoiceLine] = Field(default_factory=list)
    payments: list[InvoicePayment] = Field(default_factory=list)


class AdmissionSummary(ApiModel):
    admission_id: int
    school_id: int
    school_name: str
    student_full_name: str
    parent_full_name: str
    parent_phone: str
    status: AdmissionStatus
    contract_status: ContractStatus | None = None
    first_invoice_status: InvoiceStatus | None = None
    first_due_date: date
    updated_at: datetime


class AdmissionDetail(ApiModel):
    admission_id: int
    school_id: int
    school_name: str
    student_full_name: str
    student_phone: str
    parent_full_name: str
    parent_phone: str
    parent_telegram_username: str
    preferred_language: str
    service_start_date: date | None = None
    first_due_date: date
    billing_day: int
    currency: str
    status: AdmissionStatus
    version: int
    activated_student_id: int | None = None
    activated_parent_id: int | None = None
    activated_at: datetime | None = None
    cancellation_reason: str = ""
    groups: list[AdmissionGroup] = Field(default_factory=list)
    contract: AdmissionContract | None = None
    invoices: list[Invoice] = Field(default_factory=list)
    audit_events: list[AdmissionAuditEvent] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdmissionPage(ApiModel):
    items: list[AdmissionSummary] = Field(default_factory=list)
    total: int = 0


class InvoiceQueueItem(ApiModel):
    invoice_id: int
    invoice_number: str
    admission_id: int
    school_id: int
    school_name: str
    student_full_name: str
    parent_full_name: str
    parent_phone: str
    invoice_kind: InvoiceKind
    currency: str
    total_minor: int
    paid_minor: int
    balance_minor: int
    status: InvoiceStatus
    due_date: date
    issued_at: datetime | None = None
    paid_at: datetime | None = None
    version: int


class InvoiceQueuePage(ApiModel):
    items: list[InvoiceQueueItem] = Field(default_factory=list)
    total: int = 0


class AdmissionAccess(ApiModel):
    admission: AdmissionDetail
    access_token: str
    expires_at: datetime


class AdmissionLink(ApiModel):
    access_token: str
    expires_at: datetime


class PrivateDocumentReference(AdmissionDomainModel):
    object_key: str
    original_file_name: str


class AdmissionGroupOption(ApiModel):
    group_id: int
    school_id: int
    school_name: str
    group_name: str
    subject_id: int
    subject_name: str


class ContractUploadMetadata(AdmissionDomainModel):
    object_key: str
    original_file_name: str
    mime_type: str
    size_bytes: int


class ManualPaymentCommand(ApiModel):
    amount_minor: int = Field(gt=0)
    method: ManualPaymentMethod
    paid_at: datetime
    reference: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)
    expected_version: int = Field(gt=0)


class AddPaidInvoiceCommand(ApiModel):
    due_date: date
    billing_period: date
    method: ManualPaymentMethod
    paid_at: datetime
    reference: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)


class CreateInvoiceCommand(ApiModel):
    due_date: date
    billing_period: date
    invoice_kind: InvoiceKind = InvoiceKind.FIRST


class ReviewContractCommand(ApiModel):
    accepted: bool
    reason: str = Field(default="", max_length=1000)


class CancelAdmissionCommand(ApiModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class VoidInvoiceCommand(ApiModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class ReverseManualPaymentCommand(ApiModel):
    expected_invoice_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class PublicAdmission(ApiModel):
    admission_id: int
    student_full_name: str
    school_name: str
    preferred_language: str
    status: AdmissionStatus
    contract: AdmissionContract | None = None
    invoice: Invoice | None = None
    payme_is_available: bool = False
    checkout_url: str = ""
    merchant_id: str = ""
    callback_url: str = ""


__all__ = [
    "AdmissionAccess",
    "AdmissionAuditEvent",
    "AdmissionContract",
    "AdmissionDetail",
    "AdmissionDomainModel",
    "AdmissionGroup",
    "AdmissionGroupInput",
    "AdmissionGroupOption",
    "AdmissionLink",
    "AdmissionPage",
    "AdmissionSummary",
    "AddPaidInvoiceCommand",
    "CancelAdmissionCommand",
    "ContractUploadMetadata",
    "CreateAdmissionCommand",
    "CreateInvoiceCommand",
    "UpdateAdmissionCommand",
    "Invoice",
    "InvoiceLine",
    "InvoicePayment",
    "InvoiceQueueItem",
    "InvoiceQueuePage",
    "ManualPaymentCommand",
    "PublicAdmission",
    "PrivateDocumentReference",
    "ReviewContractCommand",
    "ReverseManualPaymentCommand",
    "VoidInvoiceCommand",
]
