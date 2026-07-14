"""Gradebook service operations."""


from backend.core.database import connect_auth_db
from backend.modules.academics.assessments.filters import is_exam_performance_row
from backend.modules.academics.calendar import repository as calendar_repository
from backend.modules.academics.timetable import repository as timetable_repository
from backend.modules.academics.calendar.service import serialize_calendar_closure
from backend.modules.academics.groups import repository as groups_repository
from backend.modules.academics.gradebook import repository
from backend.modules.academics.gradebook.window import _gradebook_lesson_payload, _gradebook_lesson_window

def get_group_gradebook(
    group_id, *, lesson_limit=0, lesson_cursor="", lesson_direction="",
    anchor_date="", lesson_month="", section="all"
):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required")

    with connect_auth_db() as conn:
        group_row = repository.get_group_header(conn, group_id)
        if not group_row:
            return None

        active_schedule_row = timetable_repository.get_active_group_schedule(
            conn, int(group_row["id"])
        )
        closure_rows = list(calendar_repository.list_effective_group_closures(
            conn, int(group_row["school_id"]), int(group_row["id"])
        ))

        lesson_rows = repository.list_primary_lesson_rows(conn, int(group_row["id"]))
        exception_rows = repository.list_active_cancellation_rows(
            conn, int(group_row["id"])
        )

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
                month=lesson_month,
                closures=closure_rows,
            )
        else:
            lesson_payload, page_info = _gradebook_lesson_window(
                full_lesson_payload, limit=0, closures=closure_rows
            )
        record_lesson_ids = [int(item["id"]) for item in lesson_payload if int(item["id"]) > 0]

        enrollment_rows = repository.list_group_enrollment_rows(
            conn, int(group_row["id"])
        )

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
            for row in repository.list_attendance_rows(
                conn, enrollment_ids, record_lesson_ids
            ):
                attendance_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = str(row["status"])
                attendance_by_lesson_id.setdefault(int(row["enrollment_id"]), {})[
                    str(int(row["lesson_session_id"]))
                ] = str(row["status"])
            for row in repository.list_homework_rows(
                conn, enrollment_ids, record_lesson_ids
            ):
                homework_by_enrollment.setdefault(int(row["enrollment_id"]), {})[
                    str(row["lesson_label"])
                ] = float(row["score"])
                homework_by_lesson_id.setdefault(int(row["enrollment_id"]), {})[
                    str(int(row["lesson_session_id"]))
                ] = float(row["score"])
        if enrollment_ids and needs_exam_records:
            for row in repository.list_exam_rows(conn, enrollment_ids):
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
        "schedule": (
            {
                **dict(active_schedule_row),
                "group_id": int(group_row["legacy_group_id"] or group_row["id"]),
                "group_name": str(group_row["group_name"]),
                "school_code": str(group_row["school_key"]),
                "subject_name": str(group_row["subject_name"]),
                "status": "active",
            }
            if active_schedule_row
            else None
        ),
        "lessons": lesson_payload,
        "pageInfo": page_info,
        "calendarClosures": [serialize_calendar_closure(dict(row)) for row in closure_rows],
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


def get_enrollment_gradebook_summary(enrollment_id):
    with connect_auth_db() as conn:
        enrollment = groups_repository.get_enrollment_by_legacy_id(
            conn, int(enrollment_id or 0)
        )
        if not enrollment:
            raise ValueError("Enrollment not found.")
        row = repository.get_enrollment_metrics(
            conn,
            group_id=int(enrollment["group_id"]),
            student_id=int(enrollment["student_id"]),
        )
    total = int(row["attendance_total"] or 0)
    present = int(row["attendance_present"] or 0)
    return {
        "averageGrade": float(row["average_grade"] or 0),
        "attendancePresent": present,
        "attendanceTotal": total,
        "attendanceRate": round((present / total) * 100) if total else None,
    }
