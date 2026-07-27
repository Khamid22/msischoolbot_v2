"""Timetable domain services."""

import json
from datetime import date, timedelta

from backend.modules.domains.academics.calendar import repository as calendar_repository
from backend.modules.domains.academics.curriculum import repository as curriculum_repository
from backend.modules.domains.academics.groups import repository as group_repository
from backend.modules.domains.academics.timetable import repository as timetable_repository
from backend.modules.domains.academics.calendar.scheduling import closure_ranges, generate_teaching_dates
from backend.modules.domains.academics.foundation import (
    _connect, _resolve_group, _resolve_teacher_id, _parse_date_input,
    _time_to_minutes, _parse_time, _normalize_weekdays,
    _generated_schedule_dates, _schedule_conflict_message,
)

def create_schedule(
    group_id,
    *,
    teacher_id=0,
    weekdays=None,
    start_time="",
    end_time="",
    lesson_duration_minutes=0,
    start_date="",
    end_date="",
    room="",
    online_url="",
    title="",
    replace_existing=False,
    actor_staff_id=None,
    actor_account_id=None,
):
    group_id = int(group_id or 0)
    weekdays = _normalize_weekdays(weekdays)
    start_date_obj = _parse_date_input(start_date, "Start date")
    start_minutes = _time_to_minutes(start_time, "Start time")
    duration = int(lesson_duration_minutes or 0)
    if duration:
        if duration < 15 or duration > 240:
            raise ValueError("Lesson duration must be between 15 and 240 minutes.")
        end_minutes = start_minutes + duration
        if end_minutes >= 24 * 60:
            raise ValueError("Lesson duration cannot continue past midnight.")
        end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"
    else:
        end_minutes = _time_to_minutes(end_time, "End time")

    predicted = not str(end_date or "").strip()
    with _connect() as prediction_conn:
        prediction_group = _resolve_group(prediction_conn, group_id)
        if not prediction_group:
            raise ValueError("Group was not found.")
        prediction_group_id = int(prediction_group["id"])
        active_closures = calendar_repository.list_effective_group_closures(
            prediction_conn, int(prediction_group["school_id"]), prediction_group_id
        )
        blocked_dates = {
            row["blocked_date"]
            for row in timetable_repository.list_blocked_group_dates(
                prediction_conn, prediction_group_id
            )
            if row.get("blocked_date") is not None
        }
        if predicted:
            session_count = curriculum_repository.get_program_teaching_session_count(
                prediction_conn, int(prediction_group["program_id"])
            )
            if session_count <= 0:
                raise ValueError("The subject program has no lessons to schedule.")
            generated_dates = generate_teaching_dates(
                start_date=start_date_obj,
                count=session_count,
                weekdays=weekdays,
                blocked_dates=blocked_dates,
                closures=closure_ranges(active_closures),
            )
            end_date_obj = generated_dates[-1]
        else:
            end_date_obj = _parse_date_input(end_date, "End date")
            generated_dates = _generated_schedule_dates(
                start_date_obj,
                end_date_obj,
                weekdays,
                blocked_dates=blocked_dates,
                closures=closure_ranges(active_closures),
            )
    if end_date_obj < start_date_obj:
        raise ValueError("End date cannot be earlier than start date.")
    if (end_date_obj - start_date_obj).days > 366:
        raise ValueError("Schedule range cannot be longer than one year.")
    if end_minutes <= start_minutes:
        raise ValueError("End time must be after start time.")

    if not generated_dates:
        raise ValueError("The selected date range has no teaching days outside school breaks.")

    weekdays_text = ",".join(str(day) for day in weekdays)
    title = str(title or "").strip()
    room = str(room or "").strip()
    online_url = str(online_url or "").strip()
    start_time_obj = _parse_time(start_time, "Start time")
    end_time_obj = _parse_time(end_time, "End time")

    with _connect() as conn:
        group = _resolve_group(conn, group_id)
        if not group:
            raise ValueError("Group was not found.")
        v2_group_id = int(group["id"])
        teacher_v2_id = _resolve_teacher_id(conn, teacher_id)
        existing_rule = timetable_repository.get_active_group_schedule(conn, v2_group_id) if replace_existing else None
        existing_schedule_id = int(existing_rule["id"]) if existing_rule else 0

        conflict = _schedule_conflict_message(
            conn,
            group_v2_id=v2_group_id,
            teacher_v2_id=teacher_v2_id,
            weekdays=weekdays,
            start_date=start_date_obj,
            end_date=end_date_obj,
            start_time=start_time,
            end_time=end_time,
            exclude_schedule_id=existing_schedule_id,
        )
        if conflict:
            raise ValueError(conflict)

        rule_values = dict(teacher_v2_id=teacher_v2_id, title=title, weekdays_text=weekdays_text,
                           start_time=start_time_obj, end_time=end_time_obj, start_date=start_date_obj,
                           end_date=end_date_obj, room=room, online_url=online_url)
        if existing_schedule_id:
            timetable_repository.update_schedule_rule(conn, existing_schedule_id, **rule_values)
            timetable_repository.delete_unrecorded_schedule_sessions(conn, existing_schedule_id)
            schedule_id = existing_schedule_id
        else:
            inserted_rule = timetable_repository.insert_schedule_rule(conn, group_v2_id=v2_group_id, **rule_values)
            schedule_id = int(inserted_rule["id"]) if inserted_rule else 0

        session_ids = []
        for session_date in generated_dates:
            session_cur = timetable_repository.insert_lesson_session(
                conn,
                group_v2_id=v2_group_id,
                schedule_id=schedule_id,
                teacher_v2_id=teacher_v2_id,
                session_date=session_date,
                start_time=start_time_obj,
                end_time=end_time_obj,
                room=room,
                online_url=online_url,
            )
            if session_cur:
                session_ids.append(int(session_cur["id"] or 0))
        group_repository.insert_audit_event(
            conn,
            event_type="academic.schedule_upserted",
            entity_type="group_schedule_rule",
            entity_id=schedule_id,
            detail_json=json.dumps(
                {
                    "group_id": v2_group_id,
                    "start_date": start_date_obj.isoformat(),
                    "end_date": end_date_obj.isoformat(),
                    "weekdays": weekdays,
                    "session_count": len(generated_dates),
                    "replaced_existing": bool(existing_schedule_id),
                }
            ),
            actor_staff_id=actor_staff_id,
            actor_account_id=actor_account_id,
        )
        conn.commit()

    return {
        "scheduleId": schedule_id,
        "sessionCount": len(generated_dates),
        "firstLessonDate": generated_dates[0].isoformat() if generated_dates else "",
        "lessonDurationMinutes": end_minutes - start_minutes,
        "predictedEndDate": end_date_obj.isoformat(),
        "endDateWasPredicted": predicted,
        "sessionIds": [session_id for session_id in session_ids if session_id],
    }


def _lesson_has_locked_history(lesson):
    return (
        bool(lesson.get("has_academic_records"))
        or str(lesson.get("status") or "").strip().casefold() == "completed"
    )


def _resolve_course_launch_date(existing_schedule, requested_date, *, allow_change=False):
    if existing_schedule and not allow_change:
        return existing_schedule["start_date"]
    return _parse_date_input(requested_date, "Course launch date")


def _select_schedule_change_lessons(
    lessons,
    *,
    scope,
    effective_date,
    launch_date,
    allow_recorded_lesson_changes=False,
    today=None,
):
    """Select a safe reflow set and anchor without silently moving history."""
    today = today or date.today()
    protected = [row for row in lessons if _lesson_has_locked_history(row)]

    if scope == "from_date":
        candidates = [
            row
            for row in lessons
            if row.get("session_date") is None or row.get("session_date") >= effective_date
        ]
        anchor = effective_date
    elif scope == "remaining":
        candidates = [
            row
            for row in lessons
            if str(row.get("status") or "").strip().casefold() == "scheduled"
        ]
        candidates = [row for row in candidates if not _lesson_has_locked_history(row)]
        dated_future = sorted(
            row["session_date"]
            for row in candidates
            if row.get("session_date") is not None and row["session_date"] >= today
        )
        anchor = dated_future[0] if dated_future else max(launch_date, today)
    elif scope == "all":
        candidates = list(lessons)
        anchor = launch_date
    else:
        # A new group has no history. Imported groups may already have completed
        # sessions before their first timetable rule; preserve those sessions and
        # schedule only the unrecorded remainder after the latest known lesson.
        candidates = list(lessons)
        if protected:
            candidates = [row for row in candidates if not _lesson_has_locked_history(row)]
            dated_history = [row["session_date"] for row in protected if row.get("session_date")]
            anchor = max(launch_date, max(dated_history) + timedelta(days=1), today) if dated_history else max(launch_date, today)
        else:
            anchor = launch_date

    protected_candidates = [row for row in candidates if _lesson_has_locked_history(row)]
    if protected_candidates and scope in {"all", "from_date"} and not allow_recorded_lesson_changes:
        count = len(protected_candidates)
        noun = "lesson" if count == 1 else "lessons"
        raise ValueError(
            f"This change would move {count} completed or recorded {noun}. "
            "Confirm the historical timetable change before saving."
        )

    moved_protected_count = len(protected_candidates) if allow_recorded_lesson_changes else 0
    return candidates, anchor, len(protected), moved_protected_count


def schedule_group_curriculum(
    group_id, *, teacher_id=0, course_launch_date="", weekdays=None,
    lesson_time="", lesson_duration_minutes=80, room="", change_scope="", effective_date="",
    change_course_launch_date=False, allow_recorded_lesson_changes=False,
    actor_staff_id=None, actor_account_id=None,
):
    """Version a group timetable and assign dates to its existing curriculum lessons."""
    group_id = int(group_id or 0)
    weekdays = _normalize_weekdays(weekdays)
    start_minutes = _time_to_minutes(lesson_time, "Lesson time")
    duration = int(lesson_duration_minutes or 0)
    if duration < 15 or duration > 240 or start_minutes + duration >= 24 * 60:
        raise ValueError("The school lesson duration produces an invalid lesson time.")
    end_minutes = start_minutes + duration
    end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"
    start_time_obj = _parse_time(lesson_time, "Lesson time")
    end_time_obj = _parse_time(end_time, "End time")
    scope = str(change_scope or "").strip().casefold()
    if scope and scope not in {"all", "from_date", "remaining"}:
        raise ValueError("Unsupported timetable change scope.")
    effective = _parse_date_input(effective_date, "Effective date") if scope == "from_date" else None

    with _connect() as conn:
        group = _resolve_group(conn, group_id)
        if not group:
            raise ValueError("Group was not found.")
        v2_group_id = int(group["id"])
        teacher_v2_id = _resolve_teacher_id(conn, teacher_id)
        timetable_repository.ensure_curriculum_lesson_sessions(conn, v2_group_id)
        all_lessons = list(timetable_repository.list_curriculum_lesson_sessions(conn, v2_group_id))
        if not all_lessons:
            raise ValueError("The subject program has no lessons to schedule.")
        existing = timetable_repository.get_active_group_schedule(conn, v2_group_id)
        if existing and not scope:
            raise ValueError("Choose how this timetable change should apply to existing lessons.")
        launch_date = _resolve_course_launch_date(
            existing,
            course_launch_date,
            allow_change=bool(change_course_launch_date),
        )

        selected, anchor, protected_count, moved_protected_count = _select_schedule_change_lessons(
            all_lessons,
            scope=scope,
            effective_date=effective,
            launch_date=launch_date,
            allow_recorded_lesson_changes=bool(allow_recorded_lesson_changes),
        )
        if not selected:
            raise ValueError("No lessons match the selected timetable change scope.")

        blocked_dates = {
            row["blocked_date"]
            for row in timetable_repository.list_blocked_group_dates(conn, v2_group_id)
            if row.get("blocked_date") is not None
        }
        active_closures = calendar_repository.list_effective_group_closures(
            conn, int(group["school_id"]), v2_group_id
        )
        dates = generate_teaching_dates(
            start_date=anchor,
            count=len(selected),
            weekdays=weekdays,
            blocked_dates=blocked_dates,
            closures=closure_ranges(active_closures),
        )
        final_date = dates[-1]
        existing_id = int(existing["id"]) if existing else 0
        conflict = _schedule_conflict_message(
            conn, group_v2_id=v2_group_id, teacher_v2_id=teacher_v2_id,
            weekdays=weekdays, start_date=anchor, end_date=final_date,
            start_time=lesson_time, end_time=end_time, exclude_schedule_id=existing_id,
        )
        if conflict:
            raise ValueError(conflict)
        inserted = timetable_repository.insert_schedule_rule(
            conn, group_v2_id=v2_group_id, teacher_v2_id=teacher_v2_id,
            title="Regular class", weekdays_text=",".join(str(day) for day in weekdays),
            start_time=start_time_obj, end_time=end_time_obj, start_date=launch_date,
            end_date=final_date, room=str(room or "").strip(), online_url="",
        )
        schedule_id = int(inserted["id"])
        for lesson, session_date in zip(selected, dates):
            timetable_repository.schedule_curriculum_lesson(
                conn, int(lesson["id"]), schedule_id=schedule_id,
                teacher_v2_id=teacher_v2_id, session_date=session_date,
                start_time=start_time_obj, end_time=end_time_obj,
                room=str(room or "").strip(),
            )
        if existing_id:
            timetable_repository.cancel_schedule_rule(conn, existing_id)
        timetable_repository.delete_unrecorded_generic_group_sessions(conn, v2_group_id)
        group_repository.insert_audit_event(
            conn,
            event_type="academic.schedule_upserted",
            entity_type="group_schedule_rule",
            entity_id=schedule_id,
            detail_json=json.dumps(
                {
                    "group_id": v2_group_id,
                    "change_scope": scope or "initial",
                    "effective_date": effective.isoformat() if effective else None,
                    "course_launch_date": launch_date.isoformat(),
                    "affected_lesson_count": len(selected),
                    "moved_recorded_lesson_count": moved_protected_count,
                    "replaced_schedule_id": existing_id or None,
                }
            ),
            actor_staff_id=actor_staff_id,
            actor_account_id=actor_account_id,
        )
        conn.commit()
    return {
        "scheduleId": schedule_id, "affectedLessonCount": len(selected),
        "firstLessonDate": dates[0].isoformat(), "predictedEndDate": final_date.isoformat(),
        "lessonDurationMinutes": duration, "changeScope": scope or "initial",
        "courseLaunchDate": launch_date.isoformat(),
        "protectedLessonCount": protected_count,
        "movedRecordedLessonCount": moved_protected_count,
    }
