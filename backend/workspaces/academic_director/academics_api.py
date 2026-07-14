"""Academic Director academic workspace API v1 routes."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, get_current_user
from backend.core.http import ApiSuccess, api_success
from backend.modules.academics.schemas import (
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
    AdminLessonCancelRequest,
    AdminLessonRecoverRequest,
    AdminLessonUpdated,
    AdminRecordAttendanceRequest,
    AdminRecordCoinRequest,
    AdminRecordCreated,
    AdminRecordExamRequest,
    AdminRecordHomeworkRequest,
    AdminScheduleCreated,
    AdminUpdateGroupScheduleRequest,
    AdminCreateGroupStudentRequest,
    AdminStudentCreated,
)
from backend.internal_operations.page_cache import invalidate_admin_page_context_cache
from backend.modules.academics.operations import (
    AcademicConflictError,
    create_group_from_payload,
    create_class_from_payload,
    create_schedule_from_payload,
    create_school_from_payload,
    delete_group,
    get_group_gradebook,
    get_group_gradebook_trends,
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
    upsert_group_schedule_from_payload,
    create_student_with_enrollment_from_payload,
)
from backend.modules.academics.read_service import (
    get_group_summary,
    list_group_page,
    list_group_schedule_rows,
    list_program_item_page,
    list_program_page,
    list_timetable_range,
)

router = APIRouter(prefix="/academic")


def _payload(model) -> dict[str, Any]:
    return model.model_dump(exclude_none=True)


@router.get(
    "/context",
    operation_id="api_v1_academic_director_academic_context",
    response_model=ApiSuccess[AdminAcademicContextPayload],
    deprecated=True,
)
def academic_context():
    return api_success(list_admin_academic_context(include_heavy=True))


@router.get(
    "/groups",
    operation_id="api_v1_academic_director_list_academic_groups",
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
    operation_id="api_v1_academic_director_academic_group_summary",
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


@router.get(
    "/programs",
    operation_id="api_v1_academic_director_list_academic_programs",
    response_model=ApiSuccess[dict[str, Any]],
)
def list_academic_programs(cursor: str = "", limit: int = 50):
    try:
        return api_success(list_program_page(cursor=cursor, limit=limit))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/programs/{program_id}/items",
    operation_id="api_v1_academic_director_list_academic_program_items",
    response_model=ApiSuccess[dict[str, Any]],
)
def list_academic_program_items(
    program_id: int, cursor: str = "", limit: int = 100
):
    try:
        return api_success(
            list_program_item_page(program_id, cursor=cursor, limit=limit)
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/timetable",
    operation_id="api_v1_academic_director_academic_timetable_range",
    response_model=ApiSuccess[dict[str, Any]],
)
def academic_timetable_range(
    date_from: str,
    date_to: str,
    group_id: int = 0,
    school_id: int = 0,
):
    try:
        return api_success(
            list_timetable_range(
                start_date=date_from,
                end_date=date_to,
                group_id=group_id,
                school_id=school_id,
            )
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/groups/{group_id}/timetable",
    operation_id="api_v1_academic_director_group_timetable_range",
    response_model=ApiSuccess[dict[str, Any]],
)
def group_timetable_range(group_id: int, date_from: str, date_to: str):
    try:
        return api_success(
            list_timetable_range(
                start_date=date_from, end_date=date_to, group_id=group_id
            )
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
    return api_success(list_admin_academic_context(include_heavy=False))


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
    return api_success(list_admin_academic_context(include_heavy=False))


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
    return api_success(list_admin_academic_context(include_heavy=False))


@router.post(
    "/schedules",
    operation_id="api_v1_academic_director_create_academic_schedule",
    response_model=ApiSuccess[AdminScheduleCreated],
)
def create_schedule(
    payload: AdminCreateScheduleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = create_schedule_from_payload(
            _payload(payload),
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    timetable = list_timetable_range(
        start_date=result.get("firstLessonDate", ""),
        end_date=min(
            date.fromisoformat(result["predictedEndDate"]),
            date.fromisoformat(result["firstLessonDate"]) + timedelta(days=62),
        ).isoformat(),
        group_id=payload.group_id,
    )
    return api_success(
        {
            "schedule": result,
            "schedules": timetable.get("schedules", []),
            "sessions": timetable.get("sessions", []),
            "lessons": [],
            "entity": result,
            "affected_ids": result.get("sessionIds", []),
            "revision": f"schedule:{result.get('scheduleId', 0)}",
        }
    )


@router.put("/groups/{group_id}/schedule", operation_id="api_v1_academic_director_upsert_group_schedule", response_model=ApiSuccess[AdminScheduleCreated])
def upsert_group_schedule(
    group_id: int,
    payload: AdminUpdateGroupScheduleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = upsert_group_schedule_from_payload(
            group_id,
            _payload(payload),
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({
        "schedule": result,
        "schedules": list_group_schedule_rows(group_id),
        "sessions": [],
        "lessons": [],
        "entity": result,
        "affected_ids": [int(result.get("scheduleId", 0))],
        "revision": f"schedule:{result.get('scheduleId', 0)}",
    })


@router.post("/groups/{group_id}/students", operation_id="api_v1_academic_director_create_group_student", response_model=ApiSuccess[AdminStudentCreated])
def create_group_student(group_id: int, payload: AdminCreateGroupStudentRequest):
    try:
        student = create_student_with_enrollment_from_payload({"full_name": payload.full_name, "group_id": group_id})
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"student": student})


@router.get(
    "/gradebook",
    operation_id="api_v1_academic_director_academic_gradebook",
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
    operation_id="api_v1_academic_director_academic_group_gradebook_trends",
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


@router.delete(
    "/groups/{group_id}",
    operation_id="api_v1_academic_director_delete_academic_group",
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
    academic_context = list_admin_academic_context(include_heavy=False)
    return api_success({"enrollment": result, "groups": academic_context.get("groups", [])})


@router.post(
    "/attendance",
    operation_id="api_v1_academic_director_record_academic_attendance",
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
    operation_id="api_v1_academic_director_record_academic_homework",
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
    operation_id="api_v1_academic_director_update_academic_lesson",
    response_model=ApiSuccess[AdminLessonUpdated],
)
def update_lesson(
    lesson_session_id: int,
    payload: AdminLessonUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        lesson = update_lesson_session_from_payload(
            lesson_session_id, _payload(payload), user.staff_id
        )
    except AcademicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"lesson": lesson})


@router.post(
    "/lessons/{lesson_session_id}/cancel",
    operation_id="api_v1_academic_director_cancel_academic_lesson",
    response_model=ApiSuccess[dict[str, Any]],
)
def cancel_lesson(lesson_session_id: int, payload: AdminLessonCancelRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        result = cancel_lesson_session(
            lesson_session_id,
            payload.reason,
            user.staff_id,
            allow_recorded_lesson_changes=payload.allow_recorded_lesson_changes,
        )
    except AcademicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(result)


@router.post(
    "/lessons/{lesson_session_id}/recover",
    operation_id="api_v1_academic_director_recover_academic_lesson",
    response_model=ApiSuccess[dict[str, Any]],
)
def recover_lesson(
    lesson_session_id: int,
    payload: AdminLessonRecoverRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = recover_lesson_session(
            lesson_session_id,
            user.staff_id,
            allow_recorded_lesson_changes=bool(
                payload and payload.allow_recorded_lesson_changes
            ),
        )
    except AcademicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(result)


@router.post(
    "/exams",
    operation_id="api_v1_academic_director_record_academic_exam",
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
