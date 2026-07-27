"""Customer Support ticket API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.core.api import ApiModel
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)
from backend.modules.people.customer_support.tickets.commands import TicketMutationResult
from backend.modules.people.customer_support.tickets.queries import (
    TicketDetailResult,
    TicketQueueItem,
    TicketQueuePage,
)


class TicketQueueItemResponse(ApiModel):
    ticket_id: int
    parent_id: int
    student_id: int | None
    school_id: int
    school_name: str
    topic: str
    category: str
    status: str
    priority: TicketPriority
    sla_state: TicketSlaState
    requester_name: str
    assigned_staff_id: int | None
    assigned_staff_name: str
    reply_count: int
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    first_responded_at: datetime | None
    is_waiting_on_requester: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_item(cls, item: TicketQueueItem) -> TicketQueueItemResponse:
        return cls(
            ticket_id=item.ticket_id,
            parent_id=item.parent_id,
            student_id=item.student_id,
            school_id=item.school_id,
            school_name=item.school_name,
            topic=item.topic,
            category=item.category.value,
            status=item.status.value,
            priority=item.priority,
            sla_state=item.sla_state,
            requester_name=item.requester_name,
            assigned_staff_id=item.assigned_staff_id,
            assigned_staff_name=item.assigned_staff_name,
            reply_count=item.reply_count,
            first_response_due_at=item.first_response_due_at,
            resolution_due_at=item.resolution_due_at,
            first_responded_at=item.first_responded_at,
            is_waiting_on_requester=item.is_waiting_on_requester,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class TicketMessageResponse(ApiModel):
    message_id: int
    author_type: str
    author_name: str
    body: str
    created_at: datetime


class TicketDetailResponse(ApiModel):
    ticket: TicketQueueItemResponse
    messages: list[TicketMessageResponse] = Field(default_factory=list)

    @classmethod
    def from_result(cls, result: TicketDetailResult) -> TicketDetailResponse:
        return cls(
            ticket=TicketQueueItemResponse.from_item(result.ticket),
            messages=[TicketMessageResponse(**message.__dict__) for message in result.messages],
        )


class TicketQueueResponse(ApiModel):
    items: list[TicketQueueItemResponse] = Field(default_factory=list)
    next_cursor: str | None = None
    total: int | None = None
    actor_staff_id: int | None = None

    @classmethod
    def from_page(
        cls,
        page: TicketQueuePage,
        *,
        actor_staff_id: int | None = None,
    ) -> TicketQueueResponse:
        return cls(
            items=[TicketQueueItemResponse.from_item(item) for item in page.items],
            next_cursor=page.next_cursor,
            total=page.total,
            actor_staff_id=actor_staff_id,
        )


class ReplyTicketRequest(ApiModel):
    body: str = Field(min_length=1, max_length=4_000)


class AssignTicketRequest(ApiModel):
    assigned_staff_id: int | None = Field(default=None, gt=0)


class ChangeTicketStatusRequest(ApiModel):
    status: TicketStatus
    reason: str = Field(default="", max_length=1_000)


class ChangeTicketPriorityRequest(ApiModel):
    priority: TicketPriority


class SetTicketWaitingRequest(ApiModel):
    is_waiting: bool


class TicketMutationResponse(ApiModel):
    ticket_id: int
    status: TicketStatus
    updated_at: str

    @classmethod
    def from_result(cls, result: TicketMutationResult) -> TicketMutationResponse:
        return cls(
            ticket_id=result.ticket_id,
            status=result.status,
            updated_at=result.updated_at,
        )


__all__ = [name for name in globals() if name.endswith(("Request", "Response"))]
