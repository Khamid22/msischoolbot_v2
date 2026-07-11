"""Admin complaints API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.http import ApiSuccess, api_success
from backend.internal_operations.schemas import (
    ComplaintList,
    ComplaintPayload,
    ComplaintReplyRequest,
    CreateComplaintRequest,
    UpdateComplaintRequest,
)
from backend.modules.complaints.service import (
    add_complaint_reply,
    create_complaint,
    get_complaint,
    list_complaints,
    update_complaint,
)
from backend.internal_operations.page_cache import invalidate_admin_page_context_cache
from backend.core.access import CurrentUser, get_current_user

router = APIRouter(prefix="/complaints")


@router.get("", operation_id="api_v1_admin_list_complaints", response_model=ApiSuccess[ComplaintList])
def list_all(parent_admin_id: int = 0):
    try:
        complaints = list_complaints(parent_admin_id)
    except (TypeError, ValueError):
        complaints = list_complaints(0)
    return api_success({"complaints": complaints})


@router.post("", operation_id="api_v1_admin_create_complaint", response_model=ApiSuccess[ComplaintPayload])
def create(payload: CreateComplaintRequest):
    payload_data = payload.model_dump(exclude_none=True)
    parent_admin_id = payload.parent_admin_id
    student_row_id = payload.student_row_id or payload.student_id
    try:
        complaint = create_complaint(parent_admin_id, student_row_id, payload_data)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"complaint": complaint})


@router.get("/{complaint_id}", operation_id="api_v1_admin_get_complaint", response_model=ApiSuccess[ComplaintPayload])
def get_one(complaint_id: int):
    complaint = get_complaint(complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint was not found.")
    return api_success({"complaint": complaint})


@router.patch("/{complaint_id}", operation_id="api_v1_admin_update_complaint", response_model=ApiSuccess[ComplaintPayload])
def update(complaint_id: int, payload: UpdateComplaintRequest):
    try:
        complaint = update_complaint(complaint_id, payload.model_dump(exclude_none=True))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint was not found.")
    invalidate_admin_page_context_cache()
    return api_success({"complaint": complaint})


@router.post(
    "/{complaint_id}/replies",
    operation_id="api_v1_admin_reply_complaint",
    response_model=ApiSuccess[ComplaintPayload],
)
def reply(
    complaint_id: int,
    payload: ComplaintReplyRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        complaint = add_complaint_reply(
            complaint_id,
            payload.model_dump(exclude_none=True),
            author_role=user.role or "admin",
            author_login=user.login,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint was not found.")
    invalidate_admin_page_context_cache()
    return api_success({"complaint": complaint})
