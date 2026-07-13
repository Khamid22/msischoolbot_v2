"""Runtime helpers for the internal academic admin model.

Query modules own the SQL; this service keeps the same return shapes the
frontend already consumes so nothing on the admin pages breaks.
"""

from datetime import date, datetime, time, timedelta, timezone

from backend.core.database import connect_auth_db
from backend.modules.academics import canonical
from backend.modules.academics import repository as academic_repository
from backend.modules.academics import timetable_repository


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return connect_auth_db()


def group_belongs_to_school(group_name, school_code):
    normalized_group = str(group_name or "").strip()
    normalized_school = canonical.normalize_school_code(school_code, default="")
    if not normalized_group or not normalized_school or normalized_school == "all":
        return True
    try:
        with _connect() as conn:
            return academic_repository.group_belongs_to_school(
                conn,
                normalized_group,
                normalized_school,
            )
    except Exception:
        return True


def list_lesson_catalog_for_subject(subject_name):
    """Public academic read used by student-facing lesson catalog views."""

    with _connect() as conn:
        return list(
            academic_repository.list_lesson_catalog_rows_by_subject(
                conn,
                subject_name,
            )
        )


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
    ``backend.modules.accounts.bootstrap.ensure_clean_v2_schema``. A few call sites still
    invoke this helper; keep it as a no-op until they are cut over.
    """
    return None


# ---------------------------------------------------------------------------
# Legacy-id minting
# ---------------------------------------------------------------------------
# The frontend identifies enrollments, groups and dashboards by the integer
# ``legacy_*`` ids stored on the msi_v2 rows. Migrated rows keep their original
# id; rows created after the cutover get a fresh id in a high band so they never
# collide with migrated ids or with low-numbered msi_v2 primary keys.
_LEGACY_ID_FLOOR = 9_000_000_000


def _mint_legacy_id(conn, table, column, floor=_LEGACY_ID_FLOOR):
    return academic_repository.mint_legacy_id(conn, table, column, floor)


# ---------------------------------------------------------------------------
# Resolvers (accept legacy or v2 ids coming from the frontend)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Schedule helpers (date/time/weekday parsing + conflict detection)
# ---------------------------------------------------------------------------
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


def _generated_schedule_dates(start_date, end_date, weekdays):
    current = start_date
    wanted = set(weekdays)
    dates = []
    while current <= end_date:
        if current.weekday() in wanted:
            dates.append(current)
        current += timedelta(days=1)
    return dates


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


# ---------------------------------------------------------------------------
# Admin context (read)
# ---------------------------------------------------------------------------
def list_academic_admin_rows(*, include_heavy=True):
    with _connect() as conn:
        schools = [dict(row) for row in academic_repository.list_school_rows(conn)]
        classes = [dict(row) for row in academic_repository.list_class_rows(conn)]
        subjects = [dict(row) for row in academic_repository.list_subject_rows(conn)]
        groups = [dict(row) for row in academic_repository.list_group_rows(conn)]
        enrollment_summary = dict(academic_repository.get_enrollment_summary_row(conn) or {})
        duplicate_names = int(enrollment_summary.get("active_enrollments") or 0) - int(
            enrollment_summary.get("active_unique_students") or 0
        )
        enrollment_summary["active_duplicate_enrollments"] = max(0, duplicate_names)
        enrollments = []
        lessons = []
        schedules = []
        sessions = []
        curriculum_programs = []
        curriculum_items = []
        if include_heavy:
            enrollments = [dict(row) for row in academic_repository.list_enrollment_rows(conn)]
            lessons = [dict(row) for row in academic_repository.list_lesson_rows(conn)]
            schedules = [dict(row) for row in timetable_repository.list_schedule_rows(conn)]
            sessions = [dict(row) for row in timetable_repository.list_session_rows(conn)]
            curriculum_programs = [dict(row) for row in academic_repository.list_curriculum_program_rows(conn)]
            curriculum_items = [dict(row) for row in academic_repository.list_curriculum_item_rows(conn)]
        return {
            "schools": schools,
            "classes": classes,
            "subjects": subjects,
            "groups": groups,
            "enrollments": enrollments,
            "lessons": lessons,
            "schedules": schedules,
            "sessions": sessions,
            "curriculum_programs": curriculum_programs,
            "curriculum_items": curriculum_items,
            "enrollment_summary": enrollment_summary,
        }


# ---------------------------------------------------------------------------
# Admin context (write)
# ---------------------------------------------------------------------------
def create_school(name, code=""):
    import re

    name = str(name or "").strip()
    if not name:
        raise ValueError("School name is required.")
    code_value = str(code or "").strip().casefold()
    if not code_value:
        code_value = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "school"
    with _connect() as conn:
        existing = academic_repository.get_school_by_key(conn, code_value)
        if existing:
            raise ValueError(f"A client school with code '{code_value}' already exists.")
        academic_repository.insert_school(conn, code_value, name)
        conn.commit()


def create_subject(school_code, name, code=""):
    # Subjects are universal in msi_v2; the school_code is accepted for backward
    # compatibility with the old per-school form but no longer scopes the row.
    name = _canonical_subject_name(name)
    key = _canonical_subject_key(name)
    short_name = _canonical_subject_short(name)
    with _connect() as conn:
        academic_repository.upsert_subject(conn, key, name, short_name)
        conn.commit()


def create_class(school_code, class_name, class_code=""):
    class_name = str(class_name or "").strip()
    class_code = str(class_code or "").strip()
    if not class_name:
        raise ValueError("Class name is required.")
    with _connect() as conn:
        school = academic_repository.get_school_by_key(conn, school_code)
        if not school:
            raise ValueError("Client school was not found.")
        existing = academic_repository.get_class_by_school_and_name(
            conn, int(school["id"]), class_name
        )
        if existing:
            raise ValueError("A class with this name already exists in the selected school.")
        row = academic_repository.insert_class(
            conn, int(school["id"]), class_name, class_code
        )
        conn.commit()
        return dict(row)


def create_group_from_program(
    school_code, program_subject_key, group_name, group_code="", *, class_id=0, set_name="Set 1"
):
    group_name = str(group_name or "Group").strip() or "Group"
    with _connect() as conn:
        school = academic_repository.get_school_by_key(conn, school_code)
        if not school:
            raise ValueError("Client school was not found.")
        program = academic_repository.get_subject_program_by_subject_key(conn, program_subject_key)
        if not program:
            raise ValueError("Subject program was not found.")
        selected_class = None
        if int(class_id or 0) > 0:
            selected_class = academic_repository.get_class(conn, int(class_id))
            if not selected_class or int(selected_class["school_id"]) != int(school["id"]):
                raise ValueError("Class was not found in the selected school.")
            group_name = str(selected_class["class_name"])
        else:
            selected_class = academic_repository.get_class_by_school_and_name(
                conn, int(school["id"]), group_name
            )
            if not selected_class:
                selected_class = academic_repository.insert_class(
                    conn, int(school["id"]), group_name, group_code
                )
        existing = academic_repository.get_existing_group(conn, int(school["id"]), int(program["id"]), group_name)
        if existing:
            academic_repository.update_group_code(conn, int(existing["id"]), group_code)
            academic_repository.update_group_class(
                conn, int(existing["id"]), int(selected_class["id"]), set_name
            )
            group_v2_id = int(existing["id"])
        else:
            legacy_group_id = _mint_legacy_id(conn, "groups", "legacy_group_id")
            inserted_group = academic_repository.insert_group(
                conn,
                int(school["id"]),
                int(program["id"]),
                group_name,
                group_code,
                legacy_group_id,
                class_id=int(selected_class["id"]),
                set_name=set_name,
            )
            group_v2_id = int(inserted_group["id"])
        timetable_repository.ensure_curriculum_lesson_sessions(conn, group_v2_id)
        conn.commit()


def create_student_with_enrollment(full_name, group_id):
    """Create a student login identity and enroll them into a group.

    Reuses an existing student (same normalized name + school) instead of minting
    a duplicate code, then writes a ``group_students`` row with freshly minted
    legacy ids so the student immediately shows in the group's gradebook.
    """
    from backend.modules.accounts.service import provision_student_account

    full_name = str(full_name or "").strip()
    group_id = int(group_id or 0)
    if not full_name:
        raise ValueError("Student full name is required.")
    if group_id <= 0:
        raise ValueError("A group is required.")

    with _connect() as conn:
        group = _resolve_group(conn, group_id)
        if not group:
            raise ValueError("Group was not found.")

        v2_group_id = int(group["id"])
        school_id = int(group["school_id"])
        school_code = canonical.normalize_school_code(group["school_key"])
        school_name = str(group["school_name"] or canonical.school_display_name(school_code))
        subject_name = _canonical_subject_name(group["subject_name"])

        # Reuse an existing login for the same person (same normalized name +
        # school) so a person keeps one login across subjects/groups.
        target_norm = _normalize(full_name)
        existing_student = None
        for candidate in academic_repository.list_students_by_school_id(conn, school_id):
            if _normalize(candidate["full_name"]) == target_norm:
                existing_student = candidate
                break

        if existing_student:
            reused = True
            student_id = int(existing_student["id"])
            student_code = str(existing_student["student_code"] or "")
            default_password = ""  # unknown for an existing login
        else:
            reused = False
            student_code = _next_student_code(conn, canonical.student_code_prefix(school_code))
            default_password = student_code
            legacy_student_row_id = _mint_legacy_id(conn, "students", "legacy_student_row_id")
            inserted = academic_repository.insert_student(
                conn,
                student_code=student_code,
                full_name=full_name,
                school_id=school_id,
                legacy_student_row_id=legacy_student_row_id,
            )
            student_id = int(inserted["id"])
            account_id = provision_student_account(
                conn,
                student_id=student_id,
                login=student_code,
                initial_password=default_password,
                full_name=full_name,
                school_id=school_id,
            )
            if account_id <= 0:
                raise RuntimeError("Unable to provision the student account.")

        next_enrollment_id = _mint_legacy_id(conn, "group_students", "legacy_enrollment_id")
        next_dashboard_id = _mint_legacy_id(conn, "group_students", "legacy_public_dashboard_id")
        enrollment = academic_repository.upsert_group_student_enrollment(
            conn,
            group_id=v2_group_id,
            student_id=student_id,
            legacy_enrollment_id=next_enrollment_id,
            legacy_public_dashboard_id=next_dashboard_id,
        )
        if group.get("class_id"):
            academic_repository.upsert_class_student(conn, int(group["class_id"]), student_id)
        enrollment_id = int(enrollment["legacy_enrollment_id"] or next_enrollment_id) if enrollment else next_enrollment_id
        conn.commit()

    return {
        "studentRowId": int(student_id),
        "enrollmentId": int(enrollment_id),
        "studentCode": student_code,
        "password": default_password,
        "reused": reused,
        "fullName": full_name,
        "schoolName": school_name,
        "subjectName": subject_name,
        "groupName": str(group["group_name"]),
    }


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
    if predicted:
        with _connect() as prediction_conn:
            prediction_group = _resolve_group(prediction_conn, group_id)
            if not prediction_group:
                raise ValueError("Group was not found.")
            session_count = academic_repository.get_program_teaching_session_count(
                prediction_conn, int(prediction_group["program_id"])
            )
        if session_count <= 0:
            raise ValueError("The subject program has no lessons to schedule.")
        current = start_date_obj
        remaining = session_count
        selected_days = set(weekdays)
        while remaining > 0:
            if current.weekday() in selected_days:
                remaining -= 1
            if remaining > 0:
                current += timedelta(days=1)
        end_date_obj = current
    else:
        end_date_obj = _parse_date_input(end_date, "End date")
    if end_date_obj < start_date_obj:
        raise ValueError("End date cannot be earlier than start date.")
    if (end_date_obj - start_date_obj).days > 366:
        raise ValueError("Schedule range cannot be longer than one year.")
    if end_minutes <= start_minutes:
        raise ValueError("End time must be after start time.")

    generated_dates = _generated_schedule_dates(start_date_obj, end_date_obj, weekdays)
    if not generated_dates:
        raise ValueError("The selected date range does not contain the selected weekdays.")

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
        conn.commit()

    return {
        "scheduleId": schedule_id,
        "sessionCount": len(generated_dates),
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

        dates = []
        cursor = anchor
        wanted = set(weekdays)
        blocked_dates = {
            row["blocked_date"]
            for row in timetable_repository.list_blocked_group_dates(conn, v2_group_id)
            if row.get("blocked_date") is not None
        }
        while len(dates) < len(selected):
            if cursor.weekday() in wanted and cursor not in blocked_dates:
                dates.append(cursor)
            cursor += timedelta(days=1)
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
        conn.commit()
    return {
        "scheduleId": schedule_id, "affectedLessonCount": len(selected),
        "firstLessonDate": dates[0].isoformat(), "predictedEndDate": final_date.isoformat(),
        "lessonDurationMinutes": duration, "changeScope": scope or "initial",
        "courseLaunchDate": launch_date.isoformat(),
        "protectedLessonCount": protected_count,
        "movedRecordedLessonCount": moved_protected_count,
    }
