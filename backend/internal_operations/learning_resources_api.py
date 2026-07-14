"""Admin resources API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.http import ApiSuccess, api_success
from backend.internal_operations.schemas import AdminResourceList, AdminResourceUploadProgress
from backend.modules.academics.resources.service import list_resources
from backend.modules.academics.resources.upload_progress import (
    get_upload_events,
    normalize_upload_id,
)

router = APIRouter(prefix="/resources")
progress_router = APIRouter(prefix="/resource-upload-progress")


@progress_router.get(
    "/{upload_id}",
    operation_id="api_v1_admin_resource_upload_progress",
    response_model=ApiSuccess[AdminResourceUploadProgress],
)
def resource_upload_progress(upload_id: str, after_seq: int = 0):
    normalized_upload_id = normalize_upload_id(upload_id)
    if not normalized_upload_id:
        raise HTTPException(status_code=400, detail="Invalid upload id.")

    events = get_upload_events(normalized_upload_id, after_seq=max(0, after_seq))
    latest_seq = max(0, after_seq)
    done = False
    for event in events:
        latest_seq = max(latest_seq, int(event.get("seq", latest_seq) or latest_seq))
        if bool(event.get("done")) or bool(event.get("error")):
            done = True

    return api_success(
        {
            "events": events,
            "latest_seq": latest_seq,
            "done": done,
        }
    )


@router.get(
    "",
    operation_id="api_v1_admin_list_resources",
    response_model=ApiSuccess[AdminResourceList],
)
def list_all_resources():
    return api_success({"resources": list_resources(include_inactive=True)})
