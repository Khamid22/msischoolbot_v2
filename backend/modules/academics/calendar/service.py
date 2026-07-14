"""Use-cases for auditable school and group timetable closures."""

from __future__ import annotations

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from backend.core.database import connect_auth_db
from backend.modules.academics.calendar import repository as calendar_repository
from backend.modules.academics.groups import repository as academic_repository
from backend.modules.academics.timetable import repository as timetable_repository
from backend.modules.academics.calendar.scheduling import closure_ranges, generate_teaching_dates


class CalendarClosureConflictError(ValueError):
    """A closure cannot be applied without violating protected timetable state."""


def _school_today() -> date:
    return datetime.now(ZoneInfo("Asia/Tashkent")).date()


def _parse_date(value, label):
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD.") from exc


def _serialize_closure(row):
    return {
        "id": int(row["id"]),
        "schoolId": int(row["school_id"]),
        "schoolCode": str(row.get("school_key") or ""),
        "schoolName": str(row.get("school_name") or ""),
        "groupId": int(row.get("public_group_id") or row.get("group_id") or 0) or None,
        "groupName": str(row.get("group_name") or ""),
        "scope": str(row.get("scope") or ("group" if row.get("group_id") else "school")),
        "title": str(row["title"]),
        "startDate": row["start_date"].isoformat(),
        "endDate": row["end_date"].isoformat(),
        "status": str(row.get("status") or "active"),
    }


serialize_calendar_closure = _serialize_closure


def _resolve_scope(conn, *, school_id, group_id=0):
    parsed_school_id = int(school_id or 0)
    if parsed_school_id <= 0:
        raise ValueError("School is required.")
    school = calendar_repository.get_school(conn, parsed_school_id)
    if not school:
        raise ValueError("School was not found.")
    group = None
    if int(group_id or 0) > 0:
        group = academic_repository.get_group_by_legacy_or_id(conn, int(group_id))
        if not group:
            raise ValueError("Group was not found.")
        if int(group["school_id"]) != parsed_school_id:
            raise ValueError("The selected group does not belong to this school.")
    return school, group


def _weekdays(schedule):
    result = set()
    for value in str(schedule["weekdays"] or "").split(","):
        try:
            parsed = int(value.strip())
        except ValueError:
            continue
        if 0 <= parsed <= 6:
            result.add(parsed)
    if not result:
        raise CalendarClosureConflictError("The group timetable has no teaching days.")
    return result


def _is_protected(row):
    return bool(row.get("has_academic_records")) or str(row.get("status") or "").lower() == "completed"


def _plan_group_reflow(
    conn,
    group,
    *,
    trigger_start,
    trigger_end,
    rebuild_from_start=False,
    today=None,
    extra_closures=(),
):
    group_v2_id = int(group["id"])
    schedule = timetable_repository.get_active_group_schedule(conn, group_v2_id)
    lessons = [dict(row) for row in calendar_repository.list_group_curriculum_for_reflow(conn, group_v2_id)]
    protected_in_range = [
        row for row in lessons
        if row.get("session_date") is not None
        and trigger_start <= row["session_date"] <= trigger_end
        and _is_protected(row)
    ]
    if not schedule or not lessons:
        return {
            "group": dict(group), "schedule": schedule, "movable": [], "dates": [],
            "protected": protected_in_range, "conflicts": [],
        }

    today = today or _school_today()
    lower_bound = max(today, trigger_start)
    if rebuild_from_start:
        affected = [
            row for row in lessons
            if not _is_protected(row)
            and (row.get("session_date") is None or row["session_date"] >= lower_bound)
        ]
    else:
        affected = [
            row for row in lessons
            if not _is_protected(row)
            and row.get("session_date") is not None
            and lower_bound <= row["session_date"] <= trigger_end
        ]
    if not affected:
        return {
            "group": dict(group), "schedule": schedule, "movable": [], "dates": [],
            "protected": protected_in_range, "conflicts": [],
        }

    first_order = min(int(row["item_order"]) for row in affected)
    first_dates = [row["session_date"] for row in affected if row.get("session_date")]
    anchor = lower_bound if rebuild_from_start else max(lower_bound, min(first_dates))
    tail = [row for row in lessons if int(row["item_order"]) >= first_order]
    protected_future = [
        row for row in tail
        if _is_protected(row) and row.get("session_date") is not None and row["session_date"] >= anchor
    ]
    if protected_future:
        return {
            "group": dict(group), "schedule": schedule, "movable": [], "dates": [],
            "protected": protected_in_range,
            "conflicts": [
                f"{group['group_name']} has a recorded or completed future lesson that prevents a safe reflow."
            ],
        }

    movable = [
        row for row in tail
        if not _is_protected(row)
        and (row.get("session_date") is None or row["session_date"] >= anchor)
    ]
    if not movable:
        return {
            "group": dict(group), "schedule": schedule, "movable": [], "dates": [],
            "protected": protected_in_range, "conflicts": [],
        }

    closures = list(calendar_repository.list_effective_group_closures(
        conn, int(group["school_id"]), group_v2_id
    )) + list(extra_closures)
    blocked_dates = {
        row["blocked_date"] for row in timetable_repository.list_blocked_group_dates(conn, group_v2_id)
        if row.get("blocked_date") is not None
    }
    fixed_dates = {
        row["session_date"] for row in lessons
        if int(row["id"]) not in {int(item["id"]) for item in movable}
        and row.get("session_date") is not None
        and row["session_date"] >= anchor
    }
    dates = generate_teaching_dates(
        start_date=anchor,
        count=len(movable),
        weekdays=_weekdays(schedule),
        blocked_dates=blocked_dates | fixed_dates,
        closures=closure_ranges(closures),
    )
    return {
        "group": dict(group), "schedule": schedule, "movable": movable, "dates": dates,
        "protected": protected_in_range, "conflicts": [],
    }


def _validate_planned_occurrences(conn, plans):
    """Validate the complete school reflow before updating any lesson row."""

    excluded_ids = [
        int(row["id"])
        for plan in plans
        for row in plan["movable"]
    ]
    proposed = []
    for plan in plans:
        if plan["conflicts"] or not plan["movable"]:
            continue
        schedule = plan["schedule"]
        for lesson, session_date in zip(plan["movable"], plan["dates"]):
            rows = calendar_repository.list_reflow_occurrence_conflicts(
                conn,
                excluded_session_ids=excluded_ids,
                group_v2_id=int(plan["group"]["id"]),
                teacher_v2_id=int(schedule["teacher_id"] or 0),
                session_date=session_date,
                start_time=schedule["start_time"],
                end_time=schedule["end_time"],
            )
            if rows:
                conflict = rows[0]
                label = str(
                    conflict["teacher_name"]
                    or conflict["group_name"]
                    or "another lesson"
                )
                plan["conflicts"].append(
                    f"{plan['group']['group_name']} overlaps with {label} "
                    f"on {session_date.isoformat()}."
                )
                break
            proposed.append({
                "plan": plan,
                "lesson_id": int(lesson["id"]),
                "date": session_date,
                "start": schedule["start_time"],
                "end": schedule["end_time"],
                "group_id": int(plan["group"]["id"]),
                "teacher_id": int(schedule["teacher_id"] or 0),
            })

    for index, left in enumerate(proposed):
        for right in proposed[index + 1:]:
            same_resource = (
                left["group_id"] == right["group_id"]
                or (
                    left["teacher_id"] > 0
                    and left["teacher_id"] == right["teacher_id"]
                )
            )
            overlaps = left["start"] < right["end"] and right["start"] < left["end"]
            if left["date"] != right["date"] or not same_resource or not overlaps:
                continue
            right_plan = right["plan"]
            message = (
                f"{right_plan['group']['group_name']} overlaps with "
                f"{left['plan']['group']['group_name']} on {right['date'].isoformat()}."
            )
            if message not in right_plan["conflicts"]:
                right_plan["conflicts"].append(message)


def _apply_group_plan(conn, plan):
    schedule = plan["schedule"]
    for lesson, session_date in zip(plan["movable"], plan["dates"]):
        timetable_repository.schedule_curriculum_lesson(
            conn,
            int(lesson["id"]),
            schedule_id=int(schedule["id"]),
            teacher_v2_id=int(schedule["teacher_id"] or 0),
            session_date=session_date,
            start_time=schedule["start_time"],
            end_time=schedule["end_time"],
            room=str(schedule["room"] or ""),
        )
    final_date = calendar_repository.max_group_curriculum_date(conn, int(plan["group"]["id"]))
    if final_date:
        timetable_repository.update_schedule_end_date(conn, int(schedule["id"]), final_date)


def _summary(plans):
    affected_groups = [int(plan["group"]["public_group_id"]) for plan in plans if plan["movable"]]
    affected_lessons = [int(row["id"]) for plan in plans for row in plan["movable"]]
    protected_lessons = [int(row["id"]) for plan in plans for row in plan["protected"]]
    conflicts = [message for plan in plans for message in plan["conflicts"]]
    return {
        "affectedGroupIds": affected_groups,
        "affectedLessonIds": affected_lessons,
        "affectedGroupCount": len(affected_groups),
        "affectedLessonCount": len(affected_lessons),
        "preservedRecordedLessonIds": protected_lessons,
        "preservedRecordedLessonCount": len(protected_lessons),
        "conflicts": conflicts,
    }


def list_calendar_closures(*, school_id=0, group_id=0, date_from="", date_to=""):
    start = _parse_date(date_from, "Start date") if str(date_from or "").strip() else None
    end = _parse_date(date_to, "End date") if str(date_to or "").strip() else None
    if (start is None) != (end is None):
        raise ValueError("Both start and end dates are required for a closure range.")
    if start and end and end < start:
        raise ValueError("End date must be on or after the start date.")
    with connect_auth_db() as conn:
        school, group = _resolve_scope(conn, school_id=school_id, group_id=group_id)
        rows = calendar_repository.list_calendar_closures(
            conn,
            school_id=int(school["id"]),
            group_v2_id=int(group["id"]) if group else 0,
            start_date=start,
            end_date=end,
        )
    return {"items": [_serialize_closure(dict(row)) for row in rows]}


def preview_calendar_closure(payload):
    start = _parse_date(payload.get("start_date"), "Start date")
    end = _parse_date(payload.get("end_date"), "End date")
    if end < start:
        raise ValueError("End date must be on or after the start date.")
    if (end - start).days > 366:
        raise ValueError("A calendar closure cannot be longer than one year.")
    with connect_auth_db() as conn:
        school, group = _resolve_scope(
            conn, school_id=payload.get("school_id"), group_id=payload.get("group_id", 0)
        )
        groups = calendar_repository.list_scope_groups(
            conn, int(school["id"]), int(group["id"]) if group else 0
        )
        synthetic = {"start_date": start, "end_date": end}
        plans = []
        for item in groups:
            plans.append(_plan_group_reflow(
                conn,
                item,
                trigger_start=start,
                trigger_end=end,
                extra_closures=[synthetic],
            ))
        _validate_planned_occurrences(conn, plans)
        return {
            "scope": "group" if group else "school",
            "schoolId": int(school["id"]),
            "groupId": int(group["id"]) if group else None,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            **_summary(plans),
        }


def create_calendar_closure(payload, *, actor_staff_id=None, actor_account_id=None):
    title = str(payload.get("title") or "Summer holiday").strip()
    if not title:
        raise ValueError("Closure title is required.")
    start = _parse_date(payload.get("start_date"), "Start date")
    end = _parse_date(payload.get("end_date"), "End date")
    if end < start:
        raise ValueError("End date must be on or after the start date.")
    if (end - start).days > 366:
        raise ValueError("A calendar closure cannot be longer than one year.")
    with connect_auth_db() as conn:
        school, group = _resolve_scope(
            conn, school_id=payload.get("school_id"), group_id=payload.get("group_id", 0)
        )
        school_id = int(school["id"])
        group_v2_id = int(group["id"]) if group else 0
        calendar_repository.lock_closure_scope(conn, school_id)
        groups = list(calendar_repository.list_scope_groups(conn, school_id, group_v2_id))
        for item in groups:
            timetable_repository.lock_group_timetable_for_reflow(conn, int(item["id"]))
        if calendar_repository.find_exact_active_closure(
            conn, school_id, group_v2_id, start, end
        ):
            raise CalendarClosureConflictError("This exact holiday lock already exists.")
        closure = calendar_repository.insert_calendar_closure(
            conn,
            school_id=school_id,
            group_v2_id=group_v2_id,
            title=title,
            start_date=start,
            end_date=end,
            actor_staff_id=actor_staff_id,
        )
        plans = [
            _plan_group_reflow(conn, item, trigger_start=start, trigger_end=end)
            for item in groups
        ]
        _validate_planned_occurrences(conn, plans)
        summary = _summary(plans)
        if summary["conflicts"]:
            raise CalendarClosureConflictError(summary["conflicts"][0])
        for plan in plans:
            _apply_group_plan(conn, plan)
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.calendar_closure_created",
            entity_type="academic_calendar_closure",
            entity_id=int(closure["id"]),
            detail_json=json.dumps({
                "school_id": school_id,
                "group_id": group_v2_id or None,
                "title": title,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                **summary,
            }),
            actor_staff_id=actor_staff_id,
            actor_account_id=actor_account_id,
        )
        conn.commit()
        closure_payload = {
            **dict(closure),
            "school_key": school["school_key"],
            "school_name": school["school_name"],
            "public_group_id": int(payload.get("group_id") or 0) if group else None,
            "group_name": str(group.get("group_name") or "") if group else "",
            "scope": "group" if group else "school",
        }
        return {
            "closure": _serialize_closure(closure_payload),
            **summary,
            "revision": f"calendar-closure:{int(closure['id'])}",
        }


def unlock_calendar_closure(
    closure_id, *, rebuild_future=False, actor_staff_id=None, actor_account_id=None
):
    closure_id = int(closure_id or 0)
    if closure_id <= 0:
        raise ValueError("Calendar closure is required.")
    with connect_auth_db() as conn:
        closure = calendar_repository.get_calendar_closure(conn, closure_id)
        if not closure or str(closure["status"]) != "active":
            raise ValueError("Active calendar closure was not found.")
        school_id = int(closure["school_id"])
        calendar_repository.lock_closure_scope(conn, school_id)
        closure = calendar_repository.get_calendar_closure(conn, closure_id, for_update=True)
        groups = list(calendar_repository.list_scope_groups(
            conn, school_id, int(closure["group_id"] or 0)
        ))
        if rebuild_future:
            for item in groups:
                timetable_repository.lock_group_timetable_for_reflow(conn, int(item["id"]))
        unlocked = calendar_repository.unlock_calendar_closure(conn, closure_id, actor_staff_id)
        plans = []
        if rebuild_future:
            plans = [
                _plan_group_reflow(
                    conn,
                    item,
                    trigger_start=closure["start_date"],
                    trigger_end=closure["end_date"],
                    rebuild_from_start=True,
                )
                for item in groups
            ]
            _validate_planned_occurrences(conn, plans)
        summary = _summary(plans)
        if summary["conflicts"]:
            raise CalendarClosureConflictError(summary["conflicts"][0])
        for plan in plans:
            _apply_group_plan(conn, plan)
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.calendar_closure_unlocked",
            entity_type="academic_calendar_closure",
            entity_id=closure_id,
            detail_json=json.dumps({"rebuild_future": bool(rebuild_future), **summary}),
            actor_staff_id=actor_staff_id,
            actor_account_id=actor_account_id,
        )
        conn.commit()
        school = calendar_repository.get_school(conn, school_id)
        group = None
        if closure["group_id"]:
            group_rows = calendar_repository.list_scope_groups(
                conn, school_id, int(closure["group_id"])
            )
            group = group_rows[0] if group_rows else None
        closure_payload = {
            **dict(unlocked),
            "school_key": school["school_key"] if school else "",
            "school_name": school["school_name"] if school else "",
            "public_group_id": int(group["public_group_id"]) if group else None,
            "group_name": str(group["group_name"] or "") if group else "",
            "scope": "group" if closure["group_id"] else "school",
        }
        return {
            "closure": _serialize_closure(closure_payload),
            **summary,
            "revision": f"calendar-closure:{closure_id}:unlocked",
        }


__all__ = [
    "CalendarClosureConflictError",
    "create_calendar_closure",
    "list_calendar_closures",
    "preview_calendar_closure",
    "serialize_calendar_closure",
    "unlock_calendar_closure",
]
