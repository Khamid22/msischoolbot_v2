"""Build student dashboard payloads from internal academic tables (no Google Sheets)."""

import math

from database import queries

_SCHOOL_DISPLAY_NAMES = {
    "school5": "School 5",
    "sehriyo": "Sehriyo",
}


def _school_display_name(code):
    return _SCHOOL_DISPLAY_NAMES.get(str(code or "").strip().casefold(), str(code or "").capitalize())


def _split_full_name(full_name):
    parts = str(full_name or "").strip().split()
    if len(parts) >= 2:
        surname = parts[0]
        name = " ".join(parts[1:])
    elif parts:
        surname = parts[0]
        name = ""
    else:
        surname = ""
        name = ""
    initials = "".join(p[0].upper() + "." for p in parts if p)
    return {"surname": surname, "name": name, "initials": initials, "fullName": str(full_name or "").strip()}


def _filter_text(value):
    return " ".join(str(value or "").strip().lower().split())


def _average_homework_grade(homework_grades):
    scores = []
    for item in homework_grades or []:
        if not isinstance(item, dict):
            continue
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        if score != score:
            continue
        scores.append(max(0.0, min(9.0, score)))
    if not scores:
        return 0.0
    return math.floor((sum(scores) / len(scores)) * 10 + 0.5) / 10


_academic_tables_known_present = False


def _academic_tables_exist(conn) -> bool:
    # Once the clean schema is seen it never disappears at runtime, so cache the
    # positive answer and skip the pg_tables scan on every later call.
    global _academic_tables_known_present
    if _academic_tables_known_present:
        return True
    rows = conn.execute(
        "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'msi_v2'"
    ).fetchall()
    existing = {str(r["name"]) for r in rows}
    present = {
        "schools",
        "students",
        "subjects",
        "subject_programs",
        "subject_program_items",
        "groups",
        "group_students",
        "lesson_sessions",
    }.issubset(existing)
    if present:
        _academic_tables_known_present = True
    return present


def _attendance_payload(rows):
    present_count = 0
    absent_count = 0
    justified_count = 0
    attendance_lessons = []
    for row in rows:
        status = str(row["status"] or "").strip().casefold()
        if status == "present":
            present_count += 1
        elif status == "absent":
            absent_count += 1
        elif status == "justified":
            justified_count += 1
        if status:
            attendance_lessons.append({
                "lesson": row["lesson_label"],
                "topic": row["topic"] or "",
                "date": row["lesson_date"] or "",
                "attendanceType": row["attendance_type"] or "",
                "status": status,
            })
    return attendance_lessons, present_count, absent_count, justified_count


def _homework_payload(rows):
    return [
        {
            "lesson": row["lesson_label"],
            "topic": row["topic"] or "",
            "date": row["lesson_date"] or "",
            "type": row["score_type"] or "Homework",
            "score": float(row["score"]),
        }
        for row in rows
    ]


def _exam_payload(rows):
    return [
        {
            "label": row["label"],
            "examName": row["exam_name"] or "",
            "attempt": row["attempt"] or "",
            "score": float(row["score"]),
        }
        for row in rows
    ]


def get_subject_dashboards_from_db(subject_name):
    """Return minimal dashboard payloads for all students in a subject (for leaderboard)."""
    subject_norm = " ".join(str(subject_name or "").strip().casefold().split())
    if not subject_norm:
        return []

    with queries.connect_auth_db() as conn:
        if not _academic_tables_exist(conn):
            return []

        rows = conn.execute(
            """
            SELECT COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                   st.full_name,
                   COALESCE(hw.average_grade, 0) AS average_grade,
                   COALESCE(coins.total_coins, 0) AS coins,
                   sub.subject_name,
                   g.group_name,
                   g.group_code
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            LEFT JOIN (
                SELECT student_id, group_id, round(avg(score)::numeric, 1) AS average_grade
                FROM msi_v2.homework_scores
                WHERE score IS NOT NULL
                GROUP BY student_id, group_id
            ) hw ON hw.student_id = gs.student_id AND hw.group_id = gs.group_id
            LEFT JOIN (
                SELECT student_id, group_id, sum(amount)::integer AS total_coins
                FROM msi_v2.coin_events
                GROUP BY student_id, group_id
            ) coins ON coins.student_id = gs.student_id AND coins.group_id = gs.group_id
            WHERE gs.enrollment_status = 'active'
              AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
              AND lower(trim(sub.subject_name)) = %s
            ORDER BY g.group_name, st.full_name
            """,
            (subject_norm,),
        ).fetchall()

        dashboards = []
        for row in rows:
            split = _split_full_name(row["full_name"])
            student = {
                "id": int(row["public_dashboard_id"]),
                "fullName": split["fullName"],
                "surname": split["surname"],
                "name": split["name"],
                "initials": split["initials"],
                "group": row["group_name"],
                "groupCode": row["group_code"] or "",
                "subject": row["subject_name"],
                "coins": int(row["coins"] or 0),
            }
            dashboards.append({
                "student": student,
                "averageGrade": float(row["average_grade"] or 0.0),
                "examResults": [],
                "homeworkGrades": [],
                "attendanceLessons": [],
                "attendanceRecord": {
                    "presentCount": 0, "absentCount": 0,
                    "justifiedAbsentCount": 0, "totalCount": 0,
                    "subject": row["subject_name"],
                },
                "academicRecords": [],
                "coins": int(row["coins"] or 0),
            })
        return dashboards


def build_internal_dataset(school_code=""):
    """Return the old Sheets-style dataset shape from internal DB rows."""
    normalized_school = str(school_code or "").strip().casefold()

    with queries.connect_auth_db() as conn:
        if not _academic_tables_exist(conn):
            return None

        rows = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS enrollment_id,
                   COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                   st.full_name,
                   COALESCE(hw.average_grade, 0) AS average_grade,
                   COALESCE(coins.total_coins, 0) AS coins,
                   s.school_key AS school_code,
                   s.school_name,
                   sub.subject_name,
                   sub.subject_short AS subject_code,
                   g.group_name,
                   g.group_code
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            LEFT JOIN (
                SELECT student_id, group_id, round(avg(score)::numeric, 1) AS average_grade
                FROM msi_v2.homework_scores
                WHERE score IS NOT NULL
                GROUP BY student_id, group_id
            ) hw ON hw.student_id = gs.student_id AND hw.group_id = gs.group_id
            LEFT JOIN (
                SELECT student_id, group_id, sum(amount)::integer AS total_coins
                FROM msi_v2.coin_events
                GROUP BY student_id, group_id
            ) coins ON coins.student_id = gs.student_id AND coins.group_id = gs.group_id
            WHERE gs.enrollment_status = 'active'
              AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
              AND gs.legacy_enrollment_id IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY sub.subject_name, g.group_name, st.full_name
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        lesson_rows = conn.execute(
            """
            SELECT s.school_key AS school_code,
                   sub.subject_name,
                   g.group_name,
                   spi.lesson_number,
                   spi.title AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   spi.item_order AS lesson_order
            FROM msi_v2.lesson_sessions ls
            JOIN msi_v2.groups g ON g.id = ls.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE spi.item_type = 'lesson'
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY sub.subject_name, g.group_name, spi.item_order, spi.lesson_number
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        attendance_rows = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS enrollment_id,
                   spi.lesson_number AS lesson_label,
                   spi.title AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   '' AS attendance_type,
                   ar.attendance_status AS status
            FROM msi_v2.attendance_records ar
            JOIN msi_v2.group_students gs
              ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
            JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            JOIN msi_v2.groups g ON g.id = ar.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY gs.legacy_enrollment_id, spi.item_order, spi.lesson_number
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        homework_rows = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS enrollment_id,
                   spi.lesson_number AS lesson_label,
                   spi.title AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   'Homework' AS score_type,
                   hs.score
            FROM msi_v2.homework_scores hs
            JOIN msi_v2.group_students gs
              ON gs.group_id = hs.group_id AND gs.student_id = hs.student_id
            JOIN msi_v2.lesson_sessions ls ON ls.id = hs.lesson_session_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            JOIN msi_v2.groups g ON g.id = hs.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND hs.score IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY gs.legacy_enrollment_id, spi.item_order, spi.lesson_number
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        exam_rows = conn.execute(
            """
            SELECT DISTINCT ON (
                   gs.legacy_enrollment_id,
                   lower(COALESCE(er.exam_name, '')),
                   lower(COALESCE(er.attempt, ''))
                   )
                   gs.legacy_enrollment_id AS enrollment_id,
                   COALESCE(NULLIF(spi.lesson_number, ''), er.exam_name) AS label,
                   er.exam_name,
                   er.attempt,
                   er.score
            FROM msi_v2.exam_results er
            JOIN msi_v2.group_students gs
              ON gs.group_id = er.group_id AND gs.student_id = er.student_id
            JOIN msi_v2.groups g ON g.id = er.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND er.score IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY gs.legacy_enrollment_id,
                     lower(COALESCE(er.exam_name, '')),
                     lower(COALESCE(er.attempt, '')),
                     er.updated_at DESC,
                     er.id DESC
            """,
            (normalized_school, normalized_school),
        ).fetchall()

    attendance_by_enrollment = {}
    for row in attendance_rows:
        attendance_by_enrollment.setdefault(int(row["enrollment_id"]), []).append(row)

    homework_by_enrollment = {}
    for row in homework_rows:
        homework_by_enrollment.setdefault(int(row["enrollment_id"]), []).append(row)

    exams_by_enrollment = {}
    for row in exam_rows:
        exams_by_enrollment.setdefault(int(row["enrollment_id"]), []).append(row)

    students = []
    dashboards_by_id = {}
    groups = set()
    subjects = set()
    groups_by_subject = {}
    lesson_catalog_by_subject = {}
    lesson_catalog_by_subject_group = {}

    for row in rows:
        split = _split_full_name(row["full_name"])
        subject_name = str(row["subject_name"] or "").strip()
        group_name = str(row["group_name"] or "").strip()
        subjects.add(subject_name)
        groups.add(group_name)
        groups_by_subject.setdefault(subject_name, set()).add(group_name)

        enrollment_id = int(row["enrollment_id"])
        coins = int(row["coins"] or 0)

        student = {
            "id": int(row["public_dashboard_id"]),
            "fullName": split["fullName"],
            "surname": split["surname"],
            "name": split["name"],
            "initials": split["initials"],
            "group": group_name,
            "groupCode": str(row["group_code"] or ""),
            "subject": subject_name,
            "subjectCode": str(row["subject_code"] or ""),
            "schoolCode": str(row["school_code"] or ""),
            "schoolName": str(row["school_name"] or _school_display_name(row["school_code"])),
            "coins": coins,
        }
        students.append(student)

        attendance_lessons, present_count, absent_count, justified_count = (
            _attendance_payload(attendance_by_enrollment.get(enrollment_id, []))
        )
        homework_grades = _homework_payload(homework_by_enrollment.get(enrollment_id, []))
        exam_results = _exam_payload(exams_by_enrollment.get(enrollment_id, []))
        academic_records = [
            {
                "date": result["label"],
                "grade": result["score"],
                "subject": subject_name,
                "assessment": result["label"],
            }
            for result in exam_results
        ]

        average_grade = _average_homework_grade(homework_grades)
        if not average_grade:
            average_grade = float(row["average_grade"] or 0.0)

        dashboards_by_id[int(row["public_dashboard_id"])] = {
            "student": student,
            "academicRecords": academic_records,
            "examResults": exam_results,
            "homeworkGrades": homework_grades,
            "attendanceLessons": attendance_lessons,
            "attendanceRecord": {
                "presentCount": present_count,
                "absentCount": absent_count,
                "justifiedAbsentCount": justified_count,
                "totalCount": present_count + absent_count + justified_count,
                "subject": subject_name,
            },
            "averageGrade": average_grade,
            "coins": coins,
        }

    for row in lesson_rows:
        subject_name = str(row["subject_name"] or "").strip()
        group_name = str(row["group_name"] or "").strip()
        lesson = {
            "lesson_number": str(row["lesson_number"] or "").strip(),
            "lesson_topic": str(row["topic"] or "").strip(),
            "lesson_date": str(row["lesson_date"] or "").strip(),
            "lesson_order": int(row["lesson_order"] or 0),
        }
        lesson_catalog_by_subject.setdefault(subject_name, []).append(lesson)
        lesson_catalog_by_subject_group.setdefault(subject_name, {}).setdefault(
            group_name,
            [],
        ).append(lesson)

    return {
        "students": students,
        "dashboards_by_id": dashboards_by_id,
        "groups": sorted(groups, key=lambda value: value.casefold()),
        "groups_by_subject": {
            subject: sorted(group_set, key=lambda value: value.casefold())
            for subject, group_set in sorted(
                groups_by_subject.items(),
                key=lambda item: str(item[0]).casefold(),
            )
        },
        "lesson_catalog_by_subject": lesson_catalog_by_subject,
        "lesson_catalog_by_subject_group": lesson_catalog_by_subject_group,
        "subjects": sorted(subjects, key=lambda value: value.casefold()),
    }


def build_internal_overview_dataset(school_code=""):
    """Return the minimal Sheets-style dataset shape needed by admin overview charts."""
    normalized_school = str(school_code or "").strip().casefold()

    with queries.connect_auth_db() as conn:
        if not _academic_tables_exist(conn):
            return None

        enrollment_rows = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS id,
                   COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                   st.full_name,
                   s.school_key AS school_code,
                   s.school_name,
                   sub.subject_name,
                   g.group_name
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY sub.subject_name, g.group_name, st.full_name
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        homework_rows = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS enrollment_id,
                   spi.lesson_number AS lesson_label,
                   spi.title AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   'Homework' AS score_type,
                   hs.score
            FROM msi_v2.homework_scores hs
            JOIN msi_v2.group_students gs
              ON gs.group_id = hs.group_id AND gs.student_id = hs.student_id
            JOIN msi_v2.lesson_sessions ls ON ls.id = hs.lesson_session_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            JOIN msi_v2.groups g ON g.id = hs.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND hs.score IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY gs.legacy_enrollment_id, spi.item_order, spi.lesson_number
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        exam_rows = conn.execute(
            """
            SELECT DISTINCT ON (
                   gs.legacy_enrollment_id,
                   lower(COALESCE(er.exam_name, '')),
                   lower(COALESCE(er.attempt, ''))
                   )
                   gs.legacy_enrollment_id AS enrollment_id,
                   COALESCE(NULLIF(spi.lesson_number, ''), er.exam_name) AS label,
                   er.exam_name,
                   er.attempt,
                   er.score
            FROM msi_v2.exam_results er
            JOIN msi_v2.group_students gs
              ON gs.group_id = er.group_id AND gs.student_id = er.student_id
            JOIN msi_v2.groups g ON g.id = er.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND er.score IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
            ORDER BY gs.legacy_enrollment_id,
                     lower(COALESCE(er.exam_name, '')),
                     lower(COALESCE(er.attempt, '')),
                     er.updated_at DESC,
                     er.id DESC
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        attendance_rows = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS enrollment_id,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   ar.attendance_status AS status
            FROM msi_v2.attendance_records ar
            JOIN msi_v2.group_students gs
              ON gs.group_id = ar.group_id AND gs.student_id = ar.student_id
            JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
            JOIN msi_v2.groups g ON g.id = ar.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            WHERE gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
              AND ls.session_date IS NOT NULL
              AND ar.attendance_status IS NOT NULL
              AND ar.attendance_status <> ''
            ORDER BY gs.legacy_enrollment_id, ls.session_date
            """,
            (normalized_school, normalized_school),
        ).fetchall()

    homework_by_enrollment = {}
    for row in homework_rows:
        homework_by_enrollment.setdefault(int(row["enrollment_id"]), []).append(
            {
                "lesson": row["lesson_label"],
                "topic": row["topic"] or "",
                "date": row["lesson_date"] or "",
                "type": row["score_type"] or "Homework",
                "score": float(row["score"]),
            }
        )

    exams_by_enrollment = {}
    for row in exam_rows:
        exams_by_enrollment.setdefault(int(row["enrollment_id"]), []).append(
            {
                "label": row["label"] or "",
                "examName": row["exam_name"] or "",
                "attempt": row["attempt"] or "",
                "score": float(row["score"]),
            }
        )

    attendance_by_enrollment = {}
    for row in attendance_rows:
        attendance_by_enrollment.setdefault(int(row["enrollment_id"]), []).append(
            {
                "date": str(row["lesson_date"] or "").strip(),
                "status": str(row["status"] or "").strip().casefold(),
            }
        )

    dashboards_by_id = {}
    for row in enrollment_rows:
        student = {
            "id": int(row["public_dashboard_id"]),
            "fullName": str(row["full_name"] or "").strip(),
            "subject": str(row["subject_name"] or "").strip(),
            "group": str(row["group_name"] or "").strip(),
            "schoolCode": str(row["school_code"] or "").strip(),
            "schoolName": str(row["school_name"] or _school_display_name(row["school_code"])),
        }
        dashboards_by_id[int(row["public_dashboard_id"])] = {
            "student": student,
            "homeworkGrades": homework_by_enrollment.get(int(row["id"]), []),
            "examResults": exams_by_enrollment.get(int(row["id"]), []),
            "attendanceLessons": attendance_by_enrollment.get(int(row["id"]), []),
        }

    return {"dashboards_by_id": dashboards_by_id}


def get_student_subject_enrollments(public_dashboard_id):
    """All active enrollments for the SAME student as the given dashboard id.

    Identifies the student by (full_name_norm, school_id) of the current
    enrollment, then returns one entry per subject/group they are enrolled in.
    This is the reliable source for the dashboard's subject switcher — it does
    not depend on loading and name-matching the whole school dataset.
    Returns: [{"student_id": <public_dashboard_id>, "subject", "group"}].
    """
    try:
        dashboard_id = int(public_dashboard_id)
    except (TypeError, ValueError):
        return []

    with queries.connect_auth_db() as conn:
        if not _academic_tables_exist(conn):
            return []

        ref = conn.execute(
            """
            SELECT st.id AS student_id, st.school_id
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
            LIMIT 1
            """,
            (dashboard_id,),
        ).fetchone()
        if not ref:
            return []

        rows = conn.execute(
            """
            SELECT COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS id,
                   sub.subject_name AS subject,
                   g.group_name AS grp
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            WHERE gs.enrollment_status = 'active'
              AND st.id = %s
              AND st.school_id = %s
              AND COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) IS NOT NULL
            ORDER BY sub.subject_name, g.group_name
            """,
            (ref["student_id"], ref["school_id"]),
        ).fetchall()

    return [
        {
            "student_id": int(row["id"]),
            "subject": str(row["subject"] or "").strip(),
            "group": str(row["grp"] or "").strip(),
        }
        for row in rows
        if row["id"]
    ]


def get_enrollment_dashboard(public_dashboard_id, school_code="", subject_name="", group_name=""):
    """Return a dashboard payload dict from internal DB, or None if not found."""
    try:
        student_id = int(public_dashboard_id)
    except (TypeError, ValueError):
        return None

    normalized_school = str(school_code or "").strip().casefold()
    normalized_subject = _filter_text(subject_name)
    normalized_group = _filter_text(group_name)

    with queries.connect_auth_db() as conn:
        if not _academic_tables_exist(conn):
            return None

        enrollment = conn.execute(
            """
            SELECT gs.legacy_enrollment_id AS id,
                   COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) AS public_dashboard_id,
                   st.full_name,
                   COALESCE(hw.average_grade, 0) AS average_grade,
                   COALESCE(coins.total_coins, 0) AS coins,
                   s.school_key AS school_code,
                   s.school_name,
                   sub.subject_name,
                   sub.subject_short AS subject_code,
                   g.group_name,
                   g.group_code,
                   gs.group_id,
                   gs.student_id
            FROM msi_v2.group_students gs
            JOIN msi_v2.students st ON st.id = gs.student_id
            JOIN msi_v2.groups g ON g.id = gs.group_id
            JOIN msi_v2.schools s ON s.id = g.school_id
            JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
            JOIN msi_v2.subjects sub ON sub.id = sp.subject_id
            LEFT JOIN (
                SELECT student_id, group_id, round(avg(score)::numeric, 1) AS average_grade
                FROM msi_v2.homework_scores
                WHERE score IS NOT NULL
                GROUP BY student_id, group_id
            ) hw ON hw.student_id = gs.student_id AND hw.group_id = gs.group_id
            LEFT JOIN (
                SELECT student_id, group_id, sum(amount)::integer AS total_coins
                FROM msi_v2.coin_events
                GROUP BY student_id, group_id
            ) coins ON coins.student_id = gs.student_id AND coins.group_id = gs.group_id
            WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
              AND gs.enrollment_status = 'active'
              AND gs.legacy_enrollment_id IS NOT NULL
              AND lower(g.group_name) <> 'online'
              AND (%s = '' OR s.school_key = %s)
              AND (%s = '' OR lower(trim(regexp_replace(sub.subject_name, '[[:space:]]+', ' ', 'g'))) = %s)
              AND (%s = '' OR lower(trim(regexp_replace(g.group_name, '[[:space:]]+', ' ', 'g'))) = %s)
            LIMIT 1
            """,
            (
                student_id,
                normalized_school,
                normalized_school,
                normalized_subject,
                normalized_subject,
                normalized_group,
                normalized_group,
            ),
        ).fetchone()

        if not enrollment:
            return None

        enrollment_id = int(enrollment["id"])

        attendance_rows = conn.execute(
            """
            SELECT spi.lesson_number AS lesson_label,
                   spi.title AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   '' AS attendance_type,
                   ar.attendance_status AS status
            FROM msi_v2.attendance_records ar
            JOIN msi_v2.lesson_sessions ls ON ls.id = ar.lesson_session_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE ar.group_id = %s
              AND ar.student_id = %s
            ORDER BY spi.item_order, spi.lesson_number
            """,
            (enrollment["group_id"], enrollment["student_id"]),
        ).fetchall()

        attendance_lessons, present_count, absent_count, justified_count = (
            _attendance_payload(attendance_rows)
        )

        hw_rows = conn.execute(
            """
            SELECT spi.lesson_number AS lesson_label,
                   spi.title AS topic,
                   COALESCE(to_char(ls.session_date, 'DD/MM/YYYY'), '') AS lesson_date,
                   'Homework' AS score_type,
                   hs.score
            FROM msi_v2.homework_scores hs
            JOIN msi_v2.lesson_sessions ls ON ls.id = hs.lesson_session_id
            JOIN msi_v2.subject_program_items spi ON spi.id = ls.program_item_id
            WHERE hs.group_id = %s
              AND hs.student_id = %s
              AND hs.score IS NOT NULL
            ORDER BY spi.item_order, spi.lesson_number
            """,
            (enrollment["group_id"], enrollment["student_id"]),
        ).fetchall()

        homework_grades = _homework_payload(hw_rows)

        exam_rows = conn.execute(
            """
            SELECT DISTINCT ON (
                   lower(COALESCE(er.exam_name, '')),
                   lower(COALESCE(er.attempt, ''))
                   )
                   COALESCE(NULLIF(spi.lesson_number, ''), er.exam_name) AS label,
                   er.exam_name,
                   er.attempt,
                   er.score
            FROM msi_v2.exam_results er
            LEFT JOIN msi_v2.subject_program_items spi ON spi.id = er.program_item_id
            WHERE er.group_id = %s
              AND er.student_id = %s
              AND er.score IS NOT NULL
            ORDER BY lower(COALESCE(er.exam_name, '')),
                     lower(COALESCE(er.attempt, '')),
                     er.updated_at DESC,
                     er.id DESC
            """,
            (enrollment["group_id"], enrollment["student_id"]),
        ).fetchall()

        exam_results = _exam_payload(exam_rows)

        academic_records = [
            {
                "date": r["label"],
                "grade": r["score"],
                "subject": enrollment["subject_name"],
                "assessment": r["label"],
            }
            for r in exam_results
        ]

        average_grade = _average_homework_grade(homework_grades)
        if not average_grade:
            average_grade = float(enrollment["average_grade"] or 0.0)

        coins = int(enrollment["coins"] or 0)
        split = _split_full_name(enrollment["full_name"])

        student = {
            "id": int(enrollment["public_dashboard_id"]),
            "surname": split["surname"],
            "name": split["name"],
            "fullName": split["fullName"],
            "initials": split["initials"],
            "group": enrollment["group_name"],
            "groupCode": enrollment["group_code"] or "",
            "subject": enrollment["subject_name"],
            "subjectCode": enrollment["subject_code"] or "",
            "schoolCode": enrollment["school_code"],
            "schoolName": _school_display_name(enrollment["school_code"]),
            "coins": coins,
        }

        total_count = present_count + absent_count + justified_count

        return {
            "student": student,
            "academicRecords": academic_records,
            "examResults": exam_results,
            "homeworkGrades": homework_grades,
            "attendanceLessons": attendance_lessons,
            "attendanceRecord": {
                "presentCount": present_count,
                "absentCount": absent_count,
                "justifiedAbsentCount": justified_count,
                "totalCount": total_count,
                "subject": enrollment["subject_name"],
            },
            "averageGrade": average_grade,
            "coins": coins,
        }
