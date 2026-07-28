"""Typed parent API models with camelCase wire aliases."""

from __future__ import annotations

from pydantic import Field

from backend.core.api import ApiModel
from backend.modules.domains.finance.contracts import BillingAccessStatus, PaymentRecord
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketCategory,
    TicketData,
    TicketMessageData,
    TicketStatus,
)


class ParentAcademicIndicatorResponse(ApiModel):
    enrollment_id: int = 0
    subject_name: str = ""
    subject_display_name: str = ""
    subject_short: str = ""
    group_name: str = ""
    aap: float = 0
    attendance_rate: int = 0
    exam_performance: int = 0
    total_coins: int = 0
    completed_lessons: int = 0
    total_lessons: int = 0
    completion_rate: int = 0
    updated_at: str = ""


class ParentLessonResponse(ApiModel):
    date: str = ""
    subject_name: str = ""
    subject_display_name: str = ""
    group_name: str = ""
    lesson_number: str = ""
    topic: str = ""
    attendance_status: str = ""


class ParentPaymentRecordResponse(ApiModel):
    payment_id: int
    invoice_id: int | None = None
    student_row_id: int
    subject: str
    month: str
    amount: float
    currency: str
    status: str
    state: str
    due_date: str
    paid_at: str
    notes: str
    balance: float = 0
    can_pay_online: bool = False

    @classmethod
    def from_record(cls, record: PaymentRecord) -> ParentPaymentRecordResponse:
        return cls(**record.__dict__)


class ParentPaymentSummaryResponse(ApiModel):
    currency: str = "UZS"
    debt_total: float = 0
    due_total: float = 0
    upcoming_total: float = 0
    paid_total: float = 0


class ParentChildResponse(ApiModel):
    student_row_id: int
    student_code: str
    full_name: str
    school_name: str
    class_name: str = ""
    photo_url: str = ""
    subjects: list[str] = Field(default_factory=list)
    academic_indicators: list[ParentAcademicIndicatorResponse] = Field(default_factory=list)
    recent_lessons: list[ParentLessonResponse] = Field(default_factory=list)
    payment_summary: ParentPaymentSummaryResponse = Field(
        default_factory=ParentPaymentSummaryResponse
    )
    dashboard_url: str


class ParentChildrenResponse(ApiModel):
    items: list[ParentChildResponse] = Field(default_factory=list)


class ParentAnnouncementResponse(ApiModel):
    announcement_id: int
    title: str
    body: str
    priority: str
    is_pinned: bool
    published_at: str


class ParentUpdatesResponse(ApiModel):
    items: list[ParentAnnouncementResponse] = Field(default_factory=list)


class ParentPaymentsResponse(ApiModel):
    items: list[ParentPaymentRecordResponse] = Field(default_factory=list)
    summary: ParentPaymentSummaryResponse = Field(
        default_factory=ParentPaymentSummaryResponse
    )


class ParentInvoiceCheckoutResponse(ApiModel):
    checkout_url: str
    merchant_id: str
    invoice_id: int
    amount_minor: int
    currency: str
    callback_url: str


class ParentBillingStatusResponse(BillingAccessStatus):
    pass


class ParentTicketMessageResponse(ApiModel):
    message_id: int
    author_type: str
    author_name: str
    body: str
    created_at: str

    @classmethod
    def from_data(cls, message: TicketMessageData) -> ParentTicketMessageResponse:
        return cls(**message.__dict__)


class ParentTicketResponse(ApiModel):
    ticket_id: int
    parent_id: int
    student_row_id: int
    student_name: str
    student_code: str
    school_id: int
    school_name: str
    category: TicketCategory
    topic: str
    status: TicketStatus
    assigned_staff_id: int | None
    assigned_staff_name: str
    created_at: str
    updated_at: str
    resolved_at: str
    messages: list[ParentTicketMessageResponse] = Field(default_factory=list)

    @classmethod
    def from_data(cls, ticket: TicketData) -> ParentTicketResponse:
        return cls(
            ticket_id=ticket.ticket_id,
            parent_id=ticket.parent_id,
            student_row_id=ticket.student_row_id,
            student_name=ticket.student_name,
            student_code=ticket.student_code,
            school_id=ticket.school_id,
            school_name=ticket.school_name,
            category=ticket.category,
            topic=ticket.topic,
            status=ticket.status,
            assigned_staff_id=ticket.assigned_staff_id,
            assigned_staff_name=ticket.assigned_staff_name,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            resolved_at=ticket.resolved_at,
            messages=[
                ParentTicketMessageResponse.from_data(message)
                for message in ticket.messages
            ],
        )


class ParentTicketsResponse(ApiModel):
    items: list[ParentTicketResponse] = Field(default_factory=list)


class ParentPreferenceResponse(ApiModel):
    parent_id: int
    display_name: str
    preferred_language: str


class ParentOverviewResponse(ApiModel):
    children: list[ParentChildResponse] = Field(default_factory=list)
    latest_updates: list[ParentAnnouncementResponse] = Field(default_factory=list)
    payment_summary: ParentPaymentSummaryResponse = Field(
        default_factory=ParentPaymentSummaryResponse
    )
    open_ticket_count: int = 0
    average_attendance_rate: int | None = None
    average_completion_rate: int | None = None
    preference: ParentPreferenceResponse | None = None


class CreateParentTicketRequest(ApiModel):
    student_row_id: int = Field(gt=0)
    category: TicketCategory = TicketCategory.OTHER
    topic: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=5, max_length=4_000)


class ReplyToParentTicketRequest(ApiModel):
    body: str = Field(min_length=1, max_length=4_000)


class UpdateParentPreferenceRequest(ApiModel):
    preferred_language: str = Field(pattern="^(ru|uz)$")


__all__ = [name for name in globals() if name.endswith(("Request", "Response"))]
