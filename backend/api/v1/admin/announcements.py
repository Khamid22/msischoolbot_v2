"""Admin announcements API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api import ApiSuccess, api_success
from backend.api.v1.admin.schemas import CreateAnnouncementRequest, UpdateAnnouncementRequest
from backend.domains.announcements.service import (
    create_announcement,
    delete_announcement,
    list_announcements,
    update_announcement,
)
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.security import CurrentUser, get_current_user

router = APIRouter(prefix="/announcements")


@router.get("", operation_id="api_v1_admin_list_announcements", response_model=ApiSuccess[dict])
def list_all():
    return api_success({"announcements": list_announcements()})


@router.post("", operation_id="api_v1_admin_create_announcement", response_model=ApiSuccess[dict])
def create(
    payload: CreateAnnouncementRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        item = create_announcement(
            title=payload.title,
            body=payload.body,
            audience=payload.audience,
            priority=payload.priority,
            status=payload.status,
            pinned=payload.pinned,
            author=user.login or "Admin",
            scheduled_at=payload.scheduled_at,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"announcement": item})


@router.patch(
    "/{announcement_id}",
    operation_id="api_v1_admin_update_announcement",
    response_model=ApiSuccess[dict],
)
def update(announcement_id: int, payload: UpdateAnnouncementRequest):
    try:
        item = update_announcement(
            announcement_id,
            title=payload.title,
            body=payload.body,
            audience=payload.audience,
            priority=payload.priority,
            status=payload.status,
            pinned=payload.pinned,
            scheduled_at=payload.scheduled_at,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"announcement": item})


@router.delete(
    "/{announcement_id}",
    operation_id="api_v1_admin_delete_announcement",
    response_model=ApiSuccess[None],
)
def delete(announcement_id: int):
    if not delete_announcement(announcement_id):
        raise HTTPException(status_code=404, detail="Announcement not found.")
    invalidate_admin_page_context_cache()
    return api_success()
