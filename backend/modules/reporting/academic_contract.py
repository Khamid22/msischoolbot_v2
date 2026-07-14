"""Public academic read contract consumed by reporting.

Reporting receives raw academic rows through this service boundary instead of
importing the academics repository directly.
"""

from backend.modules.reporting import academic_repository as repository


def list_schema_tables(conn):
    return repository.list_msi_v2_table_names(conn)


def list_subject_dashboards(conn, subject_name):
    return repository.list_subject_dashboard_rows(conn, subject_name)


def list_dataset_enrollments(conn, school_code):
    return repository.list_internal_dataset_enrollment_rows(conn, school_code)


def list_dataset_lessons(conn, school_code):
    return repository.list_internal_dataset_lesson_rows(conn, school_code)


def list_dataset_attendance(conn, school_code):
    return repository.list_internal_dataset_attendance_rows(conn, school_code)


def list_dataset_homework(conn, school_code):
    return repository.list_internal_dataset_homework_rows(conn, school_code)


def list_dataset_exams(conn, school_code):
    return repository.list_internal_dataset_exam_rows(conn, school_code)


def list_overview_enrollments(conn, school_code):
    return repository.list_internal_overview_enrollment_rows(conn, school_code)


def list_overview_homework(conn, school_code):
    return repository.list_internal_overview_homework_rows(conn, school_code)


def list_overview_exams(conn, school_code):
    return repository.list_internal_overview_exam_rows(conn, school_code)


def list_overview_attendance(conn, school_code):
    return repository.list_internal_overview_attendance_rows(conn, school_code)


def get_enrollment_dashboard(
    conn,
    *,
    public_dashboard_id,
    normalized_school,
    normalized_subject,
    normalized_group,
):
    return repository.get_enrollment_dashboard_row(
        conn,
        public_dashboard_id=public_dashboard_id,
        normalized_school=normalized_school,
        normalized_subject=normalized_subject,
        normalized_group=normalized_group,
    )


def list_enrollment_attendance(conn, group_id, student_id):
    return repository.list_enrollment_attendance_rows(conn, group_id, student_id)


def list_enrollment_homework(conn, group_id, student_id):
    return repository.list_enrollment_homework_rows(conn, group_id, student_id)


def list_enrollment_exams(conn, group_id, student_id):
    return repository.list_enrollment_exam_rows(conn, group_id, student_id)


__all__ = [
    "get_enrollment_dashboard",
    "list_dataset_attendance",
    "list_dataset_enrollments",
    "list_dataset_exams",
    "list_dataset_homework",
    "list_dataset_lessons",
    "list_enrollment_attendance",
    "list_enrollment_exams",
    "list_enrollment_homework",
    "list_overview_attendance",
    "list_overview_enrollments",
    "list_overview_exams",
    "list_overview_homework",
    "list_schema_tables",
    "list_subject_dashboards",
]
