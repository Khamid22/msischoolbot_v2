"""Lessons academic operations."""

import json
from datetime import date

from backend.core.database import connect_auth_db
from backend.modules.domains.organization import canonical
from backend.modules.domains.academics.calendar import repository as calendar_repository
from backend.modules.domains.academics.timetable import repository as timetable_repository
from backend.modules.domains.academics.groups import repository as academic_repository
from backend.modules.domains.academics.lessons import repository
from backend.modules.domains.academics.exceptions import AcademicConflictError
from backend.modules.domains.academics.common import (
    _now, _normalize_lesson_status, _parse_optional_lesson_time,
)

def update_lesson_session_from_payload(lesson_session_id, payload, actor_staff_id=None):
    lesson_session_id = int(lesson_session_id or 0)
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    raw_date = payload.get("lesson_date", payload.get("date", None))
    next_date = None
    if raw_date is not None:
        try:
            next_date = date.fromisoformat(str(raw_date or "").strip())
        except ValueError as exc:
            raise ValueError("Lesson date must use YYYY-MM-DD.") from exc
    should_update_date = raw_date is not None
    raw_status = payload.get("status", None)
    next_status = _normalize_lesson_status(raw_status) if raw_status is not None else None
    raw_start_time = payload.get("start_time", None)
    raw_end_time = payload.get("end_time", None)
    should_update_times = raw_start_time is not None or raw_end_time is not None
    next_start_time = _parse_optional_lesson_time(raw_start_time)
    next_end_time = _parse_optional_lesson_time(raw_end_time)
    if should_update_times:
        if raw_start_time is None or raw_end_time is None or not next_start_time or not next_end_time:
            raise ValueError("Both start and end times are required.")
        if next_end_time <= next_start_time:
            raise ValueError("End time must be after the start time.")
    raw_room = payload.get("room", None)
    should_update_room = raw_room is not None
    next_room = str(raw_room or "").strip()
    raw_lesson_name = payload.get("lesson_name", None)
    should_update_lesson_name = raw_lesson_name is not None
    next_lesson_name = str(raw_lesson_name or "").strip()
    raw_topic = payload.get("topic", None)
    should_update_topic = raw_topic is not None
    next_topic = str(raw_topic or "").strip()
    if should_update_lesson_name and not next_lesson_name:
        raise ValueError("Lesson name is required.")
    allow_recorded_changes = bool(payload.get("allow_recorded_lesson_changes", False))

    def time_text(value):
        return str(value or "")[:5]

    with connect_auth_db() as conn:
        row = timetable_repository.get_lesson_session_snapshot(conn, lesson_session_id)
        if not row:
            raise ValueError("Lesson session was not found.")
        timetable_repository.lock_lesson_occurrence_scope(
            conn, int(row["group_id"]), int(row["teacher_id"] or 0)
        )
        row = timetable_repository.get_lesson_session_snapshot(
            conn, lesson_session_id, for_update=True
        )

        proposed_date = next_date if should_update_date else row["session_date"]
        proposed_start = next_start_time if should_update_times else time_text(row["start_time"])
        proposed_end = next_end_time if should_update_times else time_text(row["end_time"])
        proposed_room = next_room if should_update_room else str(row["room"] or "")
        proposed_name = next_lesson_name if should_update_lesson_name else str(row["lesson_number"] or "Session")
        proposed_topic = next_topic if should_update_topic else str(row["topic"] or "")
        changed_fields = []
        comparisons = {
            "lesson_date": (row["session_date"], proposed_date),
            "start_time": (time_text(row["start_time"]), proposed_start),
            "end_time": (time_text(row["end_time"]), proposed_end),
            "room": (str(row["room"] or ""), proposed_room),
            "lesson_name": (str(row["lesson_number"] or "Session"), proposed_name),
            "topic": (str(row["topic"] or ""), proposed_topic),
        }
        requested = {
            "lesson_date": should_update_date,
            "start_time": should_update_times,
            "end_time": should_update_times,
            "room": should_update_room,
            "lesson_name": should_update_lesson_name,
            "topic": should_update_topic,
        }
        for field, values in comparisons.items():
            if requested[field] and values[0] != values[1]:
                changed_fields.append(field)

        if changed_fields and bool(row["has_academic_records"]) and not allow_recorded_changes:
            raise AcademicConflictError(
                "This lesson already has attendance or homework. Confirm that you want to change it."
            )

        schedule_changed = any(
            field in changed_fields for field in ("lesson_date", "start_time", "end_time")
        )
        if schedule_changed:
            if proposed_date is None or not proposed_start or not proposed_end:
                raise ValueError("A scheduled lesson requires a date, start time, and end time.")
            active_exception = timetable_repository.get_active_lesson_exception(
                conn, lesson_session_id
            )
            if active_exception:
                raise AcademicConflictError(
                    "Recover this cancelled lesson before moving its scheduled occurrence."
                )
            if timetable_repository.group_date_has_active_exception(
                conn,
                int(row["group_id"]),
                proposed_date,
                exclude_lesson_session_id=lesson_session_id,
            ):
                raise AcademicConflictError(
                    "That date is blocked by an active lesson cancellation."
                )
            active_closure = calendar_repository.group_date_has_active_closure(
                conn,
                int(row["school_id"]),
                int(row["group_id"]),
                proposed_date,
            )
            if active_closure:
                raise AcademicConflictError(
                    f"That date is locked for {active_closure['title']}. Choose a teaching date outside the break."
                )
            conflicts = timetable_repository.list_lesson_occurrence_conflicts(
                conn,
                lesson_session_id=lesson_session_id,
                group_v2_id=int(row["group_id"]),
                teacher_v2_id=int(row["teacher_id"] or 0),
                session_date=proposed_date,
                start_time=proposed_start,
                end_time=proposed_end,
            )
            if conflicts:
                conflict = conflicts[0]
                label = str(conflict["teacher_name"] or conflict["group_name"] or "another lesson")
                raise AcademicConflictError(f"This time overlaps with {label}.")

        repository.update_lesson_session(
            conn,
            lesson_session_id=lesson_session_id,
            should_update_date=should_update_date,
            lesson_date=next_date,
            should_update_times=should_update_times,
            start_time=next_start_time,
            end_time=next_end_time,
            should_update_room=should_update_room,
            room=next_room,
            should_update_lesson_name=should_update_lesson_name,
            lesson_name=next_lesson_name,
            should_update_topic=should_update_topic,
            topic=next_topic,
            status=next_status,
        )
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.lesson_corrected",
            entity_type="lesson_session",
            entity_id=lesson_session_id,
            detail_json=json.dumps(
                {
                    "changed_fields": sorted(changed_fields),
                    "before": {
                        "date": row["session_date"].isoformat() if row["session_date"] else "",
                        "start_time": time_text(row["start_time"]),
                        "end_time": time_text(row["end_time"]),
                        "room": str(row["room"] or ""),
                        "lesson_name": str(row["lesson_number"] or "Session"),
                        "topic": str(row["topic"] or ""),
                    },
                    "after": {
                        "date": proposed_date.isoformat() if proposed_date else "",
                        "start_time": proposed_start,
                        "end_time": proposed_end,
                        "room": proposed_room,
                        "lesson_name": proposed_name,
                        "topic": proposed_topic,
                    },
                }
            ),
            actor_staff_id=actor_staff_id,
        )
        conn.commit()

    display_date = canonical.format_date(proposed_date)
    return {
        "id": lesson_session_id,
        "lessonSessionId": lesson_session_id,
        "groupId": int(row["public_group_id"]),
        "lessonNumber": proposed_name,
        "topic": proposed_topic,
        "date": display_date,
        "isoDate": proposed_date.isoformat() if proposed_date else "",
        "room": proposed_room,
        "startTime": proposed_start,
        "endTime": proposed_end,
        "status": next_status or str(row["status"] or "scheduled"),
        "hasAcademicRecords": bool(row["has_academic_records"]),
        "affectedIds": [lesson_session_id],
        "originalDate": row["session_date"].isoformat() if row["session_date"] else "",
        "revision": f"lesson:{lesson_session_id}:{_now().isoformat()}",
    }
