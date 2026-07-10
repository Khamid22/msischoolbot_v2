"""Admin student-payment API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.http import ApiSuccess, api_success
from backend.modules.admin.schemas import (
    CreateStudentPaymentRequest,
    MarkStudentPaymentRequest,
    StudentPaymentPayload,
)
from backend.modules.payments.service import (
    create_student_payment,
    delete_student_payment,
    list_student_payments,
    set_student_payment_paid,
    summarize_payment_records,
)
from backend.modules.admin.page_cache import invalidate_admin_page_context_cache
from backend.core.access import CurrentUser, get_current_user

router = APIRouter()


@router.get(
    "/students/{student_row_id}/payments",
    operation_id="api_v1_admin_list_student_payments",
    response_model=ApiSuccess[StudentPaymentPayload],
)
def list_for_student(student_row_id: int):
    payments = list_student_payments(student_row_id)
    return api_success({"payments": payments, "summary": summarize_payment_records(payments)})


@router.post(
    "/students/{student_row_id}/payments",
    operation_id="api_v1_admin_create_student_payment",
    response_model=ApiSuccess[StudentPaymentPayload],
)
def create_for_student(
    student_row_id: int,
    payload: CreateStudentPaymentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = create_student_payment(
            student_row_id,
            payload.model_dump(exclude_none=True),
            created_by_admin_id=user.admin_id or 0,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({**result, "summary": summarize_payment_records(result["payments"])})


@router.patch(
    "/student-payments/{payment_id}",
    operation_id="api_v1_admin_mark_student_payment",
    response_model=ApiSuccess[StudentPaymentPayload],
)
def mark_paid(payment_id: int, payload: MarkStudentPaymentRequest):
    try:
        result = set_student_payment_paid(
            payment_id,
            paid=payload.paid,
            paid_at=payload.paid_at,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Payment record was not found.")
    invalidate_admin_page_context_cache()
    return api_success({**result, "summary": summarize_payment_records(result["payments"])})


@router.delete(
    "/student-payments/{payment_id}",
    operation_id="api_v1_admin_delete_student_payment",
    response_model=ApiSuccess[StudentPaymentPayload],
)
def delete(payment_id: int):
    try:
        result = delete_student_payment(payment_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Payment record was not found.")
    invalidate_admin_page_context_cache()
    return api_success({**result, "summary": summarize_payment_records(result["payments"])})
