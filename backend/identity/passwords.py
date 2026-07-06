"""Compatibility wrapper for student password services."""

from backend.domains.students.service import (  # noqa: F401
    admin_change_student_password,
    change_student_password,
)

__all__ = ["admin_change_student_password", "change_student_password"]
