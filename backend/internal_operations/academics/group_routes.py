"""System-admin routes for groups, enrollment, archival, and purge."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, get_current_user
from backend.core.api import ApiSuccess, api_success
from backend.internal_operations.academics.common import model_payload
from backend.modules.academics.groups.operations import (
    create_student_with_enrollment_from_payload,
    delete_group,
    list_admin_academic_context,
    move_enrollment_group_from_payload,
    permanently_purge_group,
    preview_group_purge,
    update_enrollment_status_from_payload,
)
from backend.modules.academics.groups.read_service import (
    get_group_summary,
    list_group_page,
)
from backend.modules.academics.schemas import (
    AdminAcademicContextDelta,
    AdminAcademicContextPayload,
    AdminCreateGroupStudentRequest,
    AdminEnrollmentGroupRequest,
    AdminEnrollmentStatusRequest,
    AdminEnrollmentUpdated,
    AdminPurgeGroupRequest,
    AdminStudentCreated,
)
from backend.platform.admin_page_cache import invalidate_admin_page_context_cache


router = APIRouter()


@router.post(
    "/groups/{group_id}/students",
    operation_id="api_v1_admin_create_group_student",
    response_model=ApiSuccess[AdminStudentCreated],
)
def create_group_student(group_id: int, payload: AdminCreateGroupStudentRequest):
    try:
        student = create_student_with_enrollment_from_payload(
            {"full_name": payload.full_name, "group_id": group_id}
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"student": student})


@router.get(
    "/context",
    operation_id="api_v1_admin_academic_context",
    response_model=ApiSuccess[AdminAcademicContextPayload],
    deprecated=True,
)
def academic_context():
    return api_success(list_admin_academic_context(include_heavy=True))


@router.get(
    "/groups",
    operation_id="api_v1_admin_list_academic_groups",
    response_model=ApiSuccess[dict[str, Any]],
)
def list_academic_groups(
    school_id: int = 0,
    subject_id: int = 0,
    query: str = "",
    cursor: str = "",
    limit: int = 50,
):
    try:
        return api_success(
            list_group_page(
                school_id=school_id,
                subject_id=subject_id,
                query=query,
                cursor=cursor,
                limit=limit,
            )
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/groups/{group_id}/summary",
    operation_id="api_v1_admin_academic_group_summary",
    response_model=ApiSuccess[dict[str, Any]],
)
def academic_group_summary(group_id: int):
    try:
        summary = get_group_summary(group_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not summary:
        raise HTTPException(status_code=404, detail="Group not found")
    return api_success(summary)


@router.delete(
    "/groups/{group_id}",
    operation_id="api_v1_admin_delete_academic_group",
    response_model=ApiSuccess[AdminAcademicContextDelta],
)
def delete_academic_group(
    group_id: int,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        deleted = delete_group(
            group_id,
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")

    invalidate_admin_page_context_cache()
    academic_context = list_admin_academic_context(include_heavy=False)
    return api_success(
        {
            "group": deleted,
            "groups": academic_context.get("groups", []),
            "entity": deleted,
            "affected_ids": [int(deleted["id"])],
            "revision": f"group:{deleted['id']}:archived",
        }
    )


@router.get(
    "/groups/{group_id}/purge-preview",
    operation_id="api_v1_admin_preview_academic_group_purge",
    response_model=ApiSuccess[dict[str, Any]],
)
def preview_academic_group_purge(
    group_id: int,
    user: CurrentUser = Depends(get_current_user),
):
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Owner access is required.")
    try:
        preview = preview_group_purge(group_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not preview:
        raise HTTPException(status_code=404, detail="Group not found")
    return api_success(preview)


@router.post(
    "/groups/{group_id}/purge",
    operation_id="api_v1_admin_purge_academic_group",
    response_model=ApiSuccess[dict[str, Any]],
)
def purge_academic_group(
    group_id: int,
    payload: AdminPurgeGroupRequest,
    user: CurrentUser = Depends(get_current_user),
):
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Owner access is required.")
    try:
        deleted = permanently_purge_group(
            group_id,
            payload.confirmation,
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    invalidate_admin_page_context_cache()
    return api_success(
        {
            "entity": deleted,
            "affected_ids": [int(deleted["id"])],
            "revision": f"group:{deleted['id']}:purged",
        }
    )


@router.patch(
    "/enrollments/{enrollment_id}/status",
    operation_id="api_v1_admin_update_academic_enrollment_status",
    response_model=ApiSuccess[AdminEnrollmentUpdated],
)
def update_enrollment_status(
    enrollment_id: int,
    payload: AdminEnrollmentStatusRequest,
):
    try:
        result = update_enrollment_status_from_payload(
            enrollment_id,
            model_payload(payload),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"enrollment": result})


@router.patch(
    "/enrollments/{enrollment_id}/group",
    operation_id="api_v1_admin_move_academic_enrollment_group",
    response_model=ApiSuccess[AdminEnrollmentUpdated],
)
def move_enrollment_group(
    enrollment_id: int,
    payload: AdminEnrollmentGroupRequest,
):
    try:
        result = move_enrollment_group_from_payload(
            enrollment_id,
            model_payload(payload),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    academic_context = list_admin_academic_context(include_heavy=False)
    return api_success(
        {"enrollment": result, "groups": academic_context.get("groups", [])}
    )
