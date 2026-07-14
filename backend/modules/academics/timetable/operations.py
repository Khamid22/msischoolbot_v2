"""Timetable academic operations."""

import json
from datetime import timedelta

from backend.core.database import connect_auth_db
from backend.modules.academics.calendar import repository as calendar_repository
from backend.modules.academics.timetable import repository as timetable_repository
from backend.modules.academics.groups import repository as academic_repository
from backend.modules.academics.calendar.scheduling import closure_ranges, generate_teaching_dates
from backend.modules.academics.exceptions import AcademicConflictError
from backend.modules.academics.common import (
    _now,
)
from backend.modules.academics.timetable.service import (
    create_schedule,
    schedule_group_curriculum,
)

def create_schedule_from_payload(payload, *, actor_staff_id=None, actor_account_id=None):
    group_id = int(payload.get("group_id", 0) or 0)
    if group_id <= 0:
        raise ValueError("Group is required.")
    result = create_schedule(
        group_id,
        teacher_id=int(payload.get("teacher_id", 0) or 0),
        weekdays=payload.get("weekdays", []),
        start_time=payload.get("start_time", ""),
        end_time=payload.get("end_time", ""),
        lesson_duration_minutes=int(payload.get("lesson_duration_minutes", 0) or 0),
        start_date=payload.get("start_date", ""),
        end_date=payload.get("end_date", ""),
        room=payload.get("room", ""),
        online_url=payload.get("online_url", ""),
        title=payload.get("title", ""),
        actor_staff_id=actor_staff_id,
        actor_account_id=actor_account_id,
    )
    return result


def upsert_group_schedule_from_payload(
    group_id, payload, *, actor_staff_id=None, actor_account_id=None
):
    return schedule_group_curriculum(
        int(group_id), teacher_id=int(payload.get("teacher_id", 0) or 0),
        course_launch_date=payload.get("course_launch_date", payload.get("start_date", "")),
        weekdays=payload.get("weekdays", []),
        lesson_time=payload.get("lesson_time", payload.get("start_time", "")),
        lesson_duration_minutes=int(payload.get("lesson_duration_minutes", 80) or 80),
        room=payload.get("room", ""), change_scope=payload.get("change_scope", ""),
        effective_date=payload.get("effective_date", ""),
        change_course_launch_date=bool(payload.get("change_course_launch_date", False)),
        allow_recorded_lesson_changes=bool(payload.get("allow_recorded_lesson_changes", False)),
        actor_staff_id=actor_staff_id, actor_account_id=actor_account_id,
    )


def _schedule_weekdays(schedule):
    values = []
    for value in str(schedule["weekdays"] or "").split(","):
        try:
            day = int(value.strip())
        except (TypeError, ValueError):
            continue
        if 0 <= day <= 6 and day not in values:
            values.append(day)
    if not values:
        raise ValueError("The group timetable has no teaching days.")
    return set(values)


def _reflow_lesson_sequence(conn, lesson, *, first_date, include_first_date, ignored_exception_id=0):
    schedule = timetable_repository.get_active_group_schedule(conn, int(lesson["group_id"]))
    if not schedule:
        raise ValueError("Set up the group timetable before changing lessons.")
    weekdays = _schedule_weekdays(schedule)
    active_exceptions = timetable_repository.list_active_lesson_exceptions(conn, int(lesson["group_id"]))
    blocked = {
        row["original_session_date"]
        for row in active_exceptions
        if int(row["id"]) != int(ignored_exception_id or 0)
    }
    lessons = timetable_repository.list_curriculum_lessons_from_order(
        conn, int(lesson["group_id"]), int(lesson["item_order"])
    )
    active_closures = calendar_repository.list_effective_group_closures(
        conn, int(lesson["school_id"]), int(lesson["group_id"])
    )
    dates = generate_teaching_dates(
        start_date=first_date if include_first_date else first_date + timedelta(days=1),
        count=len(lessons),
        weekdays=weekdays,
        blocked_dates=blocked,
        closures=closure_ranges(active_closures),
    )
    for row, session_date in zip(lessons, dates):
        timetable_repository.schedule_curriculum_lesson(
            conn,
            int(row["id"]),
            schedule_id=int(schedule["id"]),
            teacher_v2_id=int(schedule["teacher_id"] or 0),
            session_date=session_date,
            start_time=schedule["start_time"],
            end_time=schedule["end_time"],
            room=str(schedule["room"] or ""),
        )
    if dates:
        timetable_repository.update_schedule_end_date(conn, int(schedule["id"]), dates[-1])
    return [int(row["id"]) for row in lessons]


def cancel_lesson_session(
    lesson_session_id,
    reason,
    actor_staff_id=None,
    *,
    allow_recorded_lesson_changes=False,
):
    lesson_session_id = int(lesson_session_id or 0)
    reason = str(reason or "").strip()
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    if not reason:
        raise ValueError("Cancellation reason is required.")
    with connect_auth_db() as conn:
        lesson = timetable_repository.get_curriculum_lesson_for_exception(conn, lesson_session_id)
        if not lesson:
            raise ValueError("Curriculum lesson was not found.")
        timetable_repository.lock_group_timetable_for_reflow(conn, int(lesson["group_id"]))
        lesson = timetable_repository.get_curriculum_lesson_for_exception(
            conn, lesson_session_id, for_update=True
        )
        if lesson["session_date"] is None:
            raise ValueError("Only a scheduled lesson can be cancelled.")
        if bool(lesson["has_academic_records"]) and not allow_recorded_lesson_changes:
            raise AcademicConflictError(
                "This lesson already has attendance or homework. Confirm cancellation to keep those records attached."
            )
        if timetable_repository.get_active_lesson_exception(conn, lesson_session_id):
            raise ValueError("This lesson is already cancelled.")
        exception = timetable_repository.insert_lesson_exception(conn, lesson, reason, actor_staff_id)
        affected_ids = _reflow_lesson_sequence(
            conn, lesson, first_date=lesson["session_date"], include_first_date=False
        )
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.lesson_cancelled",
            entity_type="lesson_session",
            entity_id=lesson_session_id,
            detail_json=json.dumps(
                {"exception_id": int(exception["id"]), "reason": reason, "affected": len(affected_ids)}
            ),
            actor_staff_id=actor_staff_id,
        )
        conn.commit()
        return {
            "groupId": int(lesson["group_id"]),
            "exceptionId": int(exception["id"]),
            "affectedLessonCount": len(affected_ids),
            "affectedIds": affected_ids,
            "revision": f"lesson-exception:{int(exception['id'])}:{_now().isoformat()}",
        }


def recover_lesson_session(
    lesson_session_id,
    actor_staff_id=None,
    *,
    allow_recorded_lesson_changes=False,
):
    lesson_session_id = int(lesson_session_id or 0)
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    with connect_auth_db() as conn:
        lesson = timetable_repository.get_curriculum_lesson_for_exception(conn, lesson_session_id)
        if not lesson:
            raise ValueError("Curriculum lesson was not found.")
        timetable_repository.lock_group_timetable_for_reflow(conn, int(lesson["group_id"]))
        lesson = timetable_repository.get_curriculum_lesson_for_exception(
            conn, lesson_session_id, for_update=True
        )
        exception = timetable_repository.get_active_lesson_exception(conn, lesson_session_id)
        if not exception:
            raise ValueError("This lesson has no active cancellation to recover.")
        if bool(lesson["has_academic_records"]) and not allow_recorded_lesson_changes:
            raise AcademicConflictError(
                "This lesson already has attendance or homework. Confirm recovery to keep those records attached."
            )
        timetable_repository.recover_lesson_exception(conn, int(exception["id"]), actor_staff_id)
        affected_ids = _reflow_lesson_sequence(
            conn,
            lesson,
            first_date=exception["original_session_date"],
            include_first_date=True,
            ignored_exception_id=int(exception["id"]),
        )
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.lesson_recovered",
            entity_type="lesson_session",
            entity_id=lesson_session_id,
            detail_json=json.dumps(
                {"exception_id": int(exception["id"]), "affected": len(affected_ids)}
            ),
            actor_staff_id=actor_staff_id,
        )
        conn.commit()
        return {
            "groupId": int(lesson["group_id"]),
            "exceptionId": int(exception["id"]),
            "affectedLessonCount": len(affected_ids),
            "affectedIds": affected_ids,
            "revision": f"lesson-exception:{int(exception['id'])}:recovered:{_now().isoformat()}",
        }
