"""Customer Support transport for school-scoped tickets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.application.container import AppContainer
from backend.application.customer_support import build_customer_support_tickets
from backend.core.access import ActorContext, get_actor_context
from backend.core.api import ApiSuccess, api_error, api_success
from backend.core.api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from backend.modules.people.customer_support.policies import CustomerSupportAccessError
from backend.modules.people.customer_support.tickets.commands import (
    AssignTicketCommand,
    ChangeTicketPriorityCommand,
    ChangeTicketStatusCommand,
    ReplyToTicketCommand,
    SetTicketWaitingCommand,
)
from backend.modules.people.customer_support.tickets.contracts import (
    TicketCategory,
    TicketLifecycleError,
    TicketNotFoundError,
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)
from backend.modules.people.customer_support.tickets.queries import TicketQueueQuery
from backend.modules.people.customer_support.tickets.schemas import (
    AssignTicketRequest,
    ChangeTicketPriorityRequest,
    ChangeTicketStatusRequest,
    ReplyTicketRequest,
    SetTicketWaitingRequest,
    TicketDetailResponse,
    TicketMutationResponse,
    TicketQueueResponse,
)
from backend.modules.people.customer_support.tickets.use_cases import CustomerSupportTickets

router = APIRouter(prefix="/tickets")


def get_ticket_use_cases(request: Request) -> CustomerSupportTickets:
    container: AppContainer = request.app.state.container
    return build_customer_support_tickets(container)


def _error(exc: Exception):
    if isinstance(exc, TicketNotFoundError):
        return api_error(str(exc), code="ticket_not_found", status_code=404)
    if isinstance(exc, CustomerSupportAccessError | PermissionError):
        return api_error(str(exc), code="ticket_scope_denied", status_code=403)
    if isinstance(exc, TicketLifecycleError):
        return api_error(str(exc), code="ticket_lifecycle_conflict", status_code=409)
    return api_error(str(exc), code="invalid_ticket_request", status_code=400)


@router.get(
    "",
    response_model=ApiSuccess[TicketQueueResponse],
    operation_id="api_v1_customer_support_tickets",
)
def list_tickets(
    q: str = Query(default="", max_length=200),
    school_id: int | None = Query(default=None, gt=0, alias="schoolId"),
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    category: TicketCategory | None = Query(default=None),
    priority: TicketPriority | None = Query(default=None),
    sla_state: TicketSlaState | None = Query(default=None, alias="slaState"),
    assigned_staff_id: int | None = Query(
        default=None,
        gt=0,
        alias="assignedStaffId",
    ),
    is_unassigned: bool = Query(default=False, alias="unassigned"),
    assigned_to_me: bool = Query(default=False, alias="assignedToMe"),
    cursor: str = Query(default="", max_length=500),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        page = use_cases.list_tickets(
            actor,
            TicketQueueQuery(
                search_text=q,
                school_id=school_id,
                status=ticket_status,
                category=category,
                priority=priority,
                sla_state=sla_state,
                assigned_staff_id=assigned_staff_id,
                assigned_to_me=assigned_to_me,
                is_unassigned=is_unassigned,
                cursor=cursor or None,
                page_size=limit,
            ),
        )
    except Exception as exc:
        return _error(exc)
    return api_success(
        TicketQueueResponse.from_page(
            page,
            actor_staff_id=actor.staff_id,
        )
    )


@router.get(
    "/{ticket_id}",
    response_model=ApiSuccess[TicketDetailResponse],
    operation_id="api_v1_customer_support_ticket",
)
def get_ticket(
    ticket_id: int,
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        result = use_cases.get_ticket(actor, ticket_id)
    except Exception as exc:
        return _error(exc)
    return api_success(TicketDetailResponse.from_result(result))


@router.post(
    "/{ticket_id}/messages",
    response_model=ApiSuccess[TicketMutationResponse],
    operation_id="api_v1_customer_support_ticket_reply",
)
def reply_to_ticket(
    ticket_id: int,
    payload: ReplyTicketRequest,
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        result = use_cases.reply_to_ticket(
            actor,
            ReplyToTicketCommand(ticket_id=ticket_id, body=payload.body),
        )
    except Exception as exc:
        return _error(exc)
    return api_success(TicketMutationResponse.from_result(result))


@router.patch(
    "/{ticket_id}/assignment",
    response_model=ApiSuccess[TicketMutationResponse],
    operation_id="api_v1_customer_support_ticket_assignment",
)
def assign_ticket(
    ticket_id: int,
    payload: AssignTicketRequest,
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        result = use_cases.assign_ticket(
            actor,
            AssignTicketCommand(
                ticket_id=ticket_id,
                assigned_staff_id=payload.assigned_staff_id,
            ),
        )
    except Exception as exc:
        return _error(exc)
    return api_success(TicketMutationResponse.from_result(result))


@router.patch(
    "/{ticket_id}/status",
    response_model=ApiSuccess[TicketMutationResponse],
    operation_id="api_v1_customer_support_ticket_status",
)
def change_ticket_status(
    ticket_id: int,
    payload: ChangeTicketStatusRequest,
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        result = use_cases.change_ticket_status(
            actor,
            ChangeTicketStatusCommand(
                ticket_id=ticket_id,
                status=payload.status,
                reason=payload.reason,
            ),
        )
    except Exception as exc:
        return _error(exc)
    return api_success(TicketMutationResponse.from_result(result))


@router.patch(
    "/{ticket_id}/priority",
    response_model=ApiSuccess[TicketMutationResponse],
    operation_id="api_v1_customer_support_ticket_priority",
)
def change_ticket_priority(
    ticket_id: int,
    payload: ChangeTicketPriorityRequest,
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        result = use_cases.change_ticket_priority(
            actor,
            ChangeTicketPriorityCommand(
                ticket_id=ticket_id,
                priority=payload.priority,
            ),
        )
    except Exception as exc:
        return _error(exc)
    return api_success(TicketMutationResponse.from_result(result))


@router.patch(
    "/{ticket_id}/waiting-state",
    response_model=ApiSuccess[TicketMutationResponse],
    operation_id="api_v1_customer_support_ticket_waiting_state",
)
def set_ticket_waiting(
    ticket_id: int,
    payload: SetTicketWaitingRequest,
    actor: ActorContext = Depends(get_actor_context),
    use_cases: CustomerSupportTickets = Depends(get_ticket_use_cases),
):
    try:
        result = use_cases.set_ticket_waiting(
            actor,
            SetTicketWaitingCommand(
                ticket_id=ticket_id,
                is_waiting=payload.is_waiting,
            ),
        )
    except Exception as exc:
        return _error(exc)
    return api_success(TicketMutationResponse.from_result(result))


__all__ = ["get_ticket_use_cases", "router"]
