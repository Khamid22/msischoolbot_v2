"""Customer Support records API."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from backend.core.access import CurrentUser, get_current_user, require_role
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.people.customer_support import contracts as service
from backend.modules.people.customer_support.schemas import (
    CreatePaymentRequest,
    CreateStudentRequest,
    LifecycleRequest,
    ParentChildRequest,
    SettlementRequest,
    UpdateParentRequest,
    UpdatePaymentRequest,
    UpdateStudentRequest,
    VersionOnlyRequest,
    VoidPaymentRequest,
)
from backend.modules.people.customer_support.workspace.teachers_api import (
    router as teachers_router,
)


router = APIRouter(
    prefix="/customer-support",
    dependencies=[Depends(require_role("customer_support"))],
)
router.include_router(teachers_router)


def _actor(user: CurrentUser) -> service.SupportActor:
    return service.SupportActor(
        staff_id=user.staff_id,
        account_id=user.account_id,
        login=user.login,
    )


def _payload(model) -> dict[str, Any]:
    return model.model_dump(exclude_none=True, by_alias=True)


def _call(callback, *args, **kwargs):
    try:
        return api_success(callback(*args, **kwargs))
    except service.CustomerSupportError as exc:
        return api_error(
            str(exc),
            code=exc.code,
            details=exc.details,
            status_code=exc.status_code,
        )


@router.get(
    "/context",
    operation_id="api_v1_customer_support_context",
    response_model=ApiSuccess[dict[str, Any]],
)
def get_context(user: CurrentUser = Depends(get_current_user)):
    return _call(service.context, _actor(user))


@router.get(
    "/records",
    operation_id="api_v1_customer_support_records",
    response_model=ApiSuccess[dict[str, Any]],
)
def get_records(
    q: str = Query(default="", max_length=200),
    record_type: str = Query(default="all", alias="type"),
    status: str = Query(default="all"),
    school_id: int | None = Query(default=None, alias="schoolId"),
    exclude_parent_id: int | None = Query(default=None, gt=0, alias="excludeParentId"),
    cursor: str = Query(default="", max_length=500),
    limit: int = Query(default=25, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.search_records,
        _actor(user),
        query=q,
        kind=record_type,
        status=status,
        school_id=school_id,
        exclude_parent_id=exclude_parent_id,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/students/{student_id}",
    operation_id="api_v1_customer_support_student",
    response_model=ApiSuccess[dict[str, Any]],
)
def get_student(student_id: int, user: CurrentUser = Depends(get_current_user)):
    return _call(service.student_detail, _actor(user), student_id)


@router.post(
    "/students",
    operation_id="api_v1_customer_support_create_student",
    response_model=ApiSuccess[dict[str, Any]],
)
def create_student(payload: CreateStudentRequest, user: CurrentUser = Depends(get_current_user)):
    return _call(service.create_student, _actor(user), _payload(payload))


@router.patch(
    "/students/{student_id}",
    operation_id="api_v1_customer_support_update_student",
    response_model=ApiSuccess[dict[str, Any]],
)
def update_student(
    student_id: int,
    payload: UpdateStudentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(service.update_student, _actor(user), student_id, _payload(payload))


@router.post(
    "/students/{student_id}/archive",
    operation_id="api_v1_customer_support_archive_student",
    response_model=ApiSuccess[dict[str, Any]],
)
def archive_student(
    student_id: int,
    payload: LifecycleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.set_student_lifecycle,
        _actor(user),
        student_id,
        expected_version=payload.expected_version,
        active=False,
        reason=payload.reason,
    )


@router.post(
    "/students/{student_id}/reactivate",
    operation_id="api_v1_customer_support_reactivate_student",
    response_model=ApiSuccess[dict[str, Any]],
)
def reactivate_student(
    student_id: int,
    payload: LifecycleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.set_student_lifecycle,
        _actor(user),
        student_id,
        expected_version=payload.expected_version,
        active=True,
        reason=payload.reason,
    )


@router.post(
    "/students/{student_id}/reset-access",
    operation_id="api_v1_customer_support_reset_student_access",
    response_model=ApiSuccess[dict[str, Any]],
)
def reset_student_access(
    student_id: int,
    payload: VersionOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.reset_student_access,
        _actor(user),
        student_id,
        expected_version=payload.expected_version,
    )


@router.get(
    "/parents/{parent_id}",
    operation_id="api_v1_customer_support_parent",
    response_model=ApiSuccess[dict[str, Any]],
)
def get_parent(parent_id: int, user: CurrentUser = Depends(get_current_user)):
    return _call(service.parent_detail, _actor(user), parent_id)


@router.patch(
    "/parents/{parent_id}",
    operation_id="api_v1_customer_support_update_parent",
    response_model=ApiSuccess[dict[str, Any]],
)
def update_parent(
    parent_id: int,
    payload: UpdateParentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(service.update_parent, _actor(user), parent_id, _payload(payload))


@router.post(
    "/parents/{parent_id}/deactivate",
    operation_id="api_v1_customer_support_deactivate_parent",
    response_model=ApiSuccess[dict[str, Any]],
)
def deactivate_parent(
    parent_id: int,
    payload: LifecycleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.set_parent_lifecycle,
        _actor(user),
        parent_id,
        expected_version=payload.expected_version,
        active=False,
        reason=payload.reason,
    )


@router.post(
    "/parents/{parent_id}/reactivate",
    operation_id="api_v1_customer_support_reactivate_parent",
    response_model=ApiSuccess[dict[str, Any]],
)
def reactivate_parent(
    parent_id: int,
    payload: LifecycleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.set_parent_lifecycle,
        _actor(user),
        parent_id,
        expected_version=payload.expected_version,
        active=True,
        reason=payload.reason,
    )


@router.post(
    "/parents/{parent_id}/children",
    operation_id="api_v1_customer_support_link_child",
    response_model=ApiSuccess[dict[str, Any]],
)
def link_child(
    parent_id: int,
    payload: ParentChildRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.link_parent_child,
        _actor(user),
        parent_id,
        payload.student_id,
        expected_version=payload.expected_version,
    )


@router.delete(
    "/parents/{parent_id}/children/{student_id}",
    operation_id="api_v1_customer_support_unlink_child",
    response_model=ApiSuccess[dict[str, Any]],
)
def unlink_child(
    parent_id: int,
    student_id: int,
    reason: str = Query(min_length=2, max_length=1000),
    expected_version: int = Query(gt=0, alias="expectedVersion"),
    user: CurrentUser = Depends(get_current_user),
):
    return _call(
        service.unlink_parent_child,
        _actor(user),
        parent_id,
        student_id,
        reason,
        expected_version=expected_version,
    )


def _public_base_url(request: Request) -> str:
    proto = str(request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    if not proto:
        proto = (
            "https"
            if str(request.headers.get("x-forwarded-ssl", "")).casefold() == "on"
            else "http"
        )
    host = (
        str(request.headers.get("x-forwarded-host") or request.headers.get("host") or "")
        .split(",")[0]
        .strip()
    )
    return f"{proto}://{host}".rstrip("/") if host else ""


@router.post(
    "/students/{student_id}/parent-invites",
    operation_id="api_v1_customer_support_parent_invite",
    response_model=ApiSuccess[dict[str, Any]],
)
def create_parent_invite(
    student_id: int,
    payload: VersionOnlyRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = service.create_parent_invite(
            _actor(user), student_id, expected_version=payload.expected_version
        )
    except service.CustomerSupportError as exc:
        return api_error(str(exc), code=exc.code, details=exc.details, status_code=exc.status_code)
    code = str(result["inviteCode"])
    web_path = f"/parent/invite/{code}"
    base = _public_base_url(request)
    username = (
        str(os.environ.get("TELEGRAM_BOT_USERNAME") or os.environ.get("BOT_USERNAME") or "")
        .strip()
        .lstrip("@")
    )
    telegram_url = f"https://t.me/{username}?start=parent_{code}" if username else ""
    return api_success(
        {
            **result,
            "webInviteUrl": f"{base}{web_path}" if base else web_path,
            "telegramInviteUrl": telegram_url,
            "inviteUrl": telegram_url or (f"{base}{web_path}" if base else web_path),
        }
    )


@router.get(
    "/students/{student_id}/payments",
    operation_id="api_v1_customer_support_payments",
    response_model=ApiSuccess[dict[str, Any]],
)
def get_payments(student_id: int, user: CurrentUser = Depends(get_current_user)):
    return _call(service.list_student_payments, _actor(user), student_id)


@router.post(
    "/students/{student_id}/payments",
    operation_id="api_v1_customer_support_create_payment",
    response_model=ApiSuccess[dict[str, Any]],
)
def create_payment(
    student_id: int,
    payload: CreatePaymentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(service.create_payment, _actor(user), student_id, _payload(payload))


@router.patch(
    "/payments/{payment_id}",
    operation_id="api_v1_customer_support_update_payment",
    response_model=ApiSuccess[dict[str, Any]],
)
def update_payment(
    payment_id: int,
    payload: UpdatePaymentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(service.update_payment, _actor(user), payment_id, _payload(payload))


@router.post(
    "/payments/{payment_id}/settlement",
    operation_id="api_v1_customer_support_settle_payment",
    response_model=ApiSuccess[dict[str, Any]],
)
def settle_payment(
    payment_id: int,
    payload: SettlementRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(service.settle_payment, _actor(user), payment_id, _payload(payload))


@router.post(
    "/payments/{payment_id}/void",
    operation_id="api_v1_customer_support_void_payment",
    response_model=ApiSuccess[dict[str, Any]],
)
def void_payment(
    payment_id: int,
    payload: VoidPaymentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return _call(service.void_payment, _actor(user), payment_id, _payload(payload))


__all__ = ["router"]
