"""Public Student Records use cases."""

from backend.modules.domains.student_records.service import (
    get_dashboard_student_profile,
    get_student_db_id_by_enrollment_id,
    get_student_subject_enrollments,
    list_enrolled_subject_options,
    record_student_activity,
    resolve_public_dashboard_for_student_row,
)


def parent_can_access_dashboard(parent_id, dashboard_student_id):
    from backend.modules.domains.parent_relationships.contracts import (
        parent_can_access_dashboard as can_access_dashboard,
    )

    return can_access_dashboard(parent_id, dashboard_student_id)


__all__ = [
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "get_student_subject_enrollments",
    "list_enrolled_subject_options",
    "parent_can_access_dashboard",
    "record_student_activity",
    "resolve_public_dashboard_for_student_row",
]
