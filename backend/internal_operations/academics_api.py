from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, get_current_user
from backend.core.http import ApiSuccess, api_success
from backend.internal_operations.schemas import (
    AdminAcademicContextPayload,
    AdminAcademicContextDelta,
    AdminCreateScheduleRequest,
    AdminEnrollmentGroupRequest,
    AdminEnrollmentStatusRequest,
    AdminEnrollmentUpdated,
    AdminLessonUpdateRequest,
    AdminLessonCancelRequest,
    AdminLessonUpdated,
    AdminRecordAttendanceRequest,
    AdminRecordCoinRequest,
    AdminRecordCreated,
    AdminRecordExamRequest,
    AdminRecordHomeworkRequest,
    AdminScheduleCreated,
    AdminCreateAcademicClassRequest,
    AdminUpdateGroupScheduleRequest,
    AdminCreateGroupStudentRequest,
    AdminStudentCreated,
)
from backend.modules.academics.operations import (
    create_schedule_from_payload,
    delete_group,
    get_group_gradebook,
    get_enrollment_gradebook_summary,
    list_admin_academic_context,
    move_enrollment_group_from_payload,
    record_attendance_from_payload,
    record_coin_from_payload,
    record_exam_from_payload,
    record_homework_from_payload,
    update_enrollment_status_from_payload,
    update_lesson_session_from_payload,
    cancel_lesson_session,
    recover_lesson_session,
    create_class_from_payload,
    upsert_group_schedule_from_payload,
    create_student_with_enrollment_from_payload,
)
from backend.internal_operations.page_cache import invalidate_admin_page_context_cache

router = APIRouter(prefix="/academic")


def _payload(model) -> dict[str, Any]:
    return model.model_dump(exclude_none=True)


@router.post(
    "/classes",
    operation_id="api_v1_admin_create_academic_class",
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
    "/schedules",
    operation_id="api_v1_admin_create_academic_schedule",
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


@router.put("/groups/{group_id}/schedule", operation_id="api_v1_admin_upsert_group_schedule", response_model=ApiSuccess[AdminScheduleCreated])
def upsert_group_schedule(group_id: int, payload: AdminUpdateGroupScheduleRequest):
    try:
        result = upsert_group_schedule_from_payload(group_id, _payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    context = list_admin_academic_context()
    return api_success({"schedule": result, "schedules": context.get("schedules", []), "sessions": context.get("sessions", []), "lessons": context.get("lessons", [])})


@router.post("/groups/{group_id}/students", operation_id="api_v1_admin_create_group_student", response_model=ApiSuccess[AdminStudentCreated])
def create_group_student(group_id: int, payload: AdminCreateGroupStudentRequest):
    try:
        student = create_student_with_enrollment_from_payload({"full_name": payload.full_name, "group_id": group_id})
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"student": student})


@router.get(
    "/context",
    operation_id="api_v1_admin_academic_context",
    response_model=ApiSuccess[AdminAcademicContextPayload],
)
def academic_context():
    return api_success(list_admin_academic_context(include_heavy=True))


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


@router.delete(
    "/groups/{group_id}",
    operation_id="api_v1_admin_delete_academic_group",
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
    operation_id="api_v1_admin_update_academic_enrollment_status",
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
    operation_id="api_v1_admin_move_academic_enrollment_group",
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
    operation_id="api_v1_admin_record_academic_attendance",
    response_model=ApiSuccess[dict[str, Any]],
)
def record_attendance(payload: AdminRecordAttendanceRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        record_id = record_attendance_from_payload(_payload(payload), user.staff_id)
        summary = get_enrollment_gradebook_summary(payload.enrollment_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id, "studentSummary": summary, "actorStaffId": user.staff_id})


@router.post(
    "/homework",
    operation_id="api_v1_admin_record_academic_homework",
    response_model=ApiSuccess[dict[str, Any]],
)
def record_homework(payload: AdminRecordHomeworkRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        record_id = record_homework_from_payload(_payload(payload), user.staff_id)
        summary = get_enrollment_gradebook_summary(payload.enrollment_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id, "studentSummary": summary, "actorStaffId": user.staff_id})


@router.patch(
    "/lessons/{lesson_session_id}",
    operation_id="api_v1_admin_update_academic_lesson",
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
    "/lessons/{lesson_session_id}/cancel",
    operation_id="api_v1_admin_cancel_academic_lesson",
    response_model=ApiSuccess[dict[str, Any]],
)
def cancel_lesson(lesson_session_id: int, payload: AdminLessonCancelRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        result = cancel_lesson_session(lesson_session_id, payload.reason, user.staff_id)
        gradebook = get_group_gradebook(result["groupId"], section="timetable")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({**result, "gradebook": gradebook})


@router.post(
    "/lessons/{lesson_session_id}/recover",
    operation_id="api_v1_admin_recover_academic_lesson",
    response_model=ApiSuccess[dict[str, Any]],
)
def recover_lesson(lesson_session_id: int, user: CurrentUser = Depends(get_current_user)):
    try:
        result = recover_lesson_session(lesson_session_id, user.staff_id)
        gradebook = get_group_gradebook(result["groupId"], section="timetable")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({**result, "gradebook": gradebook})


@router.post(
    "/exams",
    operation_id="api_v1_admin_record_academic_exam",
    response_model=ApiSuccess[dict[str, Any]],
)
def record_exam(payload: AdminRecordExamRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        record_id = record_exam_from_payload(_payload(payload), user.staff_id)
        summary = get_enrollment_gradebook_summary(payload.enrollment_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id, "studentSummary": summary, "actorStaffId": user.staff_id})


@router.post(
    "/coins",
    operation_id="api_v1_admin_record_academic_coins",
    response_model=ApiSuccess[AdminRecordCreated],
)
def record_coins(payload: AdminRecordCoinRequest):
    try:
        record_id = record_coin_from_payload(_payload(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return api_success({"id": record_id})
