"""Admin students API v1 routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.core.http import ApiSuccess, api_success
from backend.modules.admin.schemas import (
    AdminCreateStudentRequest,
    AdminParentInviteCreated,
    AdminStudentCreated,
    AdminStudentsList,
)
from backend.modules.parents.service import create_parent_invite_code
from backend.modules.students.service import get_admin_student_profile, list_students_for_admin
from backend.modules.academics.operations import create_student_with_enrollment_from_payload
from backend.modules.admin.page_cache import invalidate_admin_page_context_cache
from backend.core.access import CurrentUser, get_current_user

router = APIRouter(prefix="/students")


def _request_public_base_url(request: Request) -> str:
    proto = str(request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    if not proto:
        proto = "https" if str(request.headers.get("x-forwarded-ssl", "")).lower() == "on" else "http"
    host = str(request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    return f"{proto}://{host}".rstrip("/") if host else ""


def _telegram_parent_invite_url(code: str) -> str:
    bot_username = (
        os.environ.get("TELEGRAM_BOT_USERNAME")
        or os.environ.get("BOT_USERNAME")
        or ""
    )
    bot_username = str(bot_username).strip().lstrip("@")
    if not bot_username:
        return ""
    return f"https://t.me/{bot_username}?start=parent_{code}"


@router.get(
    "",
    operation_id="api_v1_admin_list_students",
    response_model=ApiSuccess[AdminStudentsList],
)
def list_students(school: str = "all"):
    school_filter = str(school or "all").strip().casefold()
    if school_filter not in {"all", "school5", "sehriyo"}:
        school_filter = "all"
    return api_success({"students": list_students_for_admin(school_filter=school_filter)})


@router.post(
    "",
    operation_id="api_v1_admin_create_student",
    response_model=ApiSuccess[AdminStudentCreated],
)
def create_student(payload: AdminCreateStudentRequest):
    try:
        result = create_student_with_enrollment_from_payload(payload.model_dump())
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"student": result})


@router.post(
    "/{student_row_id}/parent-invite",
    operation_id="api_v1_admin_create_parent_invite",
    response_model=ApiSuccess[AdminParentInviteCreated],
)
def create_parent_invite(
    student_row_id: int,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    profile = get_admin_student_profile(student_row_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Selected student was not found.")

    issued_by = int(user.admin_id or 0)
    invite_code = create_parent_invite_code(student_row_id, issued_by=issued_by)
    invite_path = f"/parent/invite/{invite_code}"
    base_url = _request_public_base_url(request)
    web_invite_url = f"{base_url}{invite_path}" if base_url else invite_path
    telegram_invite_url = _telegram_parent_invite_url(invite_code)
    invite_url = telegram_invite_url or web_invite_url
    return api_success(
        {
            "invite_code": invite_code,
            "inviteCode": invite_code,
            "invite_url": invite_url,
            "inviteUrl": invite_url,
            "telegram_invite_url": telegram_invite_url,
            "telegramInviteUrl": telegram_invite_url,
            "web_invite_url": web_invite_url,
            "webInviteUrl": web_invite_url,
        }
    )
