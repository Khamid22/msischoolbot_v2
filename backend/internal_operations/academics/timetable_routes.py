"""System-admin routes for schedules, calendar closures, and lesson timing."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, get_current_user
from backend.core.api import ApiSuccess, api_success
from backend.internal_operations.academics.common import model_payload
from backend.modules.academics.calendar.service import (
    CalendarClosureConflictError,
    create_calendar_closure,
    list_calendar_closures,
    preview_calendar_closure,
    unlock_calendar_closure,
)
from backend.modules.academics.exceptions import AcademicConflictError
from backend.modules.academics.groups.read_service import (
    list_group_schedule_rows,
    list_timetable_range,
)
from backend.modules.academics.lessons.service import update_lesson_session_from_payload
from backend.modules.academics.schemas import (
    AdminCalendarClosureRequest,
    AdminCalendarClosureUnlockRequest,
    AdminCreateScheduleRequest,
    AdminLessonCancelRequest,
    AdminLessonRecoverRequest,
    AdminLessonUpdated,
    AdminLessonUpdateRequest,
    AdminScheduleCreated,
    AdminUpdateGroupScheduleRequest,
)
from backend.modules.academics.timetable.operations import (
    cancel_lesson_session,
    create_schedule_from_payload,
    recover_lesson_session,
    upsert_group_schedule_from_payload,
)
from backend.platform.admin_page_cache import invalidate_admin_page_context_cache


router = APIRouter()


@router.post(
    "/schedules",
    operation_id="api_v1_admin_create_academic_schedule",
    response_model=ApiSuccess[AdminScheduleCreated],
)
def create_schedule(
    payload: AdminCreateScheduleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = create_schedule_from_payload(
            model_payload(payload),
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


@router.put(
    "/groups/{group_id}/schedule",
    operation_id="api_v1_admin_upsert_group_schedule",
    response_model=ApiSuccess[AdminScheduleCreated],
)
def upsert_group_schedule(
    group_id: int,
    payload: AdminUpdateGroupScheduleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = upsert_group_schedule_from_payload(
            group_id,
            model_payload(payload),
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(
        {
            "schedule": result,
            "schedules": list_group_schedule_rows(group_id),
            "sessions": [],
            "lessons": [],
            "entity": result,
            "affected_ids": [int(result.get("scheduleId", 0))],
            "revision": f"schedule:{result.get('scheduleId', 0)}",
        }
    )


@router.get(
    "/calendar-closures",
    operation_id="api_v1_admin_list_academic_calendar_closures",
    response_model=ApiSuccess[dict[str, Any]],
)
def academic_calendar_closures(
    school_id: int,
    group_id: int = 0,
    date_from: str = "",
    date_to: str = "",
):
    try:
        return api_success(
            list_calendar_closures(
                school_id=school_id,
                group_id=group_id,
                date_from=date_from,
                date_to=date_to,
            )
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/calendar-closures/preview",
    operation_id="api_v1_admin_preview_academic_calendar_closure",
    response_model=ApiSuccess[dict[str, Any]],
)
def preview_academic_calendar_closure(payload: AdminCalendarClosureRequest):
    try:
        return api_success(preview_calendar_closure(model_payload(payload)))
    except CalendarClosureConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/calendar-closures",
    operation_id="api_v1_admin_create_academic_calendar_closure",
    response_model=ApiSuccess[dict[str, Any]],
)
def create_academic_calendar_closure(
    payload: AdminCalendarClosureRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = create_calendar_closure(
            model_payload(payload),
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except CalendarClosureConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(result)


@router.post(
    "/calendar-closures/{closure_id}/unlock",
    operation_id="api_v1_admin_unlock_academic_calendar_closure",
    response_model=ApiSuccess[dict[str, Any]],
)
def unlock_academic_calendar_closure(
    closure_id: int,
    payload: AdminCalendarClosureUnlockRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        result = unlock_calendar_closure(
            closure_id,
            rebuild_future=payload.rebuild_future,
            actor_staff_id=user.staff_id,
            actor_account_id=user.account_id,
        )
    except CalendarClosureConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success(result)


@router.get(
    "/timetable",
    operation_id="api_v1_admin_academic_timetable_range",
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
    operation_id="api_v1_admin_group_timetable_range",
    response_model=ApiSuccess[dict[str, Any]],
)
def group_timetable_range(group_id: int, date_from: str, date_to: str):
    try:
        return api_success(
            list_timetable_range(
                start_date=date_from,
                end_date=date_to,
                group_id=group_id,
            )
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch(
    "/lessons/{lesson_session_id}",
    operation_id="api_v1_admin_update_academic_lesson",
    response_model=ApiSuccess[AdminLessonUpdated],
)
def update_lesson(
    lesson_session_id: int,
    payload: AdminLessonUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        lesson = update_lesson_session_from_payload(
            lesson_session_id,
            model_payload(payload),
            user.staff_id,
        )
    except AcademicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    invalidate_admin_page_context_cache()
    return api_success({"lesson": lesson})


@router.post(
    "/lessons/{lesson_session_id}/cancel",
    operation_id="api_v1_admin_cancel_academic_lesson",
    response_model=ApiSuccess[dict[str, Any]],
)
def cancel_lesson(
    lesson_session_id: int,
    payload: AdminLessonCancelRequest,
    user: CurrentUser = Depends(get_current_user),
):
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
    operation_id="api_v1_admin_recover_academic_lesson",
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
