"""Runtime raw-SQL helpers for the internal academic admin model.

All reads and writes target the clean ``msi_v2`` schema. The admin gradebook
and dashboards (in ``academic_service`` / ``internal_dashboard_service``) read
from ``msi_v2`` as well; the write helpers here keep the same return shapes the
frontend already consumes so nothing on the admin pages breaks.
"""

from datetime import datetime, time, timedelta

from database.academics import canonical
from database import queries


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    return queries.connect_auth_db()


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
    ``backend.identity.storage.ensure_clean_v2_schema``. A few call sites still
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
    row = conn.execute(
        f"SELECT coalesce(max({column}), 0) AS m FROM msi_v2.{table}"
    ).fetchone()
    return max(int(row["m"] or 0), floor) + 1


# ---------------------------------------------------------------------------
# Resolvers (accept legacy or v2 ids coming from the frontend)
# ---------------------------------------------------------------------------
_GROUP_MATCH = "(g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))"


def _resolve_group(conn, group_id):
    return conn.execute(
        f"""
        SELECT g.id, g.school_id, g.program_id, g.group_name,
               s.school_key, s.school_name,
               subj.id AS subject_id, subj.subject_name
        FROM msi_v2.groups g
        JOIN msi_v2.schools s ON s.id = g.school_id
        JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
        JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
        WHERE {_GROUP_MATCH}
        """,
        (int(group_id or 0), int(group_id or 0)),
    ).fetchone()


def _resolve_teacher_id(conn, teacher_id):
    """Resolve an incoming (legacy or v2) teacher id to the msi_v2 teachers.id."""
    teacher_id = int(teacher_id or 0)
    if teacher_id <= 0:
        return 0
    row = conn.execute(
        "SELECT id FROM msi_v2.teachers WHERE legacy_teacher_id = %s OR id = %s LIMIT 1",
        (teacher_id, teacher_id),
    ).fetchone()
    if not row:
        raise ValueError("Teacher was not found.")
    return int(row["id"])


def _next_student_code(conn, prefix="MSI"):
    normalized_prefix = str(prefix or "MSI").strip().upper() or "MSI"
    rows = conn.execute(
        "SELECT student_code FROM msi_v2.students WHERE upper(student_code) LIKE %s",
        (f"{normalized_prefix}%",),
    ).fetchall()
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
        text = str(item or "").strip().casefold()
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
    conn, *, group_v2_id, teacher_v2_id, weekdays, start_date, end_date, start_time, end_time
):
    rows = conn.execute(
        """
        SELECT sch.id, sch.group_id, sch.teacher_id, sch.weekdays,
               to_char(sch.start_date, 'DD/MM/YYYY') AS start_date,
               to_char(sch.end_date, 'DD/MM/YYYY') AS end_date,
               to_char(sch.start_time, 'HH24:MI') AS start_time,
               to_char(sch.end_time, 'HH24:MI') AS end_time,
               g.group_name AS group_name,
               coalesce(t.full_name, '') AS teacher_name
        FROM msi_v2.group_schedule_rules sch
        JOIN msi_v2.groups g ON g.id = sch.group_id
        LEFT JOIN msi_v2.teachers t ON t.id = sch.teacher_id
        WHERE sch.status = 'active'
          AND (sch.group_id = %s OR (%s > 0 AND sch.teacher_id = %s))
        """,
        (int(group_v2_id), int(teacher_v2_id or 0), int(teacher_v2_id or 0)),
    ).fetchall()
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
def list_academic_admin_rows():
    with _connect() as conn:
        schools = [
            dict(row)
            for row in conn.execute(
                "SELECT id, school_key AS code, school_name AS name FROM msi_v2.schools ORDER BY school_name"
            ).fetchall()
        ]
        subjects = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, subject_name AS name, subject_key AS key,
                       subject_short AS code, subject_short AS short_name
                FROM msi_v2.subjects
                WHERE status = 'active'
                ORDER BY subject_name
                """
            ).fetchall()
        ]
        groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT coalesce(g.legacy_group_id, g.id) AS id,
                       g.school_id, s.school_key AS school_code,
                       subj.id AS subject_id, subj.subject_name AS subject_name,
                       g.group_name AS name, g.group_code AS code,
                       count(*) FILTER (WHERE gs.enrollment_status = 'active') AS students_count,
                       count(*) FILTER (WHERE gs.enrollment_status = 'disqualified') AS disqualified_count
                FROM msi_v2.groups g
                JOIN msi_v2.schools s ON s.id = g.school_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                LEFT JOIN msi_v2.group_students gs ON gs.group_id = g.id
                WHERE lower(g.group_name) <> 'online'
                GROUP BY g.id, g.legacy_group_id, g.school_id, s.school_key, s.school_name,
                         subj.id, subj.subject_name, g.group_name, g.group_code
                ORDER BY s.school_name, subj.subject_name, g.group_name
                """
            ).fetchall()
        ]
        enrollments = [
            dict(row)
            for row in conn.execute(
                """
                SELECT gs.legacy_enrollment_id AS id,
                       coalesce(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                       st.full_name,
                       g.school_id, s.school_key AS school_code, s.school_name,
                       subj.id AS subject_id, subj.subject_name,
                       coalesce(g.legacy_group_id, g.id) AS group_id, g.group_name,
                       (gs.enrollment_status = 'active') AS active, gs.enrollment_status
                FROM msi_v2.group_students gs
                JOIN msi_v2.students st ON st.id = gs.student_id
                JOIN msi_v2.groups g ON g.id = gs.group_id
                JOIN msi_v2.schools s ON s.id = g.school_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                WHERE lower(g.group_name) <> 'online'
                  AND gs.enrollment_status = 'active'
                  AND gs.legacy_enrollment_id IS NOT NULL
                ORDER BY s.school_name, subj.subject_name, g.group_name, st.full_name
                """
            ).fetchall()
        ]
        enrollment_summary = dict(
            conn.execute(
                """
                SELECT
                  count(*) FILTER (WHERE gs.enrollment_status = 'active') AS active_enrollments,
                  count(DISTINCT lower(trim(st.full_name))) FILTER (
                    WHERE gs.enrollment_status = 'active' AND trim(st.full_name) <> ''
                  ) AS active_unique_students,
                  count(*) FILTER (WHERE gs.enrollment_status = 'disqualified') AS disqualified_enrollments
                FROM msi_v2.group_students gs
                JOIN msi_v2.students st ON st.id = gs.student_id
                JOIN msi_v2.groups g ON g.id = gs.group_id
                WHERE lower(g.group_name) <> 'online'
                """
            ).fetchone()
            or {}
        )
        duplicate_names = int(enrollment_summary.get("active_enrollments") or 0) - int(
            enrollment_summary.get("active_unique_students") or 0
        )
        enrollment_summary["active_duplicate_enrollments"] = max(0, duplicate_names)
        lessons = [
            dict(row)
            for row in conn.execute(
                """
                SELECT ls.id, g.school_id, subj.id AS subject_id,
                       coalesce(g.legacy_group_id, g.id) AS group_id,
                       s.school_key AS school_code, subj.subject_name,
                       g.group_name, spi.lesson_number, spi.title AS lesson_topic,
                       coalesce(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                       spi.item_order AS lesson_order
                FROM msi_v2.lesson_sessions ls
                JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
                JOIN msi_v2.groups g ON g.id = ls.group_id
                JOIN msi_v2.schools s ON s.id = g.school_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                WHERE spi.item_type = 'lesson' AND lower(g.group_name) <> 'online'
                ORDER BY s.school_name, subj.subject_name, g.group_name, spi.item_order
                """
            ).fetchall()
        ]
        schedules = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sch.id, g.school_id, s.school_key AS school_code, s.school_name,
                       subj.id AS subject_id, subj.subject_name,
                       coalesce(g.legacy_group_id, g.id) AS group_id, g.group_name,
                       coalesce(t.legacy_teacher_id, t.id) AS teacher_id,
                       coalesce(t.full_name, '') AS teacher_name,
                       sch.title, sch.weekdays,
                       coalesce(to_char(sch.start_time, 'HH24:MI'), '') AS start_time,
                       coalesce(to_char(sch.end_time, 'HH24:MI'), '') AS end_time,
                       coalesce(to_char(sch.start_date, 'DD/MM/YYYY'), '') AS start_date,
                       coalesce(to_char(sch.end_date, 'DD/MM/YYYY'), '') AS end_date,
                       sch.room, sch.online_url, sch.status
                FROM msi_v2.group_schedule_rules sch
                JOIN msi_v2.groups g ON g.id = sch.group_id
                JOIN msi_v2.schools s ON s.id = g.school_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                LEFT JOIN msi_v2.teachers t ON t.id = sch.teacher_id
                WHERE lower(g.group_name) <> 'online'
                ORDER BY s.school_name, subj.subject_name, g.group_name, sch.start_time
                """
            ).fetchall()
        ]
        sessions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT ls.id, ls.schedule_rule_id AS schedule_id, ls.program_item_id AS lesson_id,
                       g.school_id, s.school_key AS school_code, s.school_name,
                       subj.id AS subject_id, subj.subject_name,
                       coalesce(g.legacy_group_id, g.id) AS group_id, g.group_name,
                       coalesce(t.legacy_teacher_id, t.id) AS teacher_id,
                       coalesce(t.full_name, '') AS teacher_name,
                       coalesce(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS session_date,
                       coalesce(to_char(ls.start_time, 'HH24:MI'), '') AS start_time,
                       coalesce(to_char(ls.end_time, 'HH24:MI'), '') AS end_time,
                       ls.room, ls.online_url, ls.status
                FROM msi_v2.lesson_sessions ls
                JOIN msi_v2.groups g ON g.id = ls.group_id
                JOIN msi_v2.schools s ON s.id = g.school_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                LEFT JOIN msi_v2.teachers t ON t.id = ls.teacher_id
                WHERE (ls.schedule_rule_id IS NOT NULL
                       OR (ls.start_time IS NOT NULL AND ls.end_time IS NOT NULL))
                  AND lower(g.group_name) <> 'online'
                ORDER BY ls.session_date, ls.start_time, s.school_name, g.group_name
                """
            ).fetchall()
        ]
        curriculum_programs = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sp.id, subj.subject_key, subj.subject_name, subj.subject_short,
                       sp.source_file, sp.total_items, sp.lesson_count, sp.exam_count,
                       sp.updated_at::text AS updated_at,
                       1 AS db_subject_count,
                       (
                         SELECT count(*) FROM msi_v2.groups g
                         WHERE g.program_id = sp.id AND lower(g.group_name) <> 'online'
                       ) AS group_count
                FROM msi_v2.subject_programs sp
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                WHERE sp.status = 'active'
                ORDER BY subj.subject_name
                """
            ).fetchall()
        ]
        curriculum_items = [
            dict(row)
            for row in conn.execute(
                """
                SELECT spi.id, spi.program_id, subj.subject_key, subj.subject_name,
                       spi.item_order, spi.lesson_number, spi.item_type, spi.title,
                       spi.term_label, spi.week_label, spi.specification_points,
                       spi.book_pages, spi.lesson_count, spi.duration_hours
                FROM msi_v2.subject_program_items spi
                JOIN msi_v2.subject_programs sp ON sp.id = spi.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                ORDER BY subj.subject_name, spi.item_order
                """
            ).fetchall()
        ]
        return {
            "schools": schools,
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
        existing = conn.execute(
            "SELECT id FROM msi_v2.schools WHERE lower(school_key) = lower(%s)",
            (code_value,),
        ).fetchone()
        if existing:
            raise ValueError(f"A client school with code '{code_value}' already exists.")
        conn.execute(
            "INSERT INTO msi_v2.schools (school_key, school_name) VALUES (%s, %s)",
            (code_value, name),
        )
        conn.commit()


def create_subject(school_code, name, code=""):
    # Subjects are universal in msi_v2; the school_code is accepted for backward
    # compatibility with the old per-school form but no longer scopes the row.
    name = _canonical_subject_name(name)
    key = _canonical_subject_key(name)
    short_name = _canonical_subject_short(name)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO msi_v2.subjects (subject_key, subject_name, subject_short, status)
            VALUES (%s, %s, %s, 'active')
            ON CONFLICT ((lower(subject_key))) DO UPDATE SET
              subject_name = excluded.subject_name,
              subject_short = excluded.subject_short,
              status = 'active',
              updated_at = now()
            """,
            (key, name, short_name),
        )
        conn.commit()


def create_group_from_program(school_code, program_subject_key, group_name, group_code=""):
    group_name = str(group_name or "Group").strip() or "Group"
    with _connect() as conn:
        school = conn.execute(
            "SELECT id FROM msi_v2.schools WHERE lower(school_key) = lower(%s)",
            (school_code,),
        ).fetchone()
        if not school:
            raise ValueError("Client school was not found.")
        program = conn.execute(
            """
            SELECT sp.id
            FROM msi_v2.subject_programs sp
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            WHERE lower(subj.subject_key) = lower(%s) AND sp.status = 'active'
            ORDER BY sp.id DESC
            LIMIT 1
            """,
            (program_subject_key,),
        ).fetchone()
        if not program:
            raise ValueError("Subject program was not found.")
        existing = conn.execute(
            """
            SELECT id FROM msi_v2.groups
            WHERE school_id = %s AND program_id = %s AND lower(group_name) = lower(%s)
            """,
            (int(school["id"]), int(program["id"]), group_name),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE msi_v2.groups SET group_code = %s, updated_at = now() WHERE id = %s",
                (str(group_code or ""), int(existing["id"])),
            )
        else:
            legacy_group_id = _mint_legacy_id(conn, "groups", "legacy_group_id")
            conn.execute(
                """
                INSERT INTO msi_v2.groups (school_id, program_id, group_name, group_code, status, legacy_group_id)
                VALUES (%s, %s, %s, %s, 'active', %s)
                """,
                (int(school["id"]), int(program["id"]), group_name, str(group_code or ""), legacy_group_id),
            )
        conn.commit()


def create_student_with_enrollment(full_name, group_id):
    """Create a student login identity and enroll them into a group.

    Reuses an existing student (same normalized name + school) instead of minting
    a duplicate code, then writes a ``group_students`` row with freshly minted
    legacy ids so the student immediately shows in the group's gradebook.
    """
    from werkzeug.security import generate_password_hash

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
        for candidate in conn.execute(
            "SELECT id, full_name, student_code FROM msi_v2.students WHERE school_id = %s",
            (school_id,),
        ).fetchall():
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
            inserted = conn.execute(
                """
                INSERT INTO msi_v2.students (
                    student_code, full_name, school_id, status,
                    password_plain, legacy_student_row_id
                )
                VALUES (%s, %s, %s, 'active', %s, %s)
                RETURNING id
                """,
                (student_code, full_name, school_id, default_password, legacy_student_row_id),
            ).fetchone()
            student_id = int(inserted["id"])
            conn.execute(
                """
                INSERT INTO msi_v2.student_auth (student_id, password_hash, must_change_password, updated_at)
                VALUES (%s, %s, false, now())
                ON CONFLICT (student_id) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    updated_at = now()
                """,
                (student_id, generate_password_hash(default_password)),
            )

        next_enrollment_id = _mint_legacy_id(conn, "group_students", "legacy_enrollment_id")
        next_dashboard_id = _mint_legacy_id(conn, "group_students", "legacy_public_dashboard_id")
        enrollment = conn.execute(
            """
            INSERT INTO msi_v2.group_students (
                group_id, student_id, enrollment_status, joined_at,
                legacy_enrollment_id, legacy_public_dashboard_id
            )
            VALUES (%s, %s, 'active', now(), %s, %s)
            ON CONFLICT (group_id, student_id) DO UPDATE SET
                enrollment_status = 'active',
                left_at = NULL
            RETURNING legacy_enrollment_id
            """,
            (v2_group_id, student_id, next_enrollment_id, next_dashboard_id),
        ).fetchone()
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
    start_date="",
    end_date="",
    room="",
    online_url="",
    title="",
):
    group_id = int(group_id or 0)
    weekdays = _normalize_weekdays(weekdays)
    start_date_obj = _parse_date_input(start_date, "Start date")
    end_date_obj = _parse_date_input(end_date, "End date")
    if end_date_obj < start_date_obj:
        raise ValueError("End date cannot be earlier than start date.")
    if (end_date_obj - start_date_obj).days > 366:
        raise ValueError("Schedule range cannot be longer than one year.")
    start_minutes = _time_to_minutes(start_time, "Start time")
    end_minutes = _time_to_minutes(end_time, "End time")
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

        conflict = _schedule_conflict_message(
            conn,
            group_v2_id=v2_group_id,
            teacher_v2_id=teacher_v2_id,
            weekdays=weekdays,
            start_date=start_date_obj,
            end_date=end_date_obj,
            start_time=start_time,
            end_time=end_time,
        )
        if conflict:
            raise ValueError(conflict)

        inserted_rule = conn.execute(
            """
            INSERT INTO msi_v2.group_schedule_rules (
              group_id, teacher_id, title, weekdays, start_time, end_time,
              start_date, end_date, room, online_url, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
            RETURNING id
            """,
            (
                v2_group_id,
                teacher_v2_id or None,
                title,
                weekdays_text,
                start_time_obj,
                end_time_obj,
                start_date_obj,
                end_date_obj,
                room,
                online_url,
            ),
        ).fetchone()
        schedule_id = int(inserted_rule["id"]) if inserted_rule else 0

        session_ids = []
        for session_date in generated_dates:
            session_cur = conn.execute(
                """
                INSERT INTO msi_v2.lesson_sessions (
                  group_id, schedule_rule_id, teacher_id, session_date,
                  start_time, end_time, room, online_url, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'scheduled')
                RETURNING id
                """,
                (
                    v2_group_id,
                    schedule_id,
                    teacher_v2_id or None,
                    session_date,
                    start_time_obj,
                    end_time_obj,
                    room,
                    online_url,
                ),
            ).fetchone()
            if session_cur:
                session_ids.append(int(session_cur["id"] or 0))
        conn.commit()

    return {
        "scheduleId": schedule_id,
        "sessionCount": len(generated_dates),
        "sessionIds": [session_id for session_id in session_ids if session_id],
    }
