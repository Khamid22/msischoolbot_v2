"""Build student dashboard payloads from internal academic tables (no Google Sheets)."""

import math

from db import queries

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
    # Once the tables are seen they never disappear at runtime, so cache the
    # positive answer and skip the pg_tables scan on every later call.
    global _academic_tables_known_present
    if _academic_tables_known_present:
        return True
    rows = conn.execute(
        "SELECT tablename AS name FROM pg_tables WHERE schemaname = current_schema()"
    ).fetchall()
    existing = {str(r["name"]) for r in rows}
    present = {"academic_enrollments", "academic_schools", "academic_subjects", "academic_groups"}.issubset(existing)
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
            SELECT e.public_dashboard_id, e.full_name, e.average_grade, e.coins,
                   sub.name AS subject_name,
                   g.name  AS group_name,   g.code  AS group_code
            FROM academic_enrollments e
            JOIN academic_subjects sub ON sub.id = e.subject_id
            JOIN academic_groups   g   ON g.id   = e.group_id
            WHERE lower(trim(sub.name)) = %s
              AND e.active = 1
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
            SELECT e.id AS enrollment_id, e.public_dashboard_id, e.full_name,
                   e.average_grade, e.coins,
                   s.code AS school_code, s.name AS school_name,
                   sub.name AS subject_name, sub.code AS subject_code,
                   g.name AS group_name, g.code AS group_code
            FROM academic_enrollments e
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_subjects sub ON sub.id = e.subject_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY sub.name, g.name, e.full_name
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        lesson_rows = conn.execute(
            """
            SELECT s.code AS school_code, sub.name AS subject_name, g.name AS group_name,
                   l.lesson_number, l.topic, l.lesson_date, l.lesson_order
            FROM academic_lessons l
            JOIN academic_schools s ON s.id = l.school_id
            JOIN academic_subjects sub ON sub.id = l.subject_id
            JOIN academic_groups g ON g.id = l.group_id
            WHERE lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY sub.name, g.name, l.lesson_order, l.lesson_number
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        attendance_rows = conn.execute(
            """
            SELECT a.enrollment_id, a.lesson_label, a.topic, a.lesson_date,
                   a.attendance_type, a.status
            FROM academic_attendance_records a
            JOIN academic_enrollments e ON e.id = a.enrollment_id
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY a.enrollment_id, a.lesson_order, a.lesson_label
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        homework_rows = conn.execute(
            """
            SELECT h.enrollment_id, h.lesson_label, h.topic, h.lesson_date,
                   h.score_type, h.score
            FROM academic_homework_scores h
            JOIN academic_enrollments e ON e.id = h.enrollment_id
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY h.enrollment_id, h.lesson_order, h.lesson_label
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        exam_rows = conn.execute(
            """
            SELECT er.enrollment_id, er.label, er.exam_name, er.attempt, er.score
            FROM academic_exam_results er
            JOIN academic_enrollments e ON e.id = er.enrollment_id
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY er.enrollment_id, er.label
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
            SELECT e.id, e.public_dashboard_id, e.full_name,
                   s.code AS school_code, s.name AS school_name,
                   sub.name AS subject_name,
                   g.name AS group_name
            FROM academic_enrollments e
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_subjects sub ON sub.id = e.subject_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY sub.name, g.name, e.full_name
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        homework_rows = conn.execute(
            """
            SELECT h.enrollment_id, h.lesson_label, h.topic, h.lesson_date, h.score_type, h.score
            FROM academic_homework_scores h
            JOIN academic_enrollments e ON e.id = h.enrollment_id
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY h.enrollment_id, h.lesson_order, h.lesson_label
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        exam_rows = conn.execute(
            """
            SELECT er.enrollment_id, er.label, er.exam_name, er.attempt, er.score
            FROM academic_exam_results er
            JOIN academic_enrollments e ON e.id = er.enrollment_id
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            ORDER BY er.enrollment_id, er.label
            """,
            (normalized_school, normalized_school),
        ).fetchall()

        attendance_rows = conn.execute(
            """
            SELECT a.enrollment_id, a.lesson_date, a.status
            FROM academic_attendance_records a
            JOIN academic_enrollments e ON e.id = a.enrollment_id
            JOIN academic_schools s ON s.id = e.school_id
            JOIN academic_groups g ON g.id = e.group_id
            WHERE e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
              AND a.lesson_date IS NOT NULL
              AND a.lesson_date <> ''
              AND a.status IS NOT NULL
              AND a.status <> ''
            ORDER BY a.enrollment_id, a.lesson_date
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


def get_enrollment_dashboard(public_dashboard_id, school_code=""):
    """Return a dashboard payload dict from internal DB, or None if not found."""
    try:
        student_id = int(public_dashboard_id)
    except (TypeError, ValueError):
        return None

    normalized_school = str(school_code or "").strip().casefold()

    with queries.connect_auth_db() as conn:
        if not _academic_tables_exist(conn):
            return None

        enrollment = conn.execute(
            """
            SELECT e.id, e.public_dashboard_id, e.full_name, e.average_grade, e.coins,
                   s.code  AS school_code,  s.name  AS school_name,
                   sub.name AS subject_name, sub.code AS subject_code,
                   g.name  AS group_name,   g.code  AS group_code
            FROM academic_enrollments e
            JOIN academic_schools   s   ON s.id   = e.school_id
            JOIN academic_subjects  sub ON sub.id = e.subject_id
            JOIN academic_groups    g   ON g.id   = e.group_id
            WHERE e.public_dashboard_id = %s
              AND e.active = 1
              AND lower(g.name) <> 'online'
              AND (%s = '' OR s.code = %s)
            LIMIT 1
            """,
            (student_id, normalized_school, normalized_school),
        ).fetchone()

        if not enrollment:
            return None

        enrollment_id = int(enrollment["id"])

        attendance_rows = conn.execute(
            """
            SELECT lesson_label, topic, lesson_date, attendance_type, status, lesson_order
            FROM academic_attendance_records
            WHERE enrollment_id = %s
            ORDER BY lesson_order, lesson_label
            """,
            (enrollment_id,),
        ).fetchall()

        attendance_lessons, present_count, absent_count, justified_count = (
            _attendance_payload(attendance_rows)
        )

        hw_rows = conn.execute(
            """
            SELECT lesson_label, topic, lesson_date, score_type, score, lesson_order
            FROM academic_homework_scores
            WHERE enrollment_id = %s
            ORDER BY lesson_order, lesson_label
            """,
            (enrollment_id,),
        ).fetchall()

        homework_grades = _homework_payload(hw_rows)

        exam_rows = conn.execute(
            """
            SELECT label, exam_name, attempt, score
            FROM academic_exam_results
            WHERE enrollment_id = %s
            ORDER BY label
            """,
            (enrollment_id,),
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
