"""Customer Support transport for the unified Finance ledger."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from backend.application.container import AppContainer
from backend.application.customer_support import build_customer_support_payments
from backend.core.access import ActorContext, get_actor_context
from backend.core.api import ApiModel, ApiSuccess, api_error, api_success
from backend.modules.people.customer_support.payments.contracts import (
    AddPaidStudentInvoiceCommand,
    BillingError,
    BillingItemInput,
    BillingProfileResult,
    ConfigureBillingProfileCommand,
    InvoiceDetail,
    InvoiceKind,
    InvoicePage,
    IssueStudentInvoiceCommand,
    ManualPaymentMethod,
    RecordManualInvoicePaymentCommand,
    ReverseInvoicePaymentCommand,
    VoidStudentInvoiceCommand,
    major_to_minor,
)
from backend.modules.people.customer_support.payments.use_cases import (
    CustomerSupportPayments,
)

router = APIRouter(prefix="/payments")

ActorDependency = Annotated[ActorContext, Depends(get_actor_context)]


def get_payments_use_case(request: Request) -> CustomerSupportPayments:
    container: AppContainer = request.app.state.container
    return build_customer_support_payments(container)


PaymentsUseCaseDependency = Annotated[
    CustomerSupportPayments,
    Depends(get_payments_use_case),
]


class IssueInvoiceRequest(ApiModel):
    subject_id: int = Field(gt=0)
    description: str = Field(min_length=2, max_length=200)
    amount: float = Field(gt=0)
    due_date: date
    billing_period: date
    invoice_kind: InvoiceKind = InvoiceKind.MANUAL
    expected_student_version: int = Field(gt=0)


class AddPaidInvoiceRequest(IssueInvoiceRequest):
    method: ManualPaymentMethod
    paid_at: datetime
    reference: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)


class ManualInvoicePaymentRequest(ApiModel):
    amount: float = Field(gt=0)
    method: ManualPaymentMethod
    paid_at: datetime
    reference: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)
    expected_version: int = Field(gt=0)


class ReverseInvoicePaymentRequest(ApiModel):
    expected_invoice_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class VoidInvoiceRequest(ApiModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class BillingItemRequest(ApiModel):
    group_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    description: str = Field(default="", max_length=200)


class ConfigureBillingProfileRequest(ApiModel):
    billing_day: int = Field(ge=1, le=28)
    starts_on: date
    status: str = Field(default="active", pattern="^(active|paused|ended)$")
    items: list[BillingItemRequest] = Field(min_length=1, max_length=20)
    expected_version: int | None = Field(default=None, gt=0)


def _error(exc: Exception):
    if isinstance(exc, BillingError):
        return api_error(str(exc), code=exc.code, status_code=exc.status_code)
    if isinstance(exc, PermissionError):
        return api_error(str(exc), code="payment_scope_denied", status_code=403)
    if isinstance(exc, ValueError):
        return api_error(str(exc), code="invalid_payment_request", status_code=400)
    raise exc


@router.get(
    "/invoices",
    response_model=ApiSuccess[InvoicePage],
    operation_id="api_v1_customer_support_invoices",
)
def list_invoices(
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
    q: Annotated[str, Query(max_length=200)] = "",
    status: Annotated[str, Query(max_length=40)] = "all",
    origin: Annotated[str, Query(max_length=40)] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    try:
        return api_success(
            use_case.list_invoices(
                actor,
                query=q,
                status=status,
                origin=origin,
                limit=limit,
            )
        )
    except Exception as exc:
        return _error(exc)


@router.get(
    "/invoices/{invoice_id}",
    response_model=ApiSuccess[InvoiceDetail],
    operation_id="api_v1_customer_support_invoice_detail",
)
def get_invoice(
    invoice_id: int,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(use_case.get_invoice(actor, invoice_id))
    except Exception as exc:
        return _error(exc)


@router.post(
    "/students/{student_id}/invoices",
    response_model=ApiSuccess[InvoiceDetail],
    operation_id="api_v1_customer_support_issue_student_invoice",
)
def issue_student_invoice(
    student_id: int,
    payload: IssueInvoiceRequest,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(
            use_case.issue_invoice(
                actor,
                IssueStudentInvoiceCommand(
                    student_id=student_id,
                    subject_id=payload.subject_id,
                    description=payload.description,
                    amount_minor=major_to_minor(payload.amount),
                    due_date=payload.due_date,
                    billing_period=payload.billing_period,
                    invoice_kind=payload.invoice_kind,
                    expected_student_version=payload.expected_student_version,
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


@router.post(
    "/students/{student_id}/paid-invoices",
    response_model=ApiSuccess[InvoiceDetail],
    operation_id="api_v1_customer_support_add_paid_student_invoice",
)
def add_paid_student_invoice(
    student_id: int,
    payload: AddPaidInvoiceRequest,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(
            use_case.add_paid_invoice(
                actor,
                AddPaidStudentInvoiceCommand(
                    student_id=student_id,
                    subject_id=payload.subject_id,
                    description=payload.description,
                    amount_minor=major_to_minor(payload.amount),
                    due_date=payload.due_date,
                    billing_period=payload.billing_period,
                    invoice_kind=payload.invoice_kind,
                    expected_student_version=payload.expected_student_version,
                    method=payload.method,
                    paid_at=payload.paid_at,
                    reference=payload.reference,
                    reason=payload.reason,
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


@router.post(
    "/invoices/{invoice_id}/manual-payments",
    response_model=ApiSuccess[InvoiceDetail],
    operation_id="api_v1_customer_support_record_invoice_payment",
)
def record_manual_invoice_payment(
    invoice_id: int,
    payload: ManualInvoicePaymentRequest,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(
            use_case.record_manual_payment(
                actor,
                invoice_id,
                RecordManualInvoicePaymentCommand(
                    amount_minor=major_to_minor(payload.amount),
                    method=payload.method,
                    paid_at=payload.paid_at,
                    reference=payload.reference,
                    reason=payload.reason,
                    expected_version=payload.expected_version,
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


@router.post(
    "/invoice-payments/{payment_id}/reversal",
    response_model=ApiSuccess[InvoiceDetail],
    operation_id="api_v1_customer_support_reverse_invoice_payment",
)
def reverse_invoice_payment(
    payment_id: int,
    payload: ReverseInvoicePaymentRequest,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(
            use_case.reverse_payment(
                actor,
                payment_id,
                ReverseInvoicePaymentCommand(
                    expected_invoice_version=payload.expected_invoice_version,
                    reason=payload.reason,
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


@router.post(
    "/invoices/{invoice_id}/void",
    response_model=ApiSuccess[InvoiceDetail],
    operation_id="api_v1_customer_support_void_invoice",
)
def void_invoice(
    invoice_id: int,
    payload: VoidInvoiceRequest,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(
            use_case.void_invoice(
                actor,
                invoice_id,
                VoidStudentInvoiceCommand(
                    expected_version=payload.expected_version,
                    reason=payload.reason,
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


@router.get(
    "/students/{student_id}/billing-profile",
    response_model=ApiSuccess[BillingProfileResult | None],
    operation_id="api_v1_customer_support_billing_profile",
)
def get_billing_profile(
    student_id: int,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(use_case.get_billing_profile(actor, student_id))
    except Exception as exc:
        return _error(exc)


@router.put(
    "/students/{student_id}/billing-profile",
    response_model=ApiSuccess[BillingProfileResult],
    operation_id="api_v1_customer_support_configure_billing_profile",
)
def configure_billing_profile(
    student_id: int,
    payload: ConfigureBillingProfileRequest,
    actor: ActorDependency,
    use_case: PaymentsUseCaseDependency,
):
    try:
        return api_success(
            use_case.configure_billing_profile(
                actor,
                ConfigureBillingProfileCommand(
                    student_id=student_id,
                    billing_day=payload.billing_day,
                    starts_on=payload.starts_on,
                    status=payload.status,
                    items=[
                        BillingItemInput(
                            group_id=item.group_id,
                            amount_minor=major_to_minor(item.amount),
                            description=item.description,
                        )
                        for item in payload.items
                    ],
                    expected_version=payload.expected_version,
                ),
            )
        )
    except Exception as exc:
        return _error(exc)


__all__ = ["router"]
