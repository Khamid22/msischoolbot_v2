"""Typed read boundary for the Customer Support ticket queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.core.access.context import ActorContext
from backend.core.api.pagination import DEFAULT_PAGE_SIZE
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketCategory,
    TicketStatus,
)


@dataclass(frozen=True)
class TicketQueueQuery:
    search_text: str = ""
    school_id: int | None = None
    status: TicketStatus | None = None
    category: TicketCategory | None = None
    assigned_staff_id: int | None = None
    is_unassigned: bool = False
    cursor: str | None = None
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class TicketQueueItem:
    ticket_id: int
    parent_id: int
    student_id: int | None
    school_id: int
    school_name: str
    topic: str
    category: TicketCategory
    status: TicketStatus
    requester_name: str
    assigned_staff_id: int | None
    assigned_staff_name: str
    reply_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TicketMessageResult:
    message_id: int
    author_type: str
    author_name: str
    body: str
    created_at: datetime


@dataclass(frozen=True)
class TicketDetailResult:
    ticket: TicketQueueItem
    messages: tuple[TicketMessageResult, ...]


@dataclass(frozen=True)
class TicketQueuePage:
    items: tuple[TicketQueueItem, ...]
    next_cursor: str | None
    total: int | None = None


class CustomerSupportTicketQueries(Protocol):
    def list_tickets(
        self,
        actor: ActorContext,
        query: TicketQueueQuery,
    ) -> TicketQueuePage: ...

    def get_ticket(
        self,
        actor: ActorContext,
        ticket_id: int,
    ) -> TicketDetailResult: ...


__all__ = [
    "CustomerSupportTicketQueries",
    "TicketDetailResult",
    "TicketMessageResult",
    "TicketQueueItem",
    "TicketQueuePage",
    "TicketQueueQuery",
]
