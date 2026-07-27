"""Typed write boundary for Customer Support ticket workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.core.access.context import ActorContext
from backend.modules.domains.support_cases.tickets.contracts import TicketStatus


@dataclass(frozen=True)
class AssignTicketCommand:
    ticket_id: int
    assigned_account_id: int | None


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
class TicketMutationResult:
    ticket_id: int
    status: TicketStatus
    updated_at: str


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


__all__ = [
    "AssignTicketCommand",
    "ChangeTicketStatusCommand",
    "CustomerSupportTicketCommands",
    "ReplyToTicketCommand",
    "TicketMutationResult",
]
