"""Compatibility wrapper for student profile services.

Student profile ownership moved to ``backend.domains.students.service`` in
DB-3. Keep this module temporarily for older imports.
"""

from backend.domains.students.service import (  # noqa: F401
    extract_auto_student_context,
    get_admin_student_profile,
    get_dashboard_student_profile,
    get_student_db_id_by_enrollment_id,
    split_name,
)

__all__ = [
    "extract_auto_student_context",
    "get_admin_student_profile",
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "split_name",
]
