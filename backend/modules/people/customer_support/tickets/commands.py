"""Typed write boundary for Customer Support ticket workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.core.access.context import ActorContext
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)


@dataclass(frozen=True)
class AssignTicketCommand:
    ticket_id: int
    assigned_staff_id: int | None


@dataclass(frozen=True)
class ReplyToTicketCommand:
    ticket_id: int
    body: str


@dataclass(frozen=True)
class ChangeTicketStatusCommand:
    ticket_id: int
    status: TicketStatus
    reason: str = ""


@dataclass(frozen=True)
class ChangeTicketPriorityCommand:
    ticket_id: int
    priority: TicketPriority


@dataclass(frozen=True)
class SetTicketWaitingCommand:
    ticket_id: int
    is_waiting: bool


@dataclass(frozen=True)
class TicketMutationResult:
    ticket_id: int
    status: TicketStatus
    updated_at: str
    priority: TicketPriority = TicketPriority.NORMAL
    sla_state: TicketSlaState = TicketSlaState.ON_TRACK
    is_waiting_on_requester: bool = False


class CustomerSupportTicketCommands(Protocol):
    def assign_ticket(
        self,
        actor: ActorContext,
        command: AssignTicketCommand,
    ) -> TicketMutationResult: ...

    def reply_to_ticket(
        self,
        actor: ActorContext,
        command: ReplyToTicketCommand,
    ) -> TicketMutationResult: ...

    def change_ticket_status(
        self,
        actor: ActorContext,
        command: ChangeTicketStatusCommand,
    ) -> TicketMutationResult: ...

    def change_ticket_priority(
        self,
        actor: ActorContext,
        command: ChangeTicketPriorityCommand,
    ) -> TicketMutationResult: ...

    def set_ticket_waiting(
        self,
        actor: ActorContext,
        command: SetTicketWaitingCommand,
    ) -> TicketMutationResult: ...


__all__ = [
    "AssignTicketCommand",
    "ChangeTicketPriorityCommand",
    "ChangeTicketStatusCommand",
    "CustomerSupportTicketCommands",
    "ReplyToTicketCommand",
    "SetTicketWaitingCommand",
    "TicketMutationResult",
]
