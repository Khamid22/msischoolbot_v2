"""Admin-facing academic operations and payload shaping."""

import re
from datetime import UTC, date, datetime, timedelta

from backend.core.database import connect_auth_db
from backend.modules.academics.exam_filters import is_exam_performance_row
from backend.modules.academics import canonical
from backend.modules.academics import timetable_repository
from backend.modules.academics.service import (
    create_group_from_program,
    create_class,
    create_schedule,
    create_school,
    create_student_with_enrollment,
    schedule_group_curriculum,
    create_subject,
    list_academic_admin_rows,
)


def list_admin_academic_context(*, include_heavy=True):
    return list_academic_admin_rows(include_heavy=include_heavy)


def create_subject_from_payload(payload):
    school_code = str(payload.get("school_code", "") or "").strip()
    subject_name = str(payload.get("subject_name", "") or "").strip()
    subject_code = str(payload.get("subject_code", "") or "").strip()
    if not school_code or not subject_name:
        raise ValueError("School and subject name are required.")
    create_subject(school_code, subject_name, subject_code)
    return {"school_code": school_code}


def create_group_from_payload(payload):
    school_code = str(payload.get("school_code", "") or "").strip()
    program_subject_key = str(payload.get("program_subject_key", "") or "").strip()
    raw_program_keys = payload.get("program_subject_keys", [])
    if isinstance(raw_program_keys, str):
        raw_program_keys = [raw_program_keys]
    program_subject_keys = [
        str(key or "").strip() for key in raw_program_keys if str(key or "").strip()
    ]
    if program_subject_key and program_subject_key not in program_subject_keys:
        program_subject_keys.append(program_subject_key)
    group_name = str(payload.get("group_name", "") or "").strip()
    group_code = str(payload.get("group_code", "") or "").strip()
    class_id = int(payload.get("class_id", 0) or 0)
    set_name = str(payload.get("set_name", "Set 1") or "Set 1").strip()
    if not school_code or not program_subject_keys or not group_name:
        raise ValueError("Client school, at least one subject program, and group name are required.")
    for subject_key in dict.fromkeys(program_subject_keys):
        create_group_from_program(
            school_code, subject_key, group_name, group_code,
            class_id=class_id, set_name=set_name,
        )
    return {"school_code": school_code}


def create_class_from_payload(payload):
    school_code = str(payload.get("school_code", "") or "").strip()
    class_name = str(payload.get("class_name", "") or "").strip()
    class_code = str(payload.get("class_code", "") or "").strip()
    if not school_code or not class_name:
        raise ValueError("Client school and class name are required.")
    return create_class(school_code, class_name, class_code)


def delete_group(group_id):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required.")

    with connect_auth_db() as conn:
        group_row = conn.execute(
            """
            SELECT g.id, coalesce(g.legacy_group_id, g.id) AS public_id,
                   g.group_name, g.group_code, s.school_key, subj.subject_name
            FROM msi_v2.groups g
            JOIN msi_v2.schools s ON s.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            WHERE """ + _legacy_or_v2_group_where() + """
            """,
            (group_id, group_id),
        ).fetchone()
        if not group_row:
            return None

        group_name = str(group_row["group_name"] or "").strip()
        if group_name.casefold() == "online":
            raise ValueError("The Online group cannot be deleted.")

        v2_group_id = int(group_row["id"])
        counts = {}
        for key, table in (
            ("enrollments", "group_students"),
            ("schedules", "group_schedule_rules"),
            ("lessons", "lesson_sessions"),
            ("attendance", "attendance_records"),
            ("homework", "homework_scores"),
            ("exams", "exam_results"),
        ):
            row = conn.execute(
                f"SELECT count(*) AS total FROM msi_v2.{table} WHERE group_id = %s",
                (v2_group_id,),
            ).fetchone()
            counts[key] = int(row["total"] or 0) if row else 0

        conn.execute("DELETE FROM msi_v2.groups WHERE id = %s", (v2_group_id,))
        conn.commit()

    return {
        "id": int(group_row["public_id"]),
        "name": group_name,
        "code": str(group_row["group_code"] or "").strip(),
        "school_code": str(group_row["school_key"] or "").strip(),
        "subject_name": str(group_row["subject_name"] or "").strip(),
        "deleted": counts,
    }


def create_school_from_payload(payload):
    name = str(payload.get("school_name", "") or "").strip()
    code = str(payload.get("school_code", "") or "").strip()
    if not name:
        raise ValueError("School name is required.")
    create_school(name, code)
    return {"name": name}


def create_student_with_enrollment_from_payload(payload):
    full_name = str(payload.get("full_name", "") or "").strip()
    group_id = int(payload.get("group_id", 0) or 0)
    if not full_name or group_id <= 0:
        raise ValueError("Student name and group are required.")
    return create_student_with_enrollment(full_name, group_id)


def create_schedule_from_payload(payload):
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
    )
    return result


def upsert_group_schedule_from_payload(group_id, payload):
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
    )


def _now():
    return datetime.now(UTC)


def _legacy_or_v2_group_where():
    return "(g.legacy_group_id = %s OR (g.legacy_group_id IS NULL AND g.id = %s))"


def _legacy_or_v2_enrollment_where():
    return "(gs.legacy_enrollment_id = %s)"


def _lesson_order_from_label(value):
    match = re.search(r"(\d+)", str(value or ""))
    if not match:
        return 0
    return int(match.group(1))


def _get_v2_enrollment(conn, enrollment_id):
    return conn.execute(
        f"""
        SELECT gs.group_id, gs.student_id, gs.legacy_enrollment_id, gs.enrollment_status,
               g.legacy_group_id, g.id AS v2_group_id,
               g.school_id, g.program_id
        FROM msi_v2.group_students gs
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE {_legacy_or_v2_enrollment_where()}
        """,
        (int(enrollment_id),),
    ).fetchone()


def _get_v2_lesson_session(conn, group_id, lesson_label):
    lesson_order = _lesson_order_from_label(lesson_label)
    if lesson_order <= 0:
        raise ValueError("Lesson label must include a lesson number.")
    row = conn.execute(
        """
        SELECT ls.id, spi.lesson_number, ls.status, ls.source_kind, ls.program_item_id
        FROM msi_v2.lesson_sessions ls
        JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE ls.group_id = %s
          AND spi.item_type = 'lesson'
          AND spi.item_order = %s
        ORDER BY ls.id
        LIMIT 1
        """,
        (int(group_id), lesson_order),
    ).fetchone()
    if not row:
        raise ValueError("Lesson not found in the clean subject program.")
    return row


def _get_v2_lesson_session_by_id(conn, group_id, lesson_session_id):
    lesson_session_id = int(lesson_session_id or 0)
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    row = conn.execute(
        """
        SELECT ls.id, COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_number,
               ls.status, ls.source_kind, ls.program_item_id
        FROM msi_v2.lesson_sessions ls
        LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
        WHERE ls.group_id = %s AND ls.id = %s
        LIMIT 1
        """,
        (int(group_id), lesson_session_id),
    ).fetchone()
    if not row:
        raise ValueError("Lesson session was not found.")
    return row


def _lesson_session_for_payload(conn, enrollment, payload):
    lesson_session_id = int(payload.get("lesson_session_id") or payload.get("lesson_id") or 0)
    if lesson_session_id > 0:
        return _get_v2_lesson_session_by_id(conn, enrollment["group_id"], lesson_session_id)
    return _get_v2_lesson_session(conn, enrollment["group_id"], payload.get("lesson_label", ""))


def _parse_optional_lesson_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    parsed = canonical.parse_date(text)
    if not parsed:
        raise ValueError("Lesson date must be a valid date.")
    return parsed


def _normalize_lesson_status(value):
    status = str(value or "").strip().casefold()
    if status in {"", "scheduled", "completed", "cancelled", "canceled"}:
        return "cancelled" if status == "canceled" else status
    raise ValueError("Unsupported lesson status.")


_LESSON_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _parse_optional_lesson_time(value):
    """Normalize an HH:MM string; empty string clears the time (returns None)."""
    text = str(value or "").strip()
    if not text:
        return None
    if not _LESSON_TIME_RE.match(text):
        raise ValueError("Lesson time must be in HH:MM format.")
    return text.zfill(5)


def _gradebook_lesson_payload(lesson_rows, exception_rows):
    items = [
        {
            "id": int(row["id"]),
            "lessonNumber": str(row["lesson_number"]),
            "topic": str(row["topic"] or ""),
            "date": str(row["lesson_date"] or ""),
            "startTime": str(row["start_time"] or ""),
            "endTime": str(row["end_time"] or ""),
            "room": str(row["room"] or ""),
            "order": int(row["lesson_order"] or 0),
            "status": str(row["status"] or "scheduled"),
            "sourceKind": str(row["source_kind"] or ""),
            "hasHomework": bool(row["has_homework"]),
            "isCancellation": False,
            "cancellationReason": "",
            "exceptionId": None,
            "canRecover": False,
        }
        for row in lesson_rows
    ]
    items.extend(
        {
            "id": -int(row["id"]),
            "lessonSessionId": int(row["lesson_session_id"]),
            "lessonNumber": f"{str(row['lesson_number'])} (Cancelled)",
            "topic": str(row["reason"] or ""),
            "date": str(row["lesson_date"] or ""),
            "startTime": str(row["start_time"] or ""),
            "endTime": str(row["end_time"] or ""),
            "room": str(row["room"] or ""),
            "order": int(row["lesson_order"] or 0),
            "status": "cancelled",
            "sourceKind": "cancellation",
            "hasHomework": False,
            "isCancellation": True,
            "cancellationReason": str(row["reason"] or ""),
            "exceptionId": int(row["id"]),
            "canRecover": True,
        }
        for row in exception_rows
    )

    def sort_key(item):
        raw = str(item.get("date") or "")
        try:
            parsed = datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            parsed = datetime.max.date()
        return (parsed, str(item.get("startTime") or ""), 0 if item.get("isCancellation") else 1, int(item.get("order") or 0))

    items.sort(key=sort_key)
    return items


def _gradebook_lesson_window(items, *, limit=0, cursor="", direction="", anchor_date=""):
    total = len(items)
    limit = max(0, min(int(limit or 0), 40))
    if limit <= 0 or total <= limit:
        return items, {
            "totalLessons": total,
            "startIndex": 0,
            "endIndex": total,
            "previousCursor": None,
            "nextCursor": None,
            "hasPrevious": False,
            "hasNext": False,
        }
    start = None
    cursor_text = str(cursor or "").strip().lower()
    if cursor_text:
        raw_offset = cursor_text[1:] if cursor_text.startswith("o") else cursor_text
        try:
            start = max(0, min(int(raw_offset), max(0, total - limit)))
        except ValueError:
            raise ValueError("Invalid Gradebook lesson cursor.")
        normalized_direction = str(direction or "").strip().casefold()
        if normalized_direction == "previous":
            start = max(0, start - limit)
        elif normalized_direction == "next":
            start = min(max(0, total - limit), start + limit)
        elif normalized_direction not in {"", "current"}:
            raise ValueError("Invalid Gradebook lesson direction.")
    if start is None:
        anchor = canonical.parse_date(anchor_date) if str(anchor_date or "").strip() else date.today()
        if not anchor:
            raise ValueError("anchor_date must be a valid date.")
        anchor_index = 0
        for index, item in enumerate(items):
            parsed = canonical.parse_date(item.get("date"))
            if parsed and parsed >= anchor:
                anchor_index = index
                break
        start = max(0, min(anchor_index - (limit // 2), max(0, total - limit)))
    end = min(total, start + limit)
    previous_start = max(0, start - limit)
    next_start = min(max(0, total - limit), start + limit)
    return items[start:end], {
        "totalLessons": total,
        "startIndex": start,
        "endIndex": end,
        "previousCursor": f"o{previous_start}" if start > 0 else None,
        "nextCursor": f"o{next_start}" if end < total else None,
        "hasPrevious": start > 0,
        "hasNext": end < total,
    }


def get_group_gradebook(
    group_id, *, lesson_limit=0, lesson_cursor="", lesson_direction="",
    anchor_date="", section="all"
):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required")

    with connect_auth_db() as conn:
        group_row = conn.execute(
            """
            SELECT g.id, g.legacy_group_id, g.group_name, g.group_code,
                   s.school_key, subj.subject_name,
                   (SELECT count(*) FROM (
                      SELECT lower(btrim(exam_item.title)) AS exam_key
                      FROM msi_v2.subject_program_items exam_item
                      WHERE exam_item.program_id = g.program_id AND exam_item.item_type = 'exam'
                      UNION
                      SELECT lower(btrim(result.exam_name)) AS exam_key
                      FROM msi_v2.exam_results result
                      WHERE result.group_id = g.id AND btrim(result.exam_name) <> ''
                    ) known_exams) AS exam_count
            FROM msi_v2.groups g
            JOIN msi_v2.schools s ON s.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
            WHERE """ + _legacy_or_v2_group_where() + """
            """,
            (group_id, group_id),
        ).fetchone()
        if not group_row:
            return None

        lesson_rows = conn.execute(
            """
            WITH ranked_sessions AS (
                SELECT ls.id,
                       ls.program_item_id,
                       COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, 'Session') AS lesson_number,
                       COALESCE(NULLIF(ls.source_topic, ''), spi.title, '') AS topic,
                       COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                       ls.session_date,
                       COALESCE(to_char(ls.start_time, 'HH24:MI'), '') AS start_time,
                       COALESCE(to_char(ls.end_time, 'HH24:MI'), '') AS end_time,
                       COALESCE(ls.room, '') AS room,
                       COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999) AS lesson_order,
                       ls.status,
                       COALESCE(NULLIF(ls.source_kind, ''), spi.item_type, 'session') AS source_kind,
                       CASE
                         WHEN COALESCE(NULLIF(ls.source_kind, ''), spi.item_type, '') = 'lesson' THEN true
                         WHEN ls.program_item_id IS NOT NULL AND spi.item_type = 'lesson' THEN true
                         ELSE false
                       END AS has_homework,
                       ROW_NUMBER() OVER (
                         PARTITION BY COALESCE(ls.program_item_id, -ls.id)
                         ORDER BY CASE WHEN ls.source_key <> '' THEN 0 ELSE 1 END,
                                  COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999),
                                  ls.session_date NULLS LAST,
                                  ls.id
                       ) AS session_rank
                FROM msi_v2.lesson_sessions ls
                LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
                WHERE ls.group_id = %s
                  AND (
                    spi.item_type = 'lesson'
                    OR (ls.program_item_id IS NULL AND ls.source_key <> '')
                  )
            )
            SELECT ls.id,
                   ls.lesson_number,
                   ls.topic,
                   ls.lesson_date,
                   ls.start_time,
                   ls.end_time,
                   ls.room,
                   ls.lesson_order,
                   ls.status,
                   ls.source_kind,
                   ls.has_homework
            FROM ranked_sessions ls
            WHERE ls.session_rank = 1
            ORDER BY ls.lesson_order,
                     ls.session_date NULLS LAST,
                     ls.id
            """,
            (int(group_row["id"]),),
        ).fetchall()

        exception_rows = conn.execute(
            """
            SELECT e.id, e.lesson_session_id,
                   COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, 'Lesson') AS lesson_number,
                   to_char(e.original_session_date, 'DD/MM/YYYY') AS lesson_date,
                   COALESCE(to_char(e.original_start_time, 'HH24:MI'), '') AS start_time,
                   COALESCE(to_char(e.original_end_time, 'HH24:MI'), '') AS end_time,
                   COALESCE(ls.room, '') AS room,
                   COALESCE(NULLIF(ls.source_order, 0), spi.item_order, 999999) AS lesson_order,
                   e.reason
            FROM msi_v2.lesson_schedule_exceptions e
            JOIN msi_v2.lesson_sessions ls ON ls.id=e.lesson_session_id
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id=ls.program_item_id
            WHERE e.group_id=%s AND e.status='cancelled'
            ORDER BY e.original_session_date, e.id
            """,
            (int(group_row["id"]),),
        ).fetchall()

        full_lesson_payload = _gradebook_lesson_payload(lesson_rows, exception_rows)
        normalized_section = str(section or "all").strip().casefold()
        if normalized_section not in {"all", "gradebook", "academic", "exams", "timetable"}:
            raise ValueError("Unsupported Gradebook section.")
        if normalized_section == "gradebook" or int(lesson_limit or 0) > 0:
            lesson_payload, page_info = _gradebook_lesson_window(
                full_lesson_payload,
                limit=lesson_limit,
                cursor=lesson_cursor,
                direction=lesson_direction,
                anchor_date=anchor_date,
            )
        else:
            lesson_payload, page_info = _gradebook_lesson_window(full_lesson_payload, limit=0)
        record_lesson_ids = [int(item["id"]) for item in lesson_payload if int(item["id"]) > 0]

        enrollment_rows = conn.execute(
            """
            SELECT gs.group_id, gs.student_id, gs.legacy_enrollment_id,
                   s.legacy_public_dashboard_id, s.full_name, gs.enrollment_status,
                   gs.disqualification_reason,
                   COALESCE(to_char(gs.disqualified_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS disqualified_at,
                   COALESCE(hw.average_grade, 0) AS average_grade,
                   COALESCE(coins.total_coins, 0) AS coins
            FROM msi_v2.group_students gs
            JOIN msi_v2.students s ON s.id = gs.student_id
            LEFT JOIN (
                SELECT group_id, student_id, round(avg(score)::numeric, 1) AS average_grade
                FROM msi_v2.homework_scores
                WHERE group_id = %s
                GROUP BY group_id, student_id
            ) hw ON hw.group_id = gs.group_id AND hw.student_id = gs.student_id
            LEFT JOIN (
                SELECT student_id, sum(amount)::int AS total_coins
                FROM msi_v2.coin_events
                WHERE group_id = %s
                GROUP BY student_id
            ) coins ON coins.student_id = gs.student_id
            WHERE gs.group_id = %s
            ORDER BY
              CASE gs.enrollment_status
                WHEN 'active' THEN 0
                WHEN 'disqualified' THEN 1
                WHEN 'banned' THEN 2
                ELSE 3
              END,
              s.full_name
            """,
            (int(group_row["id"]), int(group_row["id"]), int(group_row["id"])),
        ).fetchall()

        active_enrollment_rows = [
            row
            for row in enrollment_rows
            if str(row["enrollment_status"] or "active") == "active"
        ]
        enrollment_ids = [int(row["legacy_enrollment_id"] or 0) for row in enrollment_rows if row["legacy_enrollment_id"]]
        attendance_by_enrollment = {}
        attendance_by_lesson_id = {}
        homework_by_enrollment = {}
        homework_by_lesson_id = {}
        exams_by_enrollment = {}
        exam_attempts_by_enrollment = {}
        exam_dates_by_enrollment = {}
        exam_dates_by_label = {}
        exam_labels = []
        needs_lesson_records = normalized_section in {"all", "gradebook", "academic"}
        needs_exam_records = normalized_section in {"all", "exams"}
        if enrollment_ids and needs_lesson_records and record_lesson_ids:
            placeholders = ",".join(["%s"] * len(enrollment_ids))
            lesson_placeholders = ",".join(["%s"] * len(record_lesson_ids))
            for row in conn.execute(
                f"""
                SELECT gs.legacy_enrollment_id AS enrollment_id, ls.id AS lesson_session_id,
                       COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_label,
                       ar.attendance_status AS status
                FROM msi_v2.attendance_records ar
                JOIN msi_v2.group_students gs
                     ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
                JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
                LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
                WHERE gs.legacy_enrollment_id IN ({placeholders})
                  AND ar.lesson_session_id IN ({lesson_placeholders})
                  AND (
                    spi.item_type = 'lesson'
                    OR (ls.program_item_id IS NULL AND ls.source_key <> '')
                  )
                  AND COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') <> ''
                """,
                [*enrollment_ids, *record_lesson_ids],
            ).fetchall():
                attendance_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = str(row["status"])
                attendance_by_lesson_id.setdefault(int(row["enrollment_id"]), {})[
                    str(int(row["lesson_session_id"]))
                ] = str(row["status"])
            for row in conn.execute(
                f"""
                SELECT gs.legacy_enrollment_id AS enrollment_id, ls.id AS lesson_session_id,
                       COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_label,
                       hw.score
                FROM msi_v2.homework_scores hw
                JOIN msi_v2.group_students gs
                     ON gs.group_id = hw.group_id AND gs.student_id = hw.student_id
                JOIN msi_v2.lesson_sessions ls ON ls.id = hw.lesson_session_id
                LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
                WHERE gs.legacy_enrollment_id IN ({placeholders})
                  AND hw.lesson_session_id IN ({lesson_placeholders})
                  AND (
                    spi.item_type = 'lesson'
                    OR (ls.program_item_id IS NULL AND ls.source_key <> '')
                  )
                  AND COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') <> ''
                """,
                [*enrollment_ids, *record_lesson_ids],
            ).fetchall():
                homework_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = float(row["score"])
                homework_by_lesson_id.setdefault(int(row["enrollment_id"]), {})[
                    str(int(row["lesson_session_id"]))
                ] = float(row["score"])
        if enrollment_ids and needs_exam_records:
            placeholders = ",".join(["%s"] * len(enrollment_ids))
            for row in conn.execute(
                f"""
                SELECT gs.legacy_enrollment_id AS enrollment_id,
                       er.exam_name, er.attempt, er.score,
                       COALESCE(spi.item_type, '') AS item_type,
                       COALESCE(spi.title, '') AS item_title,
                       COALESCE(
                         to_char(exam_session.session_date, 'DD/MM/YYYY'),
                         to_char(er.created_at, 'DD/MM/YYYY'),
                         ''
                       ) AS exam_date
                FROM msi_v2.exam_results er
                JOIN msi_v2.group_students gs
                     ON gs.group_id = er.group_id AND gs.student_id = er.student_id
                LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
                LEFT JOIN LATERAL (
                    SELECT ls.session_date
                    FROM msi_v2.lesson_sessions ls
                    WHERE ls.group_id = er.group_id
                      AND ls.program_item_id = er.program_item_id
                    ORDER BY ls.session_date NULLS LAST, ls.id
                    LIMIT 1
                ) exam_session ON TRUE
                WHERE gs.legacy_enrollment_id IN ({placeholders})
                ORDER BY er.exam_name, er.attempt
                """,
                enrollment_ids,
            ).fetchall():
                label = str(row["exam_name"] or "").strip()
                if not is_exam_performance_row(
                    item_type=row["item_type"],
                    exam_name=row["exam_name"],
                    label=label,
                    title=row["item_title"],
                    attempt=row["attempt"],
                ):
                    continue
                if not label:
                    continue
                score = float(row["score"])
                attempt = str(row["attempt"] or "").strip()
                exam_date = str(row["exam_date"] or "").strip()
                exams_by_enrollment.setdefault(int(row["enrollment_id"]), {})[label] = score
                exam_attempts_by_enrollment.setdefault(int(row["enrollment_id"]), {})[label] = attempt
                exam_dates_by_enrollment.setdefault(int(row["enrollment_id"]), {})[label] = exam_date
                if label not in exam_dates_by_label or not exam_dates_by_label[label]:
                    exam_dates_by_label[label] = exam_date
                if label not in exam_labels:
                    exam_labels.append(label)

    return {
        "ok": True,
        "group": {
            "id": int(group_row["legacy_group_id"] or group_row["id"]),
            "name": str(group_row["group_name"]),
            "code": str(group_row["group_code"] or ""),
            "schoolCode": str(group_row["school_key"]),
            "subjectName": str(group_row["subject_name"]),
            "examCount": int(group_row["exam_count"] or 0),
        },
        "lessons": lesson_payload,
        "pageInfo": page_info,
        "examLabels": exam_labels,
        "examDates": exam_dates_by_label,
        "enrollments": [
            {
                "enrollmentId": int(row["legacy_enrollment_id"] or 0),
                "fullName": str(row["full_name"]),
                "averageGrade": float(row["average_grade"] or 0),
                "coins": int(row["coins"] or 0),
                "attendance": attendance_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "attendanceByLessonId": attendance_by_lesson_id.get(int(row["legacy_enrollment_id"] or 0), {}),
                "homework": homework_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "homeworkByLessonId": homework_by_lesson_id.get(int(row["legacy_enrollment_id"] or 0), {}),
                "exams": exams_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "examAttempts": exam_attempts_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "examDates": exam_dates_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
            }
            for row in active_enrollment_rows
            if int(row["legacy_enrollment_id"] or 0) > 0
        ],
        "allEnrollments": [
            {
                "enrollmentId": int(row["legacy_enrollment_id"] or 0),
                "publicDashboardId": int(row["legacy_public_dashboard_id"] or 0),
                "fullName": str(row["full_name"]),
                "averageGrade": float(row["average_grade"] or 0),
                "coins": int(row["coins"] or 0),
                "active": str(row["enrollment_status"] or "active") == "active",
                "status": str(row["enrollment_status"] or "active"),
                "disqualificationReason": str(row["disqualification_reason"] or ""),
                "disqualifiedAt": str(row["disqualified_at"] or ""),
                "exams": exams_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "examAttempts": exam_attempts_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "examDates": exam_dates_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
            }
            for row in enrollment_rows
            if int(row["legacy_enrollment_id"] or 0) > 0
        ],
    }


def update_enrollment_status(enrollment_id, status, reason=""):
    enrollment_id = int(enrollment_id or 0)
    if enrollment_id <= 0:
        raise ValueError("Enrollment id is required.")
    normalized_status = str(status or "").strip().casefold()
    if normalized_status not in {"active", "disqualified", "banned"}:
        raise ValueError("Unsupported enrollment status.")

    active = 1 if normalized_status == "active" else 0
    disqualification_reason = "" if normalized_status == "active" else str(reason or "").strip()
    if normalized_status == "banned" and not disqualification_reason:
        disqualification_reason = "Banned by admin"

    now = _now()
    disqualified_at = "" if normalized_status == "active" else now.strftime("%Y-%m-%dT%H:%M:%SZ")
    with connect_auth_db() as conn:
        row = _get_v2_enrollment(conn, enrollment_id)
        if not row:
            raise ValueError("Enrollment not found.")
        conn.execute(
            """
            UPDATE msi_v2.group_students
            SET enrollment_status = %s,
                disqualification_reason = %s,
                disqualified_at = CASE WHEN %s = 'active' THEN NULL ELSE COALESCE(disqualified_at, %s) END,
                left_at = CASE WHEN %s = 'active' THEN NULL ELSE COALESCE(left_at, %s) END
            WHERE group_id = %s AND student_id = %s
            """,
            (
                normalized_status,
                disqualification_reason,
                normalized_status,
                now,
                normalized_status,
                now,
                int(row["group_id"]),
                int(row["student_id"]),
            ),
        )
        conn.commit()

    return {
        "id": enrollment_id,
        "active": bool(active),
        "status": normalized_status,
        "disqualificationReason": disqualification_reason,
        "disqualifiedAt": disqualified_at,
    }


def move_enrollment_group(enrollment_id, group_id):
    enrollment_id = int(enrollment_id or 0)
    group_id = int(group_id or 0)
    if enrollment_id <= 0:
        raise ValueError("Enrollment id is required.")
    if group_id <= 0:
        raise ValueError("Target group is required.")

    with connect_auth_db() as conn:
        row = _get_v2_enrollment(conn, enrollment_id)
        if not row:
            raise ValueError("Enrollment not found.")
        target = conn.execute(
            """
            SELECT id, school_id, program_id
            FROM msi_v2.groups g
            WHERE """ + _legacy_or_v2_group_where() + """
            """,
            (group_id, group_id),
        ).fetchone()
        if not target:
            raise ValueError("Target group not found.")
        if int(target["school_id"]) != int(row["school_id"]):
            raise ValueError("Students can only move between groups in the same school.")
        if int(target["program_id"]) != int(row["program_id"]):
            raise ValueError("Students can only move between groups using the same subject program.")
        conn.execute(
            """
            DELETE FROM msi_v2.group_students
            WHERE group_id = %s AND student_id = %s
            """,
            (
                int(row["group_id"]),
                int(row["student_id"]),
            ),
        )
        conn.execute(
            """
            INSERT INTO msi_v2.group_students (
                group_id, student_id, enrollment_status, joined_at, legacy_enrollment_id
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (group_id, student_id) DO UPDATE SET
                enrollment_status = excluded.enrollment_status,
                legacy_enrollment_id = excluded.legacy_enrollment_id,
                left_at = NULL
            """,
            (
                int(target["id"]),
                int(row["student_id"]),
                str(row["enrollment_status"] or "active"),
                _now(),
                enrollment_id,
            ),
        )
        conn.commit()

    return {"id": enrollment_id, "groupId": group_id}


def record_attendance_from_payload(payload, actor_staff_id=None):
    enrollment_id = int(payload.get("enrollment_id", 0))
    status = str(payload.get("status", "") or "").strip().casefold()
    status_aliases = {
        "p": "present",
        "present": "present",
        "a": "absent",
        "absent": "absent",
        "j": "justified",
        "justified": "justified",
        "justified absent": "justified",
        "a(i)": "justified",
        "ai": "justified",
        "l": "justified",
        "late": "justified",
    }
    status = status_aliases.get(status, status)
    if status not in {"", "present", "absent", "justified"}:
        raise ValueError("Unsupported attendance status.")
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        lesson = _lesson_session_for_payload(conn, enrollment, payload)
        if str(lesson["status"] or "").casefold() in {"cancelled", "canceled"}:
            raise ValueError("Attendance cannot be recorded for a cancelled lesson.")
        if not status:
            existing = conn.execute(
                """
                DELETE FROM msi_v2.attendance_records
                WHERE lesson_session_id = %s AND student_id = %s
                RETURNING id
                """,
                (lesson["id"], enrollment["student_id"]),
            ).fetchone()
            conn.commit()
            return int(existing["id"] or 0) if existing else 0
        row = conn.execute(
            """
            INSERT INTO msi_v2.attendance_records (
                lesson_session_id, group_id, student_id, attendance_status,
                recorded_by_staff_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
                attendance_status = excluded.attendance_status,
                recorded_by_staff_id = excluded.recorded_by_staff_id,
                updated_at = excluded.updated_at
            RETURNING id
            """,
            (lesson["id"], enrollment["group_id"], enrollment["student_id"], status,
             int(actor_staff_id) if actor_staff_id else None, _now(), _now()),
        ).fetchone()
        conn.commit()
        return int(row["id"])


def record_homework_from_payload(payload, actor_staff_id=None):
    enrollment_id = int(payload.get("enrollment_id", 0))
    score = float(payload.get("score", 0))
    if score < 1 or score > 9:
        raise ValueError("Homework score must be between 1 and 9.")
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        lesson = _lesson_session_for_payload(conn, enrollment, payload)
        if str(lesson["status"] or "").casefold() in {"cancelled", "canceled"}:
            raise ValueError("Homework cannot be recorded for a cancelled lesson.")
        if not lesson["program_item_id"] and str(lesson["source_kind"] or "").casefold() != "lesson":
            raise ValueError("Homework can only be recorded for lesson sessions.")
        row = conn.execute(
            """
            INSERT INTO msi_v2.homework_scores (
                lesson_session_id, group_id, student_id, score, score_scale,
                recorded_by_staff_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 9, %s, %s, %s)
            ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
                score = excluded.score,
                recorded_by_staff_id = excluded.recorded_by_staff_id,
                updated_at = excluded.updated_at
            RETURNING id
            """,
            (lesson["id"], enrollment["group_id"], enrollment["student_id"], score,
             int(actor_staff_id) if actor_staff_id else None, _now(), _now()),
        ).fetchone()
        conn.commit()
        return int(row["id"])


def get_enrollment_gradebook_summary(enrollment_id):
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, int(enrollment_id or 0))
        if not enrollment:
            raise ValueError("Enrollment not found.")
        row = conn.execute(
            """
            SELECT
              (SELECT COALESCE(round(avg(hw.score)::numeric, 1), 0)
               FROM msi_v2.homework_scores hw
               WHERE hw.group_id = %s AND hw.student_id = %s) AS average_grade,
              (SELECT count(*)
               FROM msi_v2.attendance_records ar
               WHERE ar.group_id = %s AND ar.student_id = %s
                 AND ar.attendance_status IN ('present', 'absent', 'justified')) AS attendance_total,
              (SELECT count(*)
               FROM msi_v2.attendance_records ar
               WHERE ar.group_id = %s AND ar.student_id = %s
                 AND ar.attendance_status = 'present') AS attendance_present
            """,
            (
                int(enrollment["group_id"]), int(enrollment["student_id"]),
                int(enrollment["group_id"]), int(enrollment["student_id"]),
                int(enrollment["group_id"]), int(enrollment["student_id"]),
            ),
        ).fetchone()
    total = int(row["attendance_total"] or 0)
    present = int(row["attendance_present"] or 0)
    return {
        "averageGrade": float(row["average_grade"] or 0),
        "attendancePresent": present,
        "attendanceTotal": total,
        "attendanceRate": round((present / total) * 100) if total else None,
    }


def update_lesson_session_from_payload(lesson_session_id, payload):
    lesson_session_id = int(lesson_session_id or 0)
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    raw_date = payload.get("lesson_date", payload.get("date", None))
    next_date = _parse_optional_lesson_date(raw_date) if raw_date is not None else None
    should_update_date = raw_date is not None
    raw_status = payload.get("status", None)
    next_status = _normalize_lesson_status(raw_status) if raw_status is not None else None
    raw_start_time = payload.get("start_time", None)
    raw_end_time = payload.get("end_time", None)
    should_update_times = raw_start_time is not None or raw_end_time is not None
    next_start_time = _parse_optional_lesson_time(raw_start_time)
    next_end_time = _parse_optional_lesson_time(raw_end_time)
    if should_update_times:
        if (next_start_time is None) != (next_end_time is None):
            raise ValueError("Both start and end times are required (or both empty to clear).")
        if next_start_time is not None and next_end_time <= next_start_time:
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

    with connect_auth_db() as conn:
        row = conn.execute(
            """
            SELECT ls.id, ls.status, ls.session_date, ls.room,
                   COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, 'Session') AS lesson_number,
                   COALESCE(NULLIF(ls.source_topic, ''), spi.title, '') AS topic
            FROM msi_v2.lesson_sessions ls
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE ls.id = %s
            """,
            (lesson_session_id,),
        ).fetchone()
        if not row:
            raise ValueError("Lesson session was not found.")

        conn.execute(
            """
            UPDATE msi_v2.lesson_sessions
            SET session_date = CASE WHEN %s THEN %s ELSE session_date END,
                start_time = CASE WHEN %s THEN %s::time ELSE start_time END,
                end_time = CASE WHEN %s THEN %s::time ELSE end_time END,
                room = CASE WHEN %s THEN %s ELSE room END,
                source_label = CASE WHEN %s THEN %s ELSE source_label END,
                source_topic = CASE WHEN %s THEN %s ELSE source_topic END,
                status = COALESCE(NULLIF(%s, ''), status),
                updated_at = now()
            WHERE id = %s
            """,
            (
                bool(should_update_date),
                next_date,
                bool(should_update_times),
                next_start_time,
                bool(should_update_times),
                next_end_time,
                bool(should_update_room),
                next_room,
                bool(should_update_lesson_name),
                next_lesson_name,
                bool(should_update_topic),
                next_topic,
                next_status if next_status is not None else "",
                lesson_session_id,
            ),
        )
        conn.commit()

    display_date = canonical.format_date(next_date if should_update_date else row["session_date"])
    return {
        "id": lesson_session_id,
        "lessonNumber": next_lesson_name if should_update_lesson_name else str(row["lesson_number"] or "Session"),
        "topic": next_topic if should_update_topic else str(row["topic"] or ""),
        "date": display_date,
        "room": next_room if should_update_room else str(row["room"] or ""),
        "startTime": next_start_time or "",
        "endTime": next_end_time or "",
        "status": next_status or str(row["status"] or "scheduled"),
    }


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
    cursor = first_date if include_first_date else first_date + timedelta(days=1)
    dates = []
    while len(dates) < len(lessons):
        if cursor.weekday() in weekdays and cursor not in blocked:
            dates.append(cursor)
        cursor += timedelta(days=1)
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
    return len(lessons)


def cancel_lesson_session(lesson_session_id, reason, actor_staff_id=None):
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
        if lesson["session_date"] is None:
            raise ValueError("Only a scheduled lesson can be cancelled.")
        if timetable_repository.get_active_lesson_exception(conn, lesson_session_id):
            raise ValueError("This lesson is already cancelled.")
        exception = timetable_repository.insert_lesson_exception(conn, lesson, reason, actor_staff_id)
        affected = _reflow_lesson_sequence(
            conn, lesson, first_date=lesson["session_date"], include_first_date=False
        )
        conn.commit()
        return {
            "groupId": int(lesson["group_id"]),
            "exceptionId": int(exception["id"]),
            "affectedLessonCount": affected,
        }


def recover_lesson_session(lesson_session_id, actor_staff_id=None):
    lesson_session_id = int(lesson_session_id or 0)
    if lesson_session_id <= 0:
        raise ValueError("Lesson session id is required.")
    with connect_auth_db() as conn:
        lesson = timetable_repository.get_curriculum_lesson_for_exception(conn, lesson_session_id)
        if not lesson:
            raise ValueError("Curriculum lesson was not found.")
        exception = timetable_repository.get_active_lesson_exception(conn, lesson_session_id)
        if not exception:
            raise ValueError("This lesson has no active cancellation to recover.")
        timetable_repository.recover_lesson_exception(conn, int(exception["id"]), actor_staff_id)
        affected = _reflow_lesson_sequence(
            conn,
            lesson,
            first_date=exception["original_session_date"],
            include_first_date=True,
            ignored_exception_id=int(exception["id"]),
        )
        conn.commit()
        return {
            "groupId": int(lesson["group_id"]),
            "exceptionId": int(exception["id"]),
            "affectedLessonCount": affected,
        }


def record_exam_from_payload(payload, actor_staff_id=None):
    enrollment_id = int(payload.get("enrollment_id", 0))
    exam_name = str(payload.get("exam_name") or payload.get("label") or "").strip()
    if not exam_name:
        raise ValueError("Exam name is required.")
    attempt = str(payload.get("attempt", "") or "").strip()
    score = float(payload.get("score", 0))
    if score < 1 or score > 9:
        raise ValueError("Exam score must be between 1 and 9.")
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        program_item = conn.execute(
            """
            SELECT spi.id
            FROM msi_v2.groups g
            JOIN msi_v2.subject_program_items spi ON spi.program_id = g.program_id
            WHERE g.id = %s
              AND spi.item_type = 'exam'
              AND lower(spi.title) = lower(%s)
            LIMIT 1
            """,
            (enrollment["group_id"], exam_name),
        ).fetchone()
        row = conn.execute(
            """
            INSERT INTO msi_v2.exam_results (
                group_id, program_item_id, student_id, exam_name, attempt, score,
                score_scale, recorded_by_staff_id, created_at, updated_at
            )
            SELECT %s, %s, %s, %s, %s, %s, 9, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM msi_v2.exam_results er
                WHERE er.group_id = %s
                  AND er.student_id = %s
                  AND lower(er.exam_name) = lower(%s)
                  AND lower(er.attempt) = lower(%s)
            )
            RETURNING id
            """,
            (
                enrollment["group_id"],
                program_item["id"] if program_item else None,
                enrollment["student_id"],
                exam_name,
                attempt,
                score,
                int(actor_staff_id) if actor_staff_id else None,
                _now(),
                _now(),
                enrollment["group_id"],
                enrollment["student_id"],
                exam_name,
                attempt,
            ),
        ).fetchone()
        if not row:
            row = conn.execute(
                """
                UPDATE msi_v2.exam_results
                SET score = %s, program_item_id = COALESCE(%s, program_item_id),
                    recorded_by_staff_id = %s, updated_at = %s
                WHERE group_id = %s
                  AND student_id = %s
                  AND lower(exam_name) = lower(%s)
                  AND lower(attempt) = lower(%s)
                RETURNING id
                """,
                (
                    score,
                    program_item["id"] if program_item else None,
                    int(actor_staff_id) if actor_staff_id else None,
                    _now(),
                    enrollment["group_id"],
                    enrollment["student_id"],
                    exam_name,
                    attempt,
                ),
            ).fetchone()
        conn.commit()
        return int(row["id"])


def record_coin_from_payload(payload):
    enrollment_id = int(payload.get("enrollment_id", 0))
    amount = int(payload.get("amount", 0))
    source = str(payload.get("source", "manual") or "manual").strip()
    with connect_auth_db() as conn:
        enrollment = _get_v2_enrollment(conn, enrollment_id)
        if not enrollment:
            raise ValueError("Enrollment not found.")
        row = conn.execute(
            """
            INSERT INTO msi_v2.coin_events (
                student_id, group_id, amount, source, note, occurred_at, created_at
            )
            VALUES (%s, %s, %s, %s, '', %s, %s)
            RETURNING id
            """,
            (enrollment["student_id"], enrollment["group_id"], amount, source, _now(), _now()),
        ).fetchone()
        conn.commit()
        return int(row["id"])


def update_enrollment_status_from_payload(enrollment_id, payload):
    return update_enrollment_status(
        enrollment_id,
        payload.get("status", ""),
        reason=payload.get("reason", ""),
    )


def move_enrollment_group_from_payload(enrollment_id, payload):
    return move_enrollment_group(enrollment_id, payload.get("group_id", 0))
