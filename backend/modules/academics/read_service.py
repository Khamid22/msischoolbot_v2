"""Small, paginated academic read models for management workspaces."""

from __future__ import annotations

from datetime import date, timedelta

from backend.core.database import connect_auth_db
from backend.modules.academics import calendar_repository, repository, timetable_repository
from backend.modules.academics.calendar_closures import serialize_calendar_closure


def _bounded_limit(value, *, default, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 1), maximum)


def _offset(cursor):
    text = str(cursor or "").strip().lower()
    if not text:
        return 0
    if text.startswith("o"):
        text = text[1:]
    try:
        return max(int(text), 0)
    except ValueError as exc:
        raise ValueError("Invalid pagination cursor.") from exc


def _page(rows, *, offset, limit):
    items = []
    total = 0
    for row in rows:
        item = dict(row)
        total = int(item.pop("filtered_total", 0) or 0)
        items.append(item)
    next_offset = offset + len(items)
    return {
        "items": items,
        "next_cursor": f"o{next_offset}" if next_offset < total else None,
        "total": total,
    }


def list_group_page(*, school_id=0, subject_id=0, query="", cursor="", limit=50):
    page_limit = _bounded_limit(limit, default=50, maximum=100)
    page_offset = _offset(cursor)
    with connect_auth_db() as conn:
        rows = repository.list_group_rows_page(
            conn,
            school_id=school_id,
            subject_id=subject_id,
            query=query,
            offset=page_offset,
            limit=page_limit,
        )
    return _page(rows, offset=page_offset, limit=page_limit)


def get_group_summary(group_id):
    parsed_group_id = int(group_id or 0)
    if parsed_group_id <= 0:
        raise ValueError("Group is required.")
    with connect_auth_db() as conn:
        row = repository.get_group_summary_row(conn, parsed_group_id)
        if not row:
            return None
        summary = dict(row)
        summary["setup_status"] = (
            "active"
            if bool(summary.get("has_active_schedule"))
            and int(summary.get("students_count") or 0) > 0
            else "incomplete"
        )
        return summary


def list_program_page(*, cursor="", limit=50):
    page_limit = _bounded_limit(limit, default=50, maximum=100)
    page_offset = _offset(cursor)
    with connect_auth_db() as conn:
        rows = repository.list_curriculum_program_page(
            conn, offset=page_offset, limit=page_limit
        )
    return _page(rows, offset=page_offset, limit=page_limit)


def list_program_item_page(program_id, *, cursor="", limit=100):
    parsed_program_id = int(program_id or 0)
    if parsed_program_id <= 0:
        raise ValueError("Program is required.")
    page_limit = _bounded_limit(limit, default=100, maximum=250)
    page_offset = _offset(cursor)
    with connect_auth_db() as conn:
        rows = repository.list_curriculum_item_page(
            conn, parsed_program_id, offset=page_offset, limit=page_limit
        )
    return _page(rows, offset=page_offset, limit=page_limit)


def list_timetable_range(*, start_date="", end_date="", group_id=0, school_id=0):
    try:
        parsed_start = date.fromisoformat(str(start_date or ""))
        parsed_end = date.fromisoformat(str(end_date or ""))
    except ValueError as exc:
        raise ValueError("Timetable dates must use YYYY-MM-DD.") from exc
    if parsed_end < parsed_start:
        raise ValueError("Timetable end date must be on or after the start date.")
    if parsed_end - parsed_start > timedelta(days=62):
        raise ValueError("Timetable ranges cannot exceed 63 days.")

    with connect_auth_db() as conn:
        group_v2_id = 0
        group_scope = None
        if int(group_id or 0) > 0:
            group = repository.get_group_by_legacy_or_id(conn, int(group_id))
            if not group:
                raise ValueError("Group was not found.")
            group_v2_id = int(group["id"])
            school_id = int(group["school_id"])
            group_scope = {
                "groupId": int(group_id),
                "groupName": str(group["group_name"]),
                "schoolId": int(group["school_id"]),
                "schoolCode": str(group["school_key"]),
                "schoolName": str(group["school_name"]),
            }
        sessions = [
            dict(row)
            for row in timetable_repository.list_timetable_rows_in_range(
                conn,
                start_date=parsed_start,
                end_date=parsed_end,
                group_v2_id=group_v2_id,
                school_id=school_id,
            )
        ]
        exceptions = [
            {
                **dict(row),
                "exception_key": f"lesson-exception:{int(row['exception_id'])}",
                "is_cancellation": True,
                "can_recover": True,
            }
            for row in timetable_repository.list_timetable_exceptions_in_range(
                conn,
                start_date=parsed_start,
                end_date=parsed_end,
                group_v2_id=group_v2_id,
                school_id=school_id,
            )
        ]
        schedules = [
            dict(row)
            for row in timetable_repository.list_active_schedule_rows_for_scope(
                conn, group_v2_id=group_v2_id, school_id=school_id
            )
        ]
        unscheduled_lesson_count = (
            timetable_repository.count_unscheduled_curriculum_lessons(conn, group_v2_id)
            if group_v2_id
            else 0
        )
        closures = [
            serialize_calendar_closure(dict(row))
            for row in calendar_repository.list_calendar_closures(
                conn,
                school_id=school_id,
                group_v2_id=group_v2_id,
                start_date=parsed_start,
                end_date=parsed_end,
            )
        ]
    return {
        "from": parsed_start.isoformat(),
        "to": parsed_end.isoformat(),
        "range": {"from": parsed_start.isoformat(), "to": parsed_end.isoformat()},
        "scope": group_scope,
        "schedules": schedules,
        "activeSchedule": schedules[0] if len(schedules) == 1 else None,
        "sessions": sessions,
        "exceptions": exceptions,
        "calendarClosures": closures,
        "hasAcademicRecords": any(
            bool(item.get("has_academic_records")) for item in sessions + exceptions
        ),
        "unscheduledLessonCount": unscheduled_lesson_count,
    }


def list_group_schedule_rows(group_id):
    parsed_group_id = int(group_id or 0)
    if parsed_group_id <= 0:
        raise ValueError("Group is required.")
    with connect_auth_db() as conn:
        group = repository.get_group_by_legacy_or_id(conn, parsed_group_id)
        if not group:
            raise ValueError("Group was not found.")
        return [
            dict(row)
            for row in timetable_repository.list_active_schedule_rows_for_scope(
                conn, group_v2_id=int(group["id"])
            )
        ]


__all__ = [
    "get_group_summary",
    "list_group_page",
    "list_group_schedule_rows",
    "list_program_item_page",
    "list_program_page",
    "list_timetable_range",
]
