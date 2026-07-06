"""Compatibility wrapper for student domain account services.

Student service ownership moved to ``backend.domains.students.service`` in DB-3.
Keep this module temporarily so ``backend.identity.account_service`` and older
imports continue to work during migration.
"""

from backend.domains.students.service import (  # noqa: F401
    list_students_for_admin,
    record_student_activity,
    update_student_admin_profile,
)

__all__ = [
    "list_students_for_admin",
    "record_student_activity",
    "update_student_admin_profile",
]
