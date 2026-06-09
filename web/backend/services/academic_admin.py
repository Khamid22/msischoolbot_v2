"""Admin-facing academic operations and payload shaping."""

from web.backend import queries
from web.backend.services.academic_postgres import (
    create_group,
    create_subject,
    ensure_academic_schema,
    list_academic_admin_rows,
    record_attendance,
    record_coin_event,
    record_exam_result,
    record_homework_score,
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
    subject_id = str(payload.get("subject_id", "") or "").strip()
    group_name = str(payload.get("group_name", "") or "").strip()
    group_code = str(payload.get("group_code", "") or "").strip()
    if not school_code or not subject_id or not group_name:
        raise ValueError("School, subject, and group name are required.")
    create_group(school_code, int(subject_id), group_name, group_code)
    return {"school_code": school_code}


def get_group_gradebook(group_id):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required")

    with queries.connect_auth_db() as conn:
        ensure_academic_schema(conn)
        group_row = conn.execute(
            """
            SELECT g.id, g.name, g.code, s.code AS school_code, sub.name AS subject_name
            FROM academic_groups g
            JOIN academic_schools s ON s.id = g.school_id
            JOIN academic_subjects sub ON sub.id = g.subject_id
            WHERE g.id = ?
            """,
            (group_id,),
        ).fetchone()
        if not group_row:
            return None

        lesson_rows = conn.execute(
            """
            SELECT id, lesson_number, topic, lesson_date, lesson_order
            FROM academic_lessons
            WHERE group_id = ?
            ORDER BY lesson_order, lesson_number
            """,
            (group_id,),
        ).fetchall()

        enrollment_rows = conn.execute(
            """
            SELECT id, public_dashboard_id, full_name, average_grade, coins,
                   active, enrollment_status, disqualification_reason, disqualified_at
            FROM academic_enrollments
            WHERE group_id = ?
            ORDER BY
              CASE enrollment_status
                WHEN 'active' THEN 0
                WHEN 'disqualified' THEN 1
                ELSE 2
              END,
              full_name
            """,
            (group_id,),
        ).fetchall()

        active_enrollment_rows = [
            row
            for row in enrollment_rows
            if int(row["active"] or 0) == 1 and str(row["enrollment_status"] or "active") == "active"
        ]
        enrollment_ids = [int(row["id"]) for row in active_enrollment_rows]
        attendance_by_enrollment = {}
        homework_by_enrollment = {}
        if enrollment_ids:
            placeholders = ",".join("?" * len(enrollment_ids))
            for row in conn.execute(
                f"""
                SELECT enrollment_id, lesson_label, status
                FROM academic_attendance_records
                WHERE enrollment_id IN ({placeholders})
                """,
                enrollment_ids,
            ).fetchall():
                attendance_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = str(row["status"])
            for row in conn.execute(
                f"""
                SELECT enrollment_id, lesson_label, score
                FROM academic_homework_scores
                WHERE enrollment_id IN ({placeholders})
                """,
                enrollment_ids,
            ).fetchall():
                homework_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = float(row["score"])

    return {
        "ok": True,
        "group": {
            "id": int(group_row["id"]),
            "name": str(group_row["name"]),
            "code": str(group_row["code"] or ""),
            "schoolCode": str(group_row["school_code"]),
            "subjectName": str(group_row["subject_name"]),
        },
        "lessons": [
            {
                "id": int(row["id"]),
                "lessonNumber": str(row["lesson_number"]),
                "topic": str(row["topic"] or ""),
                "date": str(row["lesson_date"] or ""),
                "order": int(row["lesson_order"] or 0),
            }
            for row in lesson_rows
        ],
        "enrollments": [
            {
                "enrollmentId": int(row["id"]),
                "fullName": str(row["full_name"]),
                "averageGrade": float(row["average_grade"] or 0),
                "coins": int(row["coins"] or 0),
                "attendance": attendance_by_enrollment.get(int(row["id"]), {}),
                "homework": homework_by_enrollment.get(int(row["id"]), {}),
            }
            for row in active_enrollment_rows
        ],
        "allEnrollments": [
            {
                "enrollmentId": int(row["id"]),
                "publicDashboardId": int(row["public_dashboard_id"] or 0),
                "fullName": str(row["full_name"]),
                "averageGrade": float(row["average_grade"] or 0),
                "coins": int(row["coins"] or 0),
                "active": bool(row["active"]),
                "status": str(row["enrollment_status"] or "active"),
                "disqualificationReason": str(row["disqualification_reason"] or ""),
                "disqualifiedAt": str(row["disqualified_at"] or ""),
            }
            for row in enrollment_rows
        ],
    }


def update_enrollment_status(enrollment_id, status, reason=""):
    enrollment_id = int(enrollment_id or 0)
    if enrollment_id <= 0:
        raise ValueError("Enrollment id is required.")
    normalized_status = str(status or "").strip().casefold()
    if normalized_status not in {"active", "disqualified"}:
        raise ValueError("Unsupported enrollment status.")

    from datetime import datetime

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    active = 1 if normalized_status == "active" else 0
    disqualified_at = "" if normalized_status == "active" else now
    disqualification_reason = "" if normalized_status == "active" else str(reason or "").strip()

    with queries.connect_auth_db() as conn:
        ensure_academic_schema(conn)
        row = conn.execute(
            "SELECT id FROM academic_enrollments WHERE id = ?",
            (enrollment_id,),
        ).fetchone()
        if not row:
            raise ValueError("Enrollment not found.")
        conn.execute(
            """
            UPDATE academic_enrollments
            SET active = ?,
                enrollment_status = ?,
                disqualification_reason = ?,
                disqualified_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                active,
                normalized_status,
                disqualification_reason,
                disqualified_at,
                now,
                enrollment_id,
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


def record_attendance_from_payload(payload):
    return record_attendance(
        int(payload.get("enrollment_id", 0)),
        payload.get("lesson_label", ""),
        payload.get("status", ""),
        topic=payload.get("topic", ""),
        lesson_date=payload.get("lesson_date", ""),
        attendance_type=payload.get("attendance_type", ""),
    )


def record_homework_from_payload(payload):
    return record_homework_score(
        int(payload.get("enrollment_id", 0)),
        payload.get("lesson_label", ""),
        float(payload.get("score", 0)),
        topic=payload.get("topic", ""),
        lesson_date=payload.get("lesson_date", ""),
        score_type=payload.get("score_type", "Homework"),
    )


def record_exam_from_payload(payload):
    return record_exam_result(
        int(payload.get("enrollment_id", 0)),
        payload.get("label", ""),
        float(payload.get("score", 0)),
        exam_name=payload.get("exam_name", ""),
        attempt=payload.get("attempt", ""),
    )


def record_coin_from_payload(payload):
    return record_coin_event(
        int(payload.get("enrollment_id", 0)),
        int(payload.get("amount", 0)),
        source=payload.get("source", "manual"),
    )


def update_enrollment_status_from_payload(enrollment_id, payload):
    return update_enrollment_status(
        enrollment_id,
        payload.get("status", ""),
        reason=payload.get("reason", ""),
    )
