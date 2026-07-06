"""Admin-facing academic operations and payload shaping."""

import re
from datetime import UTC, datetime

from backend.domains.academics.exam_filters import is_exam_performance_row
from database import queries
from database.academics import canonical
from backend.domains.academics.postgres_service import (
    create_group_from_program,
    create_schedule,
    create_school,
    create_student_with_enrollment,
    create_subject,
    list_academic_admin_rows,
)


def list_admin_academic_context():
    return list_academic_admin_rows()


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
    group_name = str(payload.get("group_name", "") or "").strip()
    group_code = str(payload.get("group_code", "") or "").strip()
    if not school_code or not program_subject_key or not group_name:
        raise ValueError("Client school, subject program, and group name are required.")
    create_group_from_program(school_code, program_subject_key, group_name, group_code)
    return {"school_code": school_code}


def delete_group(group_id):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required.")

    with queries.connect_auth_db() as conn:
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
        start_date=payload.get("start_date", ""),
        end_date=payload.get("end_date", ""),
        room=payload.get("room", ""),
        online_url=payload.get("online_url", ""),
        title=payload.get("title", ""),
    )
    return result


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
               g.legacy_group_id, g.id AS v2_group_id
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


def _ensure_group_curriculum_lesson_sessions(conn, group_id):
    """Materialize missing curriculum lessons so gradebooks show the full program."""
    conn.execute(
        """
        INSERT INTO msi_v2.lesson_sessions (
            group_id,
            program_item_id,
            status,
            source_key,
            source_kind,
            source_label,
            source_topic,
            source_order,
            source_file,
            source_sheet,
            created_at,
            updated_at
        )
        SELECT
            g.id,
            spi.id,
            'scheduled',
            concat('curriculum:', g.id, ':', spi.id),
            'lesson',
            spi.lesson_number,
            spi.title,
            spi.item_order,
            spi.source_file,
            spi.sheet_name,
            now(),
            now()
        FROM msi_v2.groups g
        JOIN msi_v2.subject_program_items spi ON spi.program_id = g.program_id
        WHERE g.id = %s
          AND spi.item_type = 'lesson'
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.lesson_sessions existing
              WHERE existing.group_id = g.id
                AND existing.program_item_id = spi.id
          )
        ON CONFLICT (source_key) WHERE source_key <> '' DO NOTHING
        """,
        (int(group_id),),
    )


def get_group_gradebook(group_id):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required")

    with queries.connect_auth_db() as conn:
        group_row = conn.execute(
            """
            SELECT g.id, g.legacy_group_id, g.group_name, g.group_code,
                   s.school_key, subj.subject_name
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

        _ensure_group_curriculum_lesson_sessions(conn, int(group_row["id"]))
        conn.commit()

        lesson_rows = conn.execute(
            """
            WITH ranked_sessions AS (
                SELECT ls.id,
                       ls.program_item_id,
                       COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, 'Session') AS lesson_number,
                       COALESCE(NULLIF(ls.source_topic, ''), spi.title, '') AS topic,
                       COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                       ls.session_date,
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
                GROUP BY group_id, student_id
            ) hw ON hw.group_id = gs.group_id AND hw.student_id = gs.student_id
            LEFT JOIN (
                SELECT group_id, student_id, sum(amount)::int AS total_coins
                FROM msi_v2.coin_events
                GROUP BY group_id, student_id
            ) coins ON coins.group_id = gs.group_id AND coins.student_id = gs.student_id
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
            (int(group_row["id"]),),
        ).fetchall()

        active_enrollment_rows = [
            row
            for row in enrollment_rows
            if str(row["enrollment_status"] or "active") == "active"
        ]
        enrollment_ids = [int(row["legacy_enrollment_id"] or 0) for row in enrollment_rows if row["legacy_enrollment_id"]]
        attendance_by_enrollment = {}
        homework_by_enrollment = {}
        exams_by_enrollment = {}
        exam_attempts_by_enrollment = {}
        exam_dates_by_enrollment = {}
        exam_dates_by_label = {}
        exam_labels = []
        if enrollment_ids:
            placeholders = ",".join(["%s"] * len(enrollment_ids))
            for row in conn.execute(
                f"""
                SELECT gs.legacy_enrollment_id AS enrollment_id,
                       COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_label,
                       ar.attendance_status AS status
                FROM msi_v2.attendance_records ar
                JOIN msi_v2.group_students gs
                     ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
                JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
                LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
                WHERE gs.legacy_enrollment_id IN ({placeholders})
                  AND (
                    spi.item_type = 'lesson'
                    OR (ls.program_item_id IS NULL AND ls.source_key <> '')
                  )
                  AND COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') <> ''
                """,
                enrollment_ids,
            ).fetchall():
                attendance_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = str(row["status"])
            for row in conn.execute(
                f"""
                SELECT gs.legacy_enrollment_id AS enrollment_id,
                       COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') AS lesson_label,
                       hw.score
                FROM msi_v2.homework_scores hw
                JOIN msi_v2.group_students gs
                     ON gs.group_id = hw.group_id AND gs.student_id = hw.student_id
                JOIN msi_v2.lesson_sessions ls ON ls.id = hw.lesson_session_id
                LEFT JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
                WHERE gs.legacy_enrollment_id IN ({placeholders})
                  AND (
                    spi.item_type = 'lesson'
                    OR (ls.program_item_id IS NULL AND ls.source_key <> '')
                  )
                  AND COALESCE(NULLIF(ls.source_label, ''), spi.lesson_number, '') <> ''
                """,
                enrollment_ids,
            ).fetchall():
                homework_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = float(row["score"])
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
        },
        "lessons": [
            {
                "id": int(row["id"]),
                "lessonNumber": str(row["lesson_number"]),
                "topic": str(row["topic"] or ""),
                "date": str(row["lesson_date"] or ""),
                "order": int(row["lesson_order"] or 0),
                "status": str(row["status"] or "scheduled"),
                "sourceKind": str(row["source_kind"] or ""),
                "hasHomework": bool(row["has_homework"]),
            }
            for row in lesson_rows
        ],
        "examLabels": exam_labels,
        "examDates": exam_dates_by_label,
        "enrollments": [
            {
                "enrollmentId": int(row["legacy_enrollment_id"] or 0),
                "fullName": str(row["full_name"]),
                "averageGrade": float(row["average_grade"] or 0),
                "coins": int(row["coins"] or 0),
                "attendance": attendance_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
                "homework": homework_by_enrollment.get(int(row["legacy_enrollment_id"] or 0), {}),
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
    with queries.connect_auth_db() as conn:
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

    with queries.connect_auth_db() as conn:
        row = _get_v2_enrollment(conn, enrollment_id)
        if not row:
            raise ValueError("Enrollment not found.")
        target = conn.execute(
            """
            SELECT id
            FROM msi_v2.groups g
            WHERE """ + _legacy_or_v2_group_where() + """
            """,
            (group_id, group_id),
        ).fetchone()
        if not target:
            raise ValueError("Target group not found.")
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


def record_attendance_from_payload(payload):
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
    with queries.connect_auth_db() as conn:
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
                lesson_session_id, group_id, student_id, attendance_status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
                attendance_status = excluded.attendance_status,
                updated_at = excluded.updated_at
            RETURNING id
            """,
            (lesson["id"], enrollment["group_id"], enrollment["student_id"], status, _now(), _now()),
        ).fetchone()
        conn.commit()
        return int(row["id"])


def record_homework_from_payload(payload):
    enrollment_id = int(payload.get("enrollment_id", 0))
    score = float(payload.get("score", 0))
    if score < 1 or score > 9:
        raise ValueError("Homework score must be between 1 and 9.")
    with queries.connect_auth_db() as conn:
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
                lesson_session_id, group_id, student_id, score, score_scale, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 9, %s, %s)
            ON CONFLICT (lesson_session_id, student_id) DO UPDATE SET
                score = excluded.score,
                updated_at = excluded.updated_at
            RETURNING id
            """,
            (lesson["id"], enrollment["group_id"], enrollment["student_id"], score, _now(), _now()),
        ).fetchone()
        conn.commit()
        return int(row["id"])


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

    with queries.connect_auth_db() as conn:
        row = conn.execute(
            """
            SELECT ls.id, ls.status, ls.session_date,
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
                next_status if next_status is not None else "",
                lesson_session_id,
            ),
        )
        conn.commit()

    display_date = canonical.format_date(next_date if should_update_date else row["session_date"])
    return {
        "id": lesson_session_id,
        "lessonNumber": str(row["lesson_number"] or "Session"),
        "topic": str(row["topic"] or ""),
        "date": display_date,
        "startTime": next_start_time or "",
        "endTime": next_end_time or "",
        "status": next_status or str(row["status"] or "scheduled"),
    }


def record_exam_from_payload(payload):
    enrollment_id = int(payload.get("enrollment_id", 0))
    exam_name = str(payload.get("exam_name") or payload.get("label") or "").strip()
    if not exam_name:
        raise ValueError("Exam name is required.")
    attempt = str(payload.get("attempt", "") or "").strip()
    score = float(payload.get("score", 0))
    if score < 1 or score > 9:
        raise ValueError("Exam score must be between 1 and 9.")
    with queries.connect_auth_db() as conn:
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
                score_scale, created_at, updated_at
            )
            SELECT %s, %s, %s, %s, %s, %s, 9, %s, %s
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
                SET score = %s, program_item_id = COALESCE(%s, program_item_id), updated_at = %s
                WHERE group_id = %s
                  AND student_id = %s
                  AND lower(exam_name) = lower(%s)
                  AND lower(attempt) = lower(%s)
                RETURNING id
                """,
                (
                    score,
                    program_item["id"] if program_item else None,
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
    with queries.connect_auth_db() as conn:
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
