"""Academic Director academic workspace API v1 routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.http import ApiSuccess, api_success
from backend.internal_operations.schemas import (
    AdminAcademicContextDelta,
    AdminAcademicContextPayload,
    AdminCreateAcademicGroupRequest,
    AdminCreateAcademicClassRequest,
    AdminCreateAcademicSchoolRequest,
    AdminCreateScheduleRequest,
    AdminEnrollmentGroupRequest,
    AdminEnrollmentStatusRequest,
    AdminEnrollmentUpdated,
    AdminLessonUpdateRequest,
    AdminLessonUpdated,
    AdminRecordAttendanceRequest,
    AdminRecordCoinRequest,
    AdminRecordCreated,
    AdminRecordExamRequest,
    AdminRecordHomeworkRequest,
    AdminScheduleCreated,
)
from backend.internal_operations.page_cache import invalidate_admin_page_context_cache
from backend.modules.academics.operations import (
    create_group_from_payload,
    create_class_from_payload,
    create_schedule_from_payload,
    create_school_from_payload,
    delete_group,
    get_group_gradebook,
    list_admin_academic_context,
    move_enrollment_group_from_payload,
    record_attendance_from_payload,
    record_coin_from_payload,
    record_exam_from_payload,
    record_homework_from_payload,
    update_enrollment_status_from_payload,
    update_lesson_session_from_payload,
)

router = APIRouter(prefix="/academic")


def _payload(model) -> dict[str, Any]:
    return model.model_dump(exclude_none=True)


@router.get(
    "/context",
    operation_id="api_v1_academic_director_academic_context",
    response_model=ApiSuccess[AdminAcademicContextPayload],
)
def academic_context():
    return api_success(list_admin_academic_context(include_heavy=True))


@router.post(
    "/schools",
    operation_id="api_v1_academic_director_create_academic_school",
    response_model=ApiSuccess[AdminAcademicContextPayload],
)
def create_academic_school(payload: AdminCreateAcademicSchoolRequest):
    try:
        create_school_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(list_admin_academic_context(include_heavy=True))


@router.post(
    "/classes",
    operation_id="api_v1_academic_director_create_academic_class",
    response_model=ApiSuccess[AdminAcademicContextPayload],
)
def create_academic_class(payload: AdminCreateAcademicClassRequest):
    try:
        create_class_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(list_admin_academic_context(include_heavy=True))


@router.post(
    "/groups",
    operation_id="api_v1_academic_director_create_academic_group",
    response_model=ApiSuccess[AdminAcademicContextPayload],
)
def create_academic_group(payload: AdminCreateAcademicGroupRequest):
    try:
        create_group_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(list_admin_academic_context(include_heavy=True))


@router.post(
    "/schedules",
    operation_id="api_v1_academic_director_create_academic_schedule",
    response_model=ApiSuccess[AdminScheduleCreated],
)
def create_schedule(payload: AdminCreateScheduleRequest):
    try:
        result = create_schedule_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    academic_context = list_admin_academic_context()
    return api_success(
        {
            "schedule": result,
            "schedules": academic_context.get("schedules", []),
            "sessions": academic_context.get("sessions", []),
            "lessons": academic_context.get("lessons", []),
        }
    )


@router.get(
    "/gradebook",
    operation_id="api_v1_academic_director_academic_gradebook",
    response_model=ApiSuccess[dict[str, Any]],
)
def gradebook(group_id: int = 0):
    try:
        result = get_group_gradebook(group_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    result.pop("ok", None)
    return api_success(result)


@router.delete(
    "/groups/{group_id}",
    operation_id="api_v1_academic_director_delete_academic_group",
    response_model=ApiSuccess[AdminAcademicContextDelta],
)
def delete_academic_group(group_id: int):
    try:
        deleted = delete_group(group_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")

    invalidate_admin_page_context_cache()
    academic_context = list_admin_academic_context()
    return api_success(
        {
            "group": deleted,
            "groups": academic_context.get("groups", []),
            "enrollments": academic_context.get("enrollments", []),
            "schedules": academic_context.get("schedules", []),
            "sessions": academic_context.get("sessions", []),
            "lessons": academic_context.get("lessons", []),
        }
    )


@router.patch(
    "/enrollments/{enrollment_id}/status",
    operation_id="api_v1_academic_director_update_academic_enrollment_status",
    response_model=ApiSuccess[AdminEnrollmentUpdated],
)
def update_enrollment_status(enrollment_id: int, payload: AdminEnrollmentStatusRequest):
    try:
        result = update_enrollment_status_from_payload(enrollment_id, _payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"enrollment": result})


@router.patch(
    "/enrollments/{enrollment_id}/group",
    operation_id="api_v1_academic_director_move_academic_enrollment_group",
    response_model=ApiSuccess[AdminEnrollmentUpdated],
)
def move_enrollment_group(enrollment_id: int, payload: AdminEnrollmentGroupRequest):
    try:
        result = move_enrollment_group_from_payload(enrollment_id, _payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    academic_context = list_admin_academic_context()
    return api_success({"enrollment": result, "groups": academic_context.get("groups", [])})


@router.post(
    "/attendance",
    operation_id="api_v1_academic_director_record_academic_attendance",
    response_model=ApiSuccess[AdminRecordCreated],
)
def record_attendance(payload: AdminRecordAttendanceRequest):
    try:
        record_id = record_attendance_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id})


@router.post(
    "/homework",
    operation_id="api_v1_academic_director_record_academic_homework",
    response_model=ApiSuccess[AdminRecordCreated],
)
def record_homework(payload: AdminRecordHomeworkRequest):
    try:
        record_id = record_homework_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id})


@router.patch(
    "/lessons/{lesson_session_id}",
    operation_id="api_v1_academic_director_update_academic_lesson",
    response_model=ApiSuccess[AdminLessonUpdated],
)
def update_lesson(lesson_session_id: int, payload: AdminLessonUpdateRequest):
    try:
        lesson = update_lesson_session_from_payload(lesson_session_id, _payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"lesson": lesson})


@router.post(
    "/exams",
    operation_id="api_v1_academic_director_record_academic_exam",
    response_model=ApiSuccess[AdminRecordCreated],
)
def record_exam(payload: AdminRecordExamRequest):
    try:
        record_id = record_exam_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id})


@router.post(
    "/coins",
    operation_id="api_v1_academic_director_record_academic_coins",
    response_model=ApiSuccess[AdminRecordCreated],
)
def record_coins(payload: AdminRecordCoinRequest):
    try:
        record_id = record_coin_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id})


__all__ = ["router"]
