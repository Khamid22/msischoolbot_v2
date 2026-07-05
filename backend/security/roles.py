"""Supported roles and normalization helpers."""

ROLE_OWNER = "owner"
ROLE_SYSTEM_ADMIN = "system_admin"
ROLE_CEO = "ceo"
ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_CUSTOMER_SUPPORT = "customer_support"
ROLE_HR_MANAGER = "hr_manager"
ROLE_PARENT = "parent"
ROLE_STUDENT = "student"
ROLE_ACADEMIC_DIRECTOR = "academic_director"
ROLE_HEAD_OF_DEPARTMENT = "head_of_department"

ALL_ROLES = {
    ROLE_OWNER,
    ROLE_SYSTEM_ADMIN,
    ROLE_CEO,
    ROLE_ADMIN,
    ROLE_TEACHER,
    ROLE_CUSTOMER_SUPPORT,
    ROLE_HR_MANAGER,
    ROLE_PARENT,
    ROLE_STUDENT,
    ROLE_ACADEMIC_DIRECTOR,
    ROLE_HEAD_OF_DEPARTMENT,
}


def normalize_role(role: str) -> str:
    """Normalizes a role string to lowercase and stripped of whitespace."""
    if not role:
        return ""
    return str(role).strip().lower()
