"""PostgreSQL-backed Customer Support ticket commands and queries."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability
from backend.core.api.pagination import normalize_page_size
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.support_cases.tickets.contracts import (
    TICKET_STATUS_RANK,
    TicketData,
    change_ticket_priority,
    get_support_ticket,
    list_support_tickets,
    reply_to_support_ticket,
    set_ticket_waiting_on_requester,
    update_support_ticket,
)
from backend.modules.people.customer_support.policies import require_capability
from backend.modules.people.customer_support.scope import CustomerSupportScopeProvider
from backend.modules.people.customer_support.tickets.commands import (
    AssignTicketCommand,
    ChangeTicketPriorityCommand,
    ChangeTicketStatusCommand,
    ReplyToTicketCommand,
    SetTicketWaitingCommand,
    TicketMutationResult,
)
from backend.modules.people.customer_support.tickets.queries import (
    TicketDetailResult,
    TicketMessageResult,
    TicketQueueItem,
    TicketQueuePage,
    TicketQueueQuery,
)


def _datetime(value: str) -> datetime:
    normalized = str(value or "").strip().replace("Z", "+00:00")
    if not normalized:
        return datetime.fromtimestamp(0, UTC)
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _optional_datetime(value: str) -> datetime | None:
    return _datetime(value) if str(value or "").strip() else None


def _queue_item(ticket: TicketData) -> TicketQueueItem:
    return TicketQueueItem(
        ticket_id=ticket.ticket_id,
        parent_id=ticket.parent_id,
        student_id=ticket.student_id,
        school_id=ticket.school_id,
        school_name=ticket.school_name,
        topic=ticket.topic,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        sla_state=ticket.sla_state,
        requester_name=ticket.parent_name or ticket.student_name or ticket.student_code,
        assigned_staff_id=ticket.assigned_staff_id,
        assigned_staff_name=ticket.assigned_staff_name,
        reply_count=sum(message.author_type != "parent" for message in ticket.messages),
        first_response_due_at=_optional_datetime(ticket.first_response_due_at),
        resolution_due_at=_optional_datetime(ticket.resolution_due_at),
        first_responded_at=_optional_datetime(ticket.first_responded_at),
        is_waiting_on_requester=bool(ticket.waiting_on_requester_at),
        created_at=_datetime(ticket.created_at),
        updated_at=_datetime(ticket.updated_at),
    )


def _decode_cursor(value: str | None) -> tuple[int, str, int]:
    if not value:
        return -1, "", 0
    try:
        padded = value + ("=" * (-len(value) % 4))
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        status_rank, updated_at, ticket_id = json.loads(raw)
        parsed_rank = int(status_rank)
        parsed_ticket_id = int(ticket_id)
        if not str(updated_at).strip():
            raise ValueError
        _datetime(str(updated_at))
        if parsed_rank not in TICKET_STATUS_RANK.values() or parsed_ticket_id <= 0:
            raise ValueError
        return parsed_rank, str(updated_at), parsed_ticket_id
    except (
        binascii.Error,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("The ticket cursor is invalid.") from exc


def _encode_cursor(ticket: TicketData) -> str:
    payload = json.dumps(
        [
            TICKET_STATUS_RANK[ticket.status],
            ticket.cursor_updated_at,
            ticket.ticket_id,
        ],
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


class CustomerSupportTickets:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        scope_resolver: CustomerSupportScopeProvider,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._scope_resolver = scope_resolver

    def _scope(self, actor: ActorContext, capability: Capability) -> ActorContext:
        require_capability(actor, capability)
        return self._scope_resolver.resolve(actor)

    def list_tickets(
        self,
        actor: ActorContext,
        query: TicketQueueQuery,
    ) -> TicketQueuePage:
        scoped_actor = self._scope(actor, Capability.VIEW_TICKETS)
        cursor_status_rank, cursor_updated_at, cursor_id = _decode_cursor(query.cursor)
        page_size = normalize_page_size(query.page_size)
        assigned_staff_id = query.assigned_staff_id
        if query.assigned_to_me:
            if scoped_actor.staff_id is None:
                raise PermissionError("Customer Support staff identity is required.")
            if assigned_staff_id is not None and assigned_staff_id != scoped_actor.staff_id:
                raise ValueError("assignedToMe cannot target another staff member.")
            assigned_staff_id = scoped_actor.staff_id
        with self._unit_of_work_factory.read() as unit_of_work:
            tickets = list_support_tickets(
                unit_of_work.conn,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
                status=query.status,
                category=query.category,
                priority=query.priority,
                sla_state_filter=query.sla_state,
                search_text=query.search_text,
                school_id=query.school_id,
                assigned_staff_id=assigned_staff_id,
                is_unassigned=query.is_unassigned,
                cursor_status_rank=cursor_status_rank,
                cursor_updated_at=cursor_updated_at,
                cursor_id=cursor_id,
                limit=page_size + 1,
            )
        page_tickets = tickets[:page_size]
        has_more = len(tickets) > len(page_tickets)
        return TicketQueuePage(
            items=tuple(_queue_item(ticket) for ticket in page_tickets),
            next_cursor=(_encode_cursor(page_tickets[-1]) if has_more and page_tickets else None),
            total=None,
        )

    def get_ticket(
        self,
        actor: ActorContext,
        ticket_id: int,
    ) -> TicketDetailResult:
        scoped_actor = self._scope(actor, Capability.VIEW_TICKETS)
        with self._unit_of_work_factory.read() as unit_of_work:
            ticket = get_support_ticket(
                unit_of_work.conn,
                ticket_id=ticket_id,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
            )
        return TicketDetailResult(
            ticket=_queue_item(ticket),
            messages=tuple(
                TicketMessageResult(
                    message_id=message.message_id,
                    author_type=message.author_type,
                    author_name=message.author_name,
                    body=message.body,
                    created_at=_datetime(message.created_at),
                )
                for message in ticket.messages
            ),
        )

    def assign_ticket(
        self,
        actor: ActorContext,
        command: AssignTicketCommand,
    ) -> TicketMutationResult:
        return self._update(
            actor,
            ticket_id=command.ticket_id,
            capability=Capability.ASSIGN_TICKETS,
            assigned_staff_id=command.assigned_staff_id,
            requested_status=None,
            reason="",
        )

    def change_ticket_status(
        self,
        actor: ActorContext,
        command: ChangeTicketStatusCommand,
    ) -> TicketMutationResult:
        capability = (
            Capability.RESOLVE_TICKETS
            if command.status.value == "resolved"
            else Capability.ESCALATE_TICKETS
        )
        return self._update(
            actor,
            ticket_id=command.ticket_id,
            capability=capability,
            assigned_staff_id=None,
            requested_status=command.status,
            reason=command.reason,
        )

    def _update(
        self,
        actor: ActorContext,
        *,
        ticket_id: int,
        capability: Capability,
        assigned_staff_id: int | None,
        requested_status,
        reason: str,
    ) -> TicketMutationResult:
        scoped_actor = self._scope(actor, capability)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            current = get_support_ticket(
                unit_of_work.conn,
                ticket_id=ticket_id,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
                for_update=True,
            )
            ticket = update_support_ticket(
                unit_of_work.conn,
                ticket_id=ticket_id,
                assigned_staff_id=(
                    current.assigned_staff_id if requested_status is not None else assigned_staff_id
                ),
                status=requested_status or current.status,
                actor_staff_id=scoped_actor.staff_id,
                actor_account_id=scoped_actor.account_id,
                reason=reason,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
            )
            commit_unit_of_work(unit_of_work)
        return TicketMutationResult(
            ticket_id=ticket.ticket_id,
            status=ticket.status,
            priority=ticket.priority,
            sla_state=ticket.sla_state,
            is_waiting_on_requester=bool(ticket.waiting_on_requester_at),
            updated_at=ticket.updated_at,
        )

    def reply_to_ticket(
        self,
        actor: ActorContext,
        command: ReplyToTicketCommand,
    ) -> TicketMutationResult:
        scoped_actor = self._scope(actor, Capability.REPLY_TICKETS)
        staff_id = scoped_actor.staff_id
        if staff_id is None:
            raise PermissionError("Customer Support staff identity is required.")
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = reply_to_support_ticket(
                unit_of_work.conn,
                ticket_id=command.ticket_id,
                staff_id=staff_id,
                account_id=scoped_actor.account_id,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
                body=command.body,
            )
            commit_unit_of_work(unit_of_work)
        return TicketMutationResult(
            ticket_id=ticket.ticket_id,
            status=ticket.status,
            priority=ticket.priority,
            sla_state=ticket.sla_state,
            is_waiting_on_requester=bool(ticket.waiting_on_requester_at),
            updated_at=ticket.updated_at,
        )

    def change_ticket_priority(
        self,
        actor: ActorContext,
        command: ChangeTicketPriorityCommand,
    ) -> TicketMutationResult:
        scoped_actor = self._scope(actor, Capability.ESCALATE_TICKETS)
        staff_id = scoped_actor.staff_id
        if staff_id is None:
            raise PermissionError("Customer Support staff identity is required.")
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = change_ticket_priority(
                unit_of_work.conn,
                ticket_id=command.ticket_id,
                priority=command.priority,
                actor_staff_id=staff_id,
                actor_account_id=scoped_actor.account_id,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
            )
            commit_unit_of_work(unit_of_work)
        return self._mutation_result(ticket)

    def set_ticket_waiting(
        self,
        actor: ActorContext,
        command: SetTicketWaitingCommand,
    ) -> TicketMutationResult:
        scoped_actor = self._scope(actor, Capability.REPLY_TICKETS)
        staff_id = scoped_actor.staff_id
        if staff_id is None:
            raise PermissionError("Customer Support staff identity is required.")
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = set_ticket_waiting_on_requester(
                unit_of_work.conn,
                ticket_id=command.ticket_id,
                is_waiting=command.is_waiting,
                actor_staff_id=staff_id,
                actor_account_id=scoped_actor.account_id,
                allowed_school_ids=scoped_actor.school_scope.allowed_school_ids,
                all_schools=scoped_actor.school_scope.all_schools,
            )
            commit_unit_of_work(unit_of_work)
        return self._mutation_result(ticket)

    @staticmethod
    def _mutation_result(ticket: TicketData) -> TicketMutationResult:
        return TicketMutationResult(
            ticket_id=ticket.ticket_id,
            status=ticket.status,
            priority=ticket.priority,
            sla_state=ticket.sla_state,
            is_waiting_on_requester=bool(ticket.waiting_on_requester_at),
            updated_at=ticket.updated_at,
        )


__all__ = ["CustomerSupportTickets"]
