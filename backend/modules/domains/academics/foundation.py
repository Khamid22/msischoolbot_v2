"""Academics domain services."""

from datetime import datetime, time, timezone

from backend.core.database import connect_auth_db
from backend.modules.domains.organization import canonical
from backend.modules.domains.academics.groups import repository as academic_repository
from backend.modules.domains.academics.timetable import repository as timetable_repository
from backend.modules.domains.academics.calendar.scheduling import generate_teaching_dates


_LEGACY_ID_FLOOR = 9_000_000_000


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return connect_auth_db()


def _normalize(value):
    return canonical.normalize_text(value)


def _canonical_subject_name(value):
    return canonical.canonical_subject_name(value) or "Subject"


def _canonical_subject_key(value):
    return canonical.subject_key(value)


def _canonical_subject_short(value):
    return canonical.subject_short_name(value)


def _slugify(value):
    import re

    text = re.sub(r"[^a-z0-9]+", "-", _normalize(value)).strip("-")
    return text or "item"


def ensure_academic_schema(conn):
    """Compatibility no-op.

    The clean ``msi_v2`` schema is created at startup by
    ``backend.modules.domains.identity.bootstrap.ensure_clean_v2_schema``. A few call sites still
    invoke this helper; keep it as a no-op until they are cut over.
    """
    return None


def _mint_legacy_id(conn, table, column, floor=_LEGACY_ID_FLOOR):
    return academic_repository.mint_legacy_id(conn, table, column, floor)


def _resolve_group(conn, group_id):
    return academic_repository.get_group_by_legacy_or_id(conn, group_id)


def _resolve_teacher_id(conn, teacher_id):
    """Resolve an incoming (legacy or v2) teacher id to the msi_v2 teachers.id."""
    teacher_id = int(teacher_id or 0)
    if teacher_id <= 0:
        return 0
    row = academic_repository.get_teacher_v2_id_by_legacy_or_id(conn, teacher_id)
    if not row:
        raise ValueError("Teacher was not found.")
    return int(row["id"])


def _next_student_code(conn, prefix="MSI"):
    normalized_prefix = str(prefix or "MSI").strip().upper() or "MSI"
    rows = academic_repository.list_student_codes_with_prefix(conn, normalized_prefix)
    max_num = 0
    prefix_length = len(normalized_prefix)
    for row in rows:
        raw = str(row["student_code"] or "").strip().upper()
        if not raw.startswith(normalized_prefix):
            continue
        numeric_part = raw[prefix_length:]
        if numeric_part.isdigit():
            max_num = max(max_num, int(numeric_part))
    return f"{normalized_prefix}{max_num + 1:05d}"


def _parse_date_input(value, field_name):
    text = str(value or "").strip()
    parsed = canonical.parse_date(text)
    if parsed:
        return parsed
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid date.") from exc


def _time_to_minutes(value, field_name):
    text = str(value or "").strip()
    try:
        hour, minute = text.split(":", 1)
        total = int(hour) * 60 + int(minute)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must use HH:MM time.") from exc
    if total < 0 or total >= 24 * 60 or not (0 <= int(minute) <= 59):
        raise ValueError(f"{field_name} must use HH:MM time.")
    return total


def _parse_time(value, field_name):
    minutes = _time_to_minutes(value, field_name)
    return time(hour=minutes // 60, minute=minutes % 60)


def _normalize_weekdays(value):
    raw = value
    if isinstance(value, str):
        raw = value.replace(";", ",").split(",")
    if not isinstance(raw, (list, tuple, set)):
        raw = []
    weekdays = []
    names = {
        "mon": 0, "monday": 0,
        "tue": 1, "tuesday": 1,
        "wed": 2, "wednesday": 2,
        "thu": 3, "thursday": 3,
        "fri": 4, "friday": 4,
        "sat": 5, "saturday": 5,
        "sun": 6, "sunday": 6,
    }
    for item in raw:
        # Monday is represented by integer 0, which is valid but falsy.
        text = str(item if item is not None else "").strip().casefold()
        if not text:
            continue
        if text in names:
            day = names[text]
        else:
            try:
                day = int(text)
            except ValueError:
                continue
        if 0 <= day <= 6 and day not in weekdays:
            weekdays.append(day)
    if not weekdays:
        raise ValueError("Select at least one weekday.")
    return sorted(weekdays)


def _date_ranges_overlap(start_a, end_a, start_b, end_b):
    return start_a <= end_b and start_b <= end_a


def _time_ranges_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def _generated_schedule_dates(start_date, end_date, weekdays, *, blocked_dates=(), closures=()):
    return generate_teaching_dates(
        start_date=start_date,
        count=0,
        weekdays=weekdays,
        blocked_dates=blocked_dates,
        closures=closures,
        end_date=end_date,
    )


def _schedule_conflict_message(
    conn, *, group_v2_id, teacher_v2_id, weekdays, start_date, end_date, start_time, end_time,
    exclude_schedule_id=0,
):
    rows = timetable_repository.list_schedule_conflict_rows(conn, group_v2_id, teacher_v2_id, exclude_schedule_id)
    wanted_days = set(weekdays)
    wanted_start = _time_to_minutes(start_time, "Start time")
    wanted_end = _time_to_minutes(end_time, "End time")
    for row in rows:
        other_days = set(_normalize_weekdays(str(row["weekdays"] or "")))
        if not wanted_days.intersection(other_days):
            continue
        other_start_date = _parse_date_input(row["start_date"], "Existing start date")
        other_end_date = _parse_date_input(row["end_date"], "Existing end date")
        if not _date_ranges_overlap(start_date, end_date, other_start_date, other_end_date):
            continue
        other_start = _time_to_minutes(row["start_time"], "Existing start time")
        other_end = _time_to_minutes(row["end_time"], "Existing end time")
        if not _time_ranges_overlap(wanted_start, wanted_end, other_start, other_end):
            continue
        if int(row["group_id"]) == int(group_v2_id):
            return f"Group {row['group_name']} already has a class during that time."
        teacher_name = str(row["teacher_name"] or "Teacher").strip()
        return f"{teacher_name} already has a class during that time."
    return ""
