"""Student support API transport."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.application.container import AppContainer
from backend.core.access import ActorContext, get_actor_context, require_role
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.domains.support_cases.tickets.contracts import (
    TicketLifecycleError,
    TicketNotFoundError,
)
from backend.modules.people.student.schemas import (
    CreateStudentTicketRequest,
    ReplyToStudentTicketRequest,
    StudentTicketResponse,
    StudentTicketsResponse,
)
from backend.modules.people.student.support import (
    StudentSupportAccessError,
    StudentSupportService,
)

router = APIRouter(dependencies=[Depends(require_role("student"))])


def get_student_support(request: Request) -> StudentSupportService:
    container: AppContainer = request.app.state.container
    return StudentSupportService(container.unit_of_work_factory)


def _error(exc: Exception):
    if isinstance(exc, TicketNotFoundError):
        return api_error(str(exc), code="student_ticket_not_found", status_code=404)
    if isinstance(exc, StudentSupportAccessError):
        return api_error(str(exc), code="student_support_access_denied", status_code=403)
    if isinstance(exc, TicketLifecycleError):
        return api_error(str(exc), code="student_ticket_read_only", status_code=409)
    return api_error(str(exc), code="student_support_request_failed", status_code=400)


@router.get(
    "/support/tickets",
    response_model=ApiSuccess[StudentTicketsResponse],
    operation_id="api_v1_student_support_tickets",
)
def list_tickets(
    actor: ActorContext = Depends(get_actor_context),
    service: StudentSupportService = Depends(get_student_support),
):
    try:
        return api_success(
            StudentTicketsResponse(
                items=[
                    StudentTicketResponse.from_data(ticket)
                    for ticket in service.list_tickets(actor)
                ]
            )
        )
    except Exception as exc:
        return _error(exc)


@router.post(
    "/support/tickets",
    response_model=ApiSuccess[StudentTicketResponse],
    status_code=201,
    operation_id="api_v1_student_create_support_ticket",
)
def create_ticket(
    payload: CreateStudentTicketRequest,
    actor: ActorContext = Depends(get_actor_context),
    service: StudentSupportService = Depends(get_student_support),
):
    try:
        return api_success(
            StudentTicketResponse.from_data(service.create_ticket(actor, payload)),
            status_code=201,
        )
    except Exception as exc:
        return _error(exc)


@router.get(
    "/support/tickets/{ticket_id}",
    response_model=ApiSuccess[StudentTicketResponse],
    operation_id="api_v1_student_support_ticket",
)
def get_ticket(
    ticket_id: int,
    actor: ActorContext = Depends(get_actor_context),
    service: StudentSupportService = Depends(get_student_support),
):
    try:
        return api_success(StudentTicketResponse.from_data(service.get_ticket(actor, ticket_id)))
    except Exception as exc:
        return _error(exc)


@router.post(
    "/support/tickets/{ticket_id}/messages",
    response_model=ApiSuccess[StudentTicketResponse],
    operation_id="api_v1_student_reply_support_ticket",
)
def reply_to_ticket(
    ticket_id: int,
    payload: ReplyToStudentTicketRequest,
    actor: ActorContext = Depends(get_actor_context),
    service: StudentSupportService = Depends(get_student_support),
):
    try:
        return api_success(
            StudentTicketResponse.from_data(
                service.reply(actor, ticket_id, payload)
            )
        )
    except Exception as exc:
        return _error(exc)


__all__ = ["router"]
