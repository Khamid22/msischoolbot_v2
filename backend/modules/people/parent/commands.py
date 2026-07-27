"""Typed parent workspace commands with explicit transaction ownership."""

from __future__ import annotations

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.parent_relationships.contracts import (
    set_parent_preferred_language,
)
from backend.modules.domains.support_cases.tickets.contracts import (
    create_parent_ticket,
    reply_to_parent_ticket,
)
from backend.modules.people.parent.policies import require_parent_capability
from backend.modules.people.parent.schemas import (
    CreateParentTicketRequest,
    ParentPreferenceResponse,
    ParentTicketResponse,
    ReplyToParentTicketRequest,
    UpdateParentPreferenceRequest,
)


class ParentCommands:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def create_ticket(
        self,
        actor: ActorContext,
        request: CreateParentTicketRequest,
    ) -> ParentTicketResponse:
        parent_id = require_parent_capability(actor, Capability.CONTACT_SUPPORT)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = create_parent_ticket(
                unit_of_work.conn,
                parent_id=parent_id,
                student_row_id=request.student_row_id,
                category=request.category,
                topic=request.topic,
                message=request.message,
            )
            commit_unit_of_work(unit_of_work)
        return ParentTicketResponse.from_data(ticket)

    def reply_to_ticket(
        self,
        actor: ActorContext,
        ticket_id: int,
        request: ReplyToParentTicketRequest,
    ) -> ParentTicketResponse:
        parent_id = require_parent_capability(actor, Capability.CONTACT_SUPPORT)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = reply_to_parent_ticket(
                unit_of_work.conn,
                parent_id=parent_id,
                ticket_id=ticket_id,
                body=request.body,
            )
            commit_unit_of_work(unit_of_work)
        return ParentTicketResponse.from_data(ticket)

    def update_preference(
        self,
        actor: ActorContext,
        request: UpdateParentPreferenceRequest,
    ) -> ParentPreferenceResponse:
        parent_id = require_parent_capability(actor, Capability.VIEW_DASHBOARD)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            preference = set_parent_preferred_language(
                unit_of_work.conn,
                parent_id=parent_id,
                preferred_language=request.preferred_language,
            )
            commit_unit_of_work(unit_of_work)
        return ParentPreferenceResponse(**preference.__dict__)


__all__ = ["ParentCommands"]
