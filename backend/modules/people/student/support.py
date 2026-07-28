"""Student-owned support workflows backed by Support Cases contracts."""

from __future__ import annotations

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability, Role
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketData,
    create_student_ticket,
    get_student_ticket,
    list_student_tickets,
    reply_to_student_ticket,
)
from backend.modules.people.student.schemas import (
    CreateStudentTicketRequest,
    ReplyToStudentTicketRequest,
)


class StudentSupportAccessError(PermissionError):
    pass


def _student_identity(actor: ActorContext) -> tuple[int, int]:
    if actor.role is not Role.STUDENT:
        raise StudentSupportAccessError("Student access is required.")
    if Capability.CONTACT_SUPPORT not in actor.capabilities:
        raise StudentSupportAccessError("Support access is not available.")
    if actor.account_id is None or actor.student_id is None:
        raise StudentSupportAccessError("Student account was not found.")
    return actor.account_id, actor.student_id


class StudentSupportService:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def list_tickets(self, actor: ActorContext) -> tuple[TicketData, ...]:
        account_id, _ = _student_identity(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return list_student_tickets(unit_of_work.conn, account_id=account_id)

    def get_ticket(self, actor: ActorContext, ticket_id: int) -> TicketData:
        account_id, _ = _student_identity(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return get_student_ticket(
                unit_of_work.conn,
                account_id=account_id,
                ticket_id=ticket_id,
            )

    def create_ticket(
        self,
        actor: ActorContext,
        payload: CreateStudentTicketRequest,
    ) -> TicketData:
        account_id, student_id = _student_identity(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = create_student_ticket(
                unit_of_work.conn,
                account_id=account_id,
                student_id=student_id,
                category=payload.category,
                topic=payload.topic,
                message=payload.message,
            )
            commit_unit_of_work(unit_of_work)
            return ticket

    def reply(
        self,
        actor: ActorContext,
        ticket_id: int,
        payload: ReplyToStudentTicketRequest,
    ) -> TicketData:
        account_id, _ = _student_identity(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            ticket = reply_to_student_ticket(
                unit_of_work.conn,
                account_id=account_id,
                ticket_id=ticket_id,
                body=payload.body,
            )
            commit_unit_of_work(unit_of_work)
            return ticket


__all__ = ["StudentSupportAccessError", "StudentSupportService"]
