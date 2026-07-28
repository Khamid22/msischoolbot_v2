"""Customer Support invoice queue transport."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from backend.application.container import AppContainer
from backend.application.customer_support import build_customer_support_admissions
from backend.core.access import ActorContext, get_actor_context
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.people.customer_support.admissions.contracts import (
    AdmissionError,
    CustomerSupportAdmissions,
    InvoiceQueuePage,
)

router = APIRouter(prefix="/payments")

ActorDependency = Annotated[ActorContext, Depends(get_actor_context)]


def get_payments_use_case(request: Request) -> CustomerSupportAdmissions:
    container: AppContainer = request.app.state.container
    return build_customer_support_admissions(container)


PaymentsUseCaseDependency = Annotated[
    CustomerSupportAdmissions,
    Depends(get_payments_use_case),
]


@router.get(
    "/invoices",
    response_model=ApiSuccess[InvoiceQueuePage],
    operation_id="api_v1_customer_support_invoices",
)
def list_invoices(
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
    q: Annotated[str, Query(max_length=200)] = "",
    status: Annotated[str, Query(max_length=40)] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    try:
        return api_success(
            use_case.list_invoices(
                actor,
                query=q,
                status=status,
                limit=limit,
            )
        )
    except AdmissionError as exc:
        return api_error(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
        )
    except PermissionError as exc:
        return api_error(
            str(exc),
            code="invoice_scope_denied",
            status_code=403,
        )


__all__ = ["router"]
