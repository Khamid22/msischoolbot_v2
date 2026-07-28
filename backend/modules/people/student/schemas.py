"""Student API v1 schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.core.api import ApiModel
from backend.modules.domains.finance.contracts import PaymentRecord
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketData,
    TicketMessageData,
)


class SendChatMessageRequest(BaseModel):
    room: str = "global"
    body: str = ""


class EditChatMessageRequest(BaseModel):
    body: str = ""


class ChatMessageList(BaseModel):
    messages: list[dict[str, Any]]
    room: str


class ChatMessageSent(BaseModel):
    message: dict[str, Any]


class ChatMessageEdited(BaseModel):
    id: int
    body: str
    editedAt: str


class ChatMessageDeleted(BaseModel):
    deleted: bool
    id: int


class CreateBookingRequest(BaseModel):
    availability_id: int
    student_note: str = ""
    student_topic_request: str = ""


class CancelBookingRequest(BaseModel):
    status: str


class BookingCreated(BaseModel):
    booking_id: int


class AvailabilityList(BaseModel):
    availabilities: list[dict[str, Any]]


class BookingList(BaseModel):
    bookings: list[dict[str, Any]]


class PostCommentRequest(BaseModel):
    body: str = ""


class CommentList(BaseModel):
    comments: list[dict[str, Any]]


class CommentPosted(BaseModel):
    comment: dict[str, Any]


class StudentPaymentResponse(ApiModel):
    payment_id: int
    invoice_id: int | None = None
    subject: str
    month: str
    amount: float
    currency: str
    status: str
    state: str
    due_date: str
    paid_at: str
    notes: str
    balance: float
    can_pay_online: bool

    @classmethod
    def from_record(cls, record: PaymentRecord) -> StudentPaymentResponse:
        return cls(
            payment_id=record.payment_id,
            invoice_id=record.invoice_id,
            subject=record.subject,
            month=record.month,
            amount=record.amount,
            currency=record.currency,
            status=record.status,
            state=record.state,
            due_date=record.due_date,
            paid_at=record.paid_at,
            notes=record.notes,
            balance=record.balance,
            can_pay_online=record.can_pay_online,
        )


class StudentPaymentsResponse(ApiModel):
    items: list[StudentPaymentResponse]


class StudentInvoiceCheckoutResponse(ApiModel):
    checkout_url: str
    merchant_id: str
    invoice_id: int
    amount_minor: int
    currency: str
    callback_url: str


class CreateStudentTicketRequest(ApiModel):
    topic: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=5, max_length=4_000)
    category: str = Field(default="payment", max_length=40)


class ReplyToStudentTicketRequest(ApiModel):
    body: str = Field(min_length=1, max_length=4_000)


class StudentTicketMessageResponse(ApiModel):
    message_id: int
    author_type: str
    author_name: str
    body: str
    created_at: str

    @classmethod
    def from_data(cls, message: TicketMessageData) -> StudentTicketMessageResponse:
        return cls(**message.__dict__)


class StudentTicketResponse(ApiModel):
    ticket_id: int
    student_id: int | None
    student_name: str
    student_code: str
    school_name: str
    category: str
    topic: str
    status: str
    created_at: str
    updated_at: str
    resolved_at: str
    messages: list[StudentTicketMessageResponse]

    @classmethod
    def from_data(cls, ticket: TicketData) -> StudentTicketResponse:
        return cls(
            ticket_id=ticket.ticket_id,
            student_id=ticket.student_id,
            student_name=ticket.student_name,
            student_code=ticket.student_code,
            school_name=ticket.school_name,
            category=ticket.category.value,
            topic=ticket.topic,
            status=ticket.status.value,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            resolved_at=ticket.resolved_at,
            messages=[
                StudentTicketMessageResponse.from_data(message)
                for message in ticket.messages
            ],
        )


class StudentTicketsResponse(ApiModel):
    items: list[StudentTicketResponse]
