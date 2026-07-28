"""Customer Support admissions transport."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import RedirectResponse

from backend.application.container import AppContainer
from backend.application.customer_support import build_customer_support_admissions
from backend.core.access import ActorContext, get_actor_context
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.people.customer_support.admissions.contracts import (
    AddPaidInvoiceCommand,
    AdmissionDetail,
    AdmissionError,
    AdmissionGroupOption,
    AdmissionPage,
    AdmissionStatus,
    CancelAdmissionCommand,
    CreateAdmissionCommand,
    CustomerSupportAdmissions,
    ManualPaymentCommand,
    ReverseManualPaymentCommand,
    ReviewContractCommand,
    UpdateAdmissionCommand,
    VoidInvoiceCommand,
)
from backend.modules.people.customer_support.admissions.schemas import (
    AdmissionCreatedResponse,
    AdmissionSentResponse,
)

router = APIRouter(prefix="/admissions")


def get_admissions_use_case(request: Request) -> CustomerSupportAdmissions:
    container: AppContainer = request.app.state.container
    return build_customer_support_admissions(container)


ActorDependency = Annotated[ActorContext, Depends(get_actor_context)]
AdmissionsUseCaseDependency = Annotated[
    CustomerSupportAdmissions,
    Depends(get_admissions_use_case),
]


def _error(exc: Exception):
    if isinstance(exc, AdmissionError):
        return api_error(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
        )
    if isinstance(exc, PermissionError):
        return api_error(str(exc), code="admission_scope_denied", status_code=403)
    return api_error(str(exc), code="admission_error", status_code=400)


@router.get(
    "/groups",
    response_model=ApiSuccess[list[AdmissionGroupOption]],
    operation_id="api_v1_customer_support_admission_groups",
)
def list_group_options(
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.list_group_options(actor))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.get(
    "",
    response_model=ApiSuccess[AdmissionPage],
    operation_id="api_v1_customer_support_admissions",
)
def list_admissions(
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
    q: Annotated[str, Query(max_length=200)] = "",
    status: Annotated[AdmissionStatus | str, Query()] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    try:
        status_value = status.value if isinstance(status, AdmissionStatus) else str(status)
        return api_success(
            use_case.list_admissions(
                actor,
                query=q,
                status=status_value,
                limit=limit,
            )
        )
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "",
    response_model=ApiSuccess[AdmissionCreatedResponse],
    operation_id="api_v1_customer_support_create_admission",
)
def create_admission(
    payload: CreateAdmissionCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        admission, link, public_url = use_case.create_admission(actor, payload)
        return api_success(
            AdmissionCreatedResponse(
                admission=admission,
                admission_link=link,
                public_url=public_url,
            )
        )
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.get(
    "/{admission_id}",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_admission",
)
def get_admission(
    admission_id: int,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.get_admission(actor, admission_id))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.patch(
    "/{admission_id}",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_update_admission",
)
def update_admission(
    admission_id: int,
    payload: UpdateAdmissionCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.update_admission(actor, admission_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/{admission_id}/contract",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_upload_admission_contract",
)
def upload_contract(
    admission_id: int,
    document: Annotated[UploadFile, File()],
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.upload_contract(actor, admission_id, document))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/{admission_id}/send",
    response_model=ApiSuccess[AdmissionSentResponse],
    operation_id="api_v1_customer_support_send_admission",
)
def send_admission(
    admission_id: int,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        admission, public_url = use_case.send_contract(actor, admission_id)
        return api_success(
            AdmissionSentResponse(
                admission=admission,
                public_url=public_url,
            )
        )
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/{admission_id}/contract/review",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_review_admission_contract",
)
def review_contract(
    admission_id: int,
    payload: ReviewContractCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.review_contract(actor, admission_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/invoices/{invoice_id}/manual-payment",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_admission_manual_payment",
)
def record_manual_payment(
    invoice_id: int,
    payload: ManualPaymentCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.record_manual_payment(actor, invoice_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/{admission_id}/paid-invoice",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_add_paid_admission_invoice",
)
def add_paid_invoice(
    admission_id: int,
    payload: AddPaidInvoiceCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.add_paid_invoice(actor, admission_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/invoices/{invoice_id}/void",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_void_admission_invoice",
)
def void_invoice(
    invoice_id: int,
    payload: VoidInvoiceCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.void_invoice(actor, invoice_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/payments/{payment_id}/reverse",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_reverse_admission_payment",
)
def reverse_manual_payment(
    payment_id: int,
    payload: ReverseManualPaymentCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.reverse_manual_payment(actor, payment_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.post(
    "/{admission_id}/cancel",
    response_model=ApiSuccess[AdmissionDetail],
    operation_id="api_v1_customer_support_cancel_admission",
)
def cancel_admission(
    admission_id: int,
    payload: CancelAdmissionCommand,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
):
    try:
        return api_success(use_case.cancel_admission(actor, admission_id, payload))
    except (AdmissionError, PermissionError, ValueError) as exc:
        return _error(exc)


@router.get(
    "/{admission_id}/contract/download",
    response_class=RedirectResponse,
    operation_id="api_v1_customer_support_download_admission_contract",
)
def download_contract(
    admission_id: int,
    actor: ActorDependency,
    use_case: AdmissionsUseCaseDependency,
    signed: Annotated[bool, Query()] = False,
):
    return RedirectResponse(
        use_case.contract_download_url(actor, admission_id, signed=signed),
        status_code=302,
    )


__all__ = ["router"]
