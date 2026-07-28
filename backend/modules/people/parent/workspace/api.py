"""Parent API v1 transport."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.application.container import AppContainer
from backend.application.parent import build_parent_commands, build_parent_queries
from backend.core.access import ActorContext, get_actor_context, require_role
from backend.core.api import ApiSuccess, api_error, api_success
from backend.core.api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from backend.modules.people.parent.commands import ParentCommands
from backend.modules.people.parent.contracts import (
    ParentPaymentError,
    TicketLifecycleError,
    TicketNotFoundError,
)
from backend.modules.people.parent.policies import (
    ParentAccessError,
    ParentRecordNotFoundError,
)
from backend.modules.people.parent.queries import ParentQueries
from backend.modules.people.parent.schemas import (
    CreateParentTicketRequest,
    ParentBillingStatusResponse,
    ParentChildrenResponse,
    ParentChildResponse,
    ParentInvoiceCheckoutResponse,
    ParentOverviewResponse,
    ParentPaymentsResponse,
    ParentPreferenceResponse,
    ParentTicketResponse,
    ParentTicketsResponse,
    ParentUpdatesResponse,
    ReplyToParentTicketRequest,
    UpdateParentPreferenceRequest,
)

router = APIRouter(
    prefix="/parent",
    dependencies=[Depends(require_role("parent"))],
)


def get_parent_queries(request: Request) -> ParentQueries:
    container: AppContainer = request.app.state.container
    return build_parent_queries(container)


def get_parent_commands(request: Request) -> ParentCommands:
    container: AppContainer = request.app.state.container
    return build_parent_commands(container)


def _error(exc: Exception):
    if isinstance(exc, ParentPaymentError):
        return api_error(str(exc), code=exc.code, status_code=exc.status_code)
    if isinstance(exc, TicketNotFoundError | ParentRecordNotFoundError):
        return api_error(str(exc), code="parent_record_not_found", status_code=404)
    if isinstance(exc, ParentAccessError | PermissionError):
        return api_error(str(exc), code="parent_access_denied", status_code=403)
    if isinstance(exc, TicketLifecycleError):
        return api_error(str(exc), code="ticket_lifecycle_conflict", status_code=409)
    return api_error(str(exc), code="invalid_parent_request", status_code=400)


@router.get(
    "/overview",
    response_model=ApiSuccess[ParentOverviewResponse],
    operation_id="api_v1_parent_overview",
)
def get_overview(
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.overview(actor))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/children",
    response_model=ApiSuccess[ParentChildrenResponse],
    operation_id="api_v1_parent_children",
)
def list_children(
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.list_children(actor))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/children/{student_row_id}",
    response_model=ApiSuccess[ParentChildResponse],
    operation_id="api_v1_parent_child",
)
def get_child(
    student_row_id: int,
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.get_child(actor, student_row_id))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/updates",
    response_model=ApiSuccess[ParentUpdatesResponse],
    operation_id="api_v1_parent_updates",
)
def list_updates(
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.list_updates(actor, limit=limit))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/payments",
    response_model=ApiSuccess[ParentPaymentsResponse],
    operation_id="api_v1_parent_payments",
)
def list_payments(
    student_row_id: int | None = Query(default=None, gt=0, alias="studentId"),
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(
            queries.list_payments(actor, student_row_id=student_row_id)
        )
    except Exception as exc:
        return _error(exc)


@router.get(
    "/billing-status",
    response_model=ApiSuccess[ParentBillingStatusResponse],
    operation_id="api_v1_parent_billing_status",
)
def get_billing_status(
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.get_billing_status(actor))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/payments/{invoice_id}/checkout",
    response_model=ApiSuccess[ParentInvoiceCheckoutResponse],
    operation_id="api_v1_parent_invoice_checkout",
)
def get_invoice_checkout(
    invoice_id: int,
    request: Request,
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        amount_minor, currency = queries.get_invoice_checkout(
            actor,
            invoice_id=invoice_id,
        )
        settings = request.app.state.container.settings.payme
        if not settings.is_configured:
            raise ParentPaymentError(
                "Payme checkout is not configured.",
                status_code=503,
            )
        callback_base = settings.callback_base_url.rstrip("/")
        return api_success(
            ParentInvoiceCheckoutResponse(
                checkout_url=settings.checkout_url,
                merchant_id=settings.merchant_id,
                invoice_id=invoice_id,
                amount_minor=amount_minor,
                currency=currency,
                callback_url=f"{callback_base}/parent/payments",
            )
        )
    except Exception as exc:
        return _error(exc)


@router.get(
    "/tickets",
    response_model=ApiSuccess[ParentTicketsResponse],
    operation_id="api_v1_parent_tickets",
)
def list_tickets(
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.list_tickets(actor, limit=limit))
    except Exception as exc:
        return _error(exc)


@router.post(
    "/tickets",
    response_model=ApiSuccess[ParentTicketResponse],
    status_code=201,
    operation_id="api_v1_parent_create_ticket",
)
def create_ticket(
    payload: CreateParentTicketRequest,
    actor: ActorContext = Depends(get_actor_context),
    commands: ParentCommands = Depends(get_parent_commands),
):
    try:
        return api_success(commands.create_ticket(actor, payload), status_code=201)
    except Exception as exc:
        return _error(exc)


@router.get(
    "/tickets/{ticket_id}",
    response_model=ApiSuccess[ParentTicketResponse],
    operation_id="api_v1_parent_ticket",
)
def get_ticket(
    ticket_id: int,
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.get_ticket(actor, ticket_id))
    except Exception as exc:
        return _error(exc)


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=ApiSuccess[ParentTicketResponse],
    operation_id="api_v1_parent_ticket_reply",
)
def reply_to_ticket(
    ticket_id: int,
    payload: ReplyToParentTicketRequest,
    actor: ActorContext = Depends(get_actor_context),
    commands: ParentCommands = Depends(get_parent_commands),
):
    try:
        return api_success(commands.reply_to_ticket(actor, ticket_id, payload))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/preferences",
    response_model=ApiSuccess[ParentPreferenceResponse],
    operation_id="api_v1_parent_preferences",
)
def get_preferences(
    actor: ActorContext = Depends(get_actor_context),
    queries: ParentQueries = Depends(get_parent_queries),
):
    try:
        return api_success(queries.get_preference(actor))
    except Exception as exc:
        return _error(exc)


@router.patch(
    "/preferences",
    response_model=ApiSuccess[ParentPreferenceResponse],
    operation_id="api_v1_parent_update_preferences",
)
def update_preferences(
    payload: UpdateParentPreferenceRequest,
    actor: ActorContext = Depends(get_actor_context),
    commands: ParentCommands = Depends(get_parent_commands),
):
    try:
        return api_success(commands.update_preference(actor, payload))
    except Exception as exc:
        return _error(exc)


__all__ = ["get_parent_commands", "get_parent_queries", "router"]
