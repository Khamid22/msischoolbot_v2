"""Typed public boundary for the existing support-ticket workflows."""

from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from backend.modules.domains.support_cases.tickets import service
from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketCategory,
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)
from backend.modules.domains.support_cases.tickets.transactional import (
    TICKET_STATUS_RANK,
    TicketData,
    TicketLifecycleError,
    TicketMessageData,
    TicketNotFoundError,
    change_ticket_priority,
    create_parent_ticket,
    get_parent_ticket,
    get_support_ticket,
    list_parent_tickets,
    list_support_tickets,
    reply_to_parent_ticket,
    reply_to_support_ticket,
    set_ticket_waiting_on_requester,
    update_support_ticket,
)


class CreateTicketPayload(TypedDict):
    topic: str
    message: str
    category: NotRequired[TicketCategory | str]


class UpdateTicketPayload(TypedDict, total=False):
    status: TicketStatus | str
    reply: str
    assigned_to: str


class AddTicketReplyPayload(TypedDict, total=False):
    body: str
    reply: str
    status: TicketStatus | str
    assigned_to: str


class TicketMessage(TypedDict):
    id: int
    author_role: str
    author_login: str
    body: str
    created_at: str


class TicketRecord(TypedDict):
    id: int
    parent_admin_id: int
    parent_id: int
    student_row_id: int
    category: str
    topic: str
    message: str
    status: str
    reply: str
    assigned_to: str
    created_at: str
    updated_at: str
    resolved_at: str
    parent_login: str
    parent_display_name: str
    parent_display: str
    parent_phone: str
    parent_email: str
    parent_telegram_username: str
    student_name: str
    student_code: str
    school_name: str
    messages: list[TicketMessage]
    reply_count: int
    latest_reply: str
    latest_reply_at: str


def list_tickets(parent_id: int = 0) -> list[TicketRecord]:
    return cast(list[TicketRecord], service.list_complaints(parent_id))


def get_ticket(ticket_id: int) -> TicketRecord | None:
    return cast(TicketRecord | None, service.get_complaint(ticket_id))


def create_ticket(
    parent_id: int,
    student_row_id: int,
    payload: CreateTicketPayload,
) -> TicketRecord:
    return cast(
        TicketRecord,
        service.create_complaint(parent_id, student_row_id, payload),
    )


def update_ticket(
    ticket_id: int,
    payload: UpdateTicketPayload,
) -> TicketRecord | None:
    return cast(TicketRecord | None, service.update_complaint(ticket_id, payload))


def add_ticket_reply(
    ticket_id: int,
    payload: AddTicketReplyPayload,
    *,
    author_role: str = "customer_support",
    author_login: str = "",
) -> TicketRecord | None:
    return cast(
        TicketRecord | None,
        service.add_complaint_reply(
            ticket_id,
            payload,
            author_role=author_role,
            author_login=author_login,
        ),
    )


# Existing complaint names remain available while callers migrate vocabulary.
list_complaints = list_tickets
get_complaint = get_ticket
create_complaint = create_ticket
update_complaint = update_ticket
add_complaint_reply = add_ticket_reply


__all__ = [
    "AddTicketReplyPayload",
    "CreateTicketPayload",
    "TicketCategory",
    "TicketPriority",
    "TicketSlaState",
    "TicketData",
    "TicketLifecycleError",
    "TicketMessageData",
    "TicketNotFoundError",
    "TicketMessage",
    "TicketRecord",
    "TicketStatus",
    "TICKET_STATUS_RANK",
    "UpdateTicketPayload",
    "add_complaint_reply",
    "add_ticket_reply",
    "change_ticket_priority",
    "create_complaint",
    "create_ticket",
    "get_complaint",
    "get_ticket",
    "list_complaints",
    "list_tickets",
    "update_complaint",
    "update_ticket",
    "create_parent_ticket",
    "get_parent_ticket",
    "get_support_ticket",
    "list_parent_tickets",
    "list_support_tickets",
    "reply_to_parent_ticket",
    "reply_to_support_ticket",
    "set_ticket_waiting_on_requester",
    "update_support_ticket",
]
