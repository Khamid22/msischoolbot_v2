"""Student billing API transport."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.application.container import AppContainer
from backend.core.access import ActorContext, get_actor_context, require_role
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.domains.finance.contracts import BillingAccessStatus
from backend.modules.people.student.billing import (
    StudentBillingAccessError,
    StudentBillingQueries,
)
from backend.modules.people.student.schemas import (
    StudentInvoiceCheckoutResponse,
    StudentPaymentsResponse,
    StudentPaymentResponse,
)

router = APIRouter(dependencies=[Depends(require_role("student"))])


def get_student_billing_queries(request: Request) -> StudentBillingQueries:
    container: AppContainer = request.app.state.container
    return StudentBillingQueries(container.unit_of_work_factory)


def _error(exc: Exception):
    if isinstance(exc, StudentBillingAccessError):
        return api_error(str(exc), code="student_billing_access_denied", status_code=403)
    return api_error(str(exc), code="student_billing_request_failed", status_code=400)


@router.get(
    "/billing-status",
    response_model=ApiSuccess[BillingAccessStatus],
    operation_id="api_v1_student_billing_status",
)
def get_billing_status(
    actor: ActorContext = Depends(get_actor_context),
    queries: StudentBillingQueries = Depends(get_student_billing_queries),
):
    try:
        return api_success(queries.get_access_status(actor))
    except Exception as exc:
        return _error(exc)


@router.get(
    "/payments",
    response_model=ApiSuccess[StudentPaymentsResponse],
    operation_id="api_v1_student_payments",
)
def list_payments(
    actor: ActorContext = Depends(get_actor_context),
    queries: StudentBillingQueries = Depends(get_student_billing_queries),
):
    try:
        return api_success(
            StudentPaymentsResponse(
                items=[
                    StudentPaymentResponse.from_record(record)
                    for record in queries.list_payments(actor)
                ]
            )
        )
    except Exception as exc:
        return _error(exc)


@router.get(
    "/payments/{invoice_id}/checkout",
    response_model=ApiSuccess[StudentInvoiceCheckoutResponse],
    operation_id="api_v1_student_invoice_checkout",
)
def get_invoice_checkout(
    invoice_id: int,
    request: Request,
    actor: ActorContext = Depends(get_actor_context),
    queries: StudentBillingQueries = Depends(get_student_billing_queries),
):
    try:
        amount_minor, currency = queries.get_invoice_checkout(
            actor,
            invoice_id=invoice_id,
        )
        settings = request.app.state.container.settings.payme
        if not settings.is_configured:
            return api_error(
                "Payme checkout is not configured.",
                code="payme_not_configured",
                status_code=503,
            )
        return api_success(
            StudentInvoiceCheckoutResponse(
                checkout_url=settings.checkout_url,
                merchant_id=settings.merchant_id,
                invoice_id=invoice_id,
                amount_minor=amount_minor,
                currency=currency,
                callback_url=(
                    f"{settings.callback_base_url.rstrip('/')}/student/payments"
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


__all__ = ["router"]
