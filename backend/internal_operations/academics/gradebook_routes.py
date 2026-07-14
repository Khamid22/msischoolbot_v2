"""System-admin routes for gradebook reads and academic record mutations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, get_current_user
from backend.core.api import ApiSuccess, api_success
from backend.internal_operations.academics.common import model_payload
from backend.modules.academics.assessments.service import record_exam_from_payload
from backend.modules.academics.attendance.service import record_attendance_from_payload
from backend.modules.academics.gradebook.homework import record_homework_from_payload
from backend.modules.academics.gradebook.rewards import record_coin_from_payload
from backend.modules.academics.gradebook.service import (
    get_enrollment_gradebook_summary,
    get_group_gradebook,
)
from backend.modules.academics.gradebook.trends import get_group_gradebook_trends
from backend.modules.academics.schemas import (
    AdminRecordAttendanceRequest,
    AdminRecordCoinRequest,
    AdminRecordCreated,
    AdminRecordExamRequest,
    AdminRecordHomeworkRequest,
)


router = APIRouter()


@router.get(
    "/gradebook",
    operation_id="api_v1_admin_academic_gradebook",
    response_model=ApiSuccess[dict[str, Any]],
)
def gradebook(
    group_id: int = 0,
    lesson_limit: int = 0,
    cursor: str = "",
    direction: str = "",
    anchor_date: str = "",
    month: str = "",
    section: str = "all",
):
    try:
        result = get_group_gradebook(
            group_id,
            lesson_limit=lesson_limit,
            lesson_cursor=cursor,
            lesson_direction=direction,
            anchor_date=anchor_date,
            lesson_month=month,
            section=section,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    result.pop("ok", None)
    return api_success(result)


@router.get(
    "/groups/{group_id}/gradebook-trends",
    operation_id="api_v1_admin_academic_group_gradebook_trends",
    response_model=ApiSuccess[dict[str, Any]],
)
def gradebook_trends(group_id: int, through: str, months: int = 6):
    try:
        result = get_group_gradebook_trends(group_id, through=through, months=months)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    return api_success(result)


def _record_response(record_id: int, enrollment_id: int, staff_id: int | None):
    return api_success(
        {
            "id": record_id,
            "studentSummary": get_enrollment_gradebook_summary(enrollment_id),
            "actorStaffId": staff_id,
        }
    )


@router.post(
    "/attendance",
    operation_id="api_v1_admin_record_academic_attendance",
    response_model=ApiSuccess[dict[str, Any]],
)
def record_attendance(
    payload: AdminRecordAttendanceRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        record_id = record_attendance_from_payload(model_payload(payload), user.staff_id)
        return _record_response(record_id, payload.enrollment_id, user.staff_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/homework",
    operation_id="api_v1_admin_record_academic_homework",
    response_model=ApiSuccess[dict[str, Any]],
)
def record_homework(
    payload: AdminRecordHomeworkRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        record_id = record_homework_from_payload(model_payload(payload), user.staff_id)
        return _record_response(record_id, payload.enrollment_id, user.staff_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/exams",
    operation_id="api_v1_admin_record_academic_exam",
    response_model=ApiSuccess[dict[str, Any]],
)
def record_exam(
    payload: AdminRecordExamRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        record_id = record_exam_from_payload(model_payload(payload), user.staff_id)
        return _record_response(record_id, payload.enrollment_id, user.staff_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/coins",
    operation_id="api_v1_admin_record_academic_coins",
    response_model=ApiSuccess[AdminRecordCreated],
)
def record_coins(payload: AdminRecordCoinRequest):
    try:
        record_id = record_coin_from_payload(model_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id})
