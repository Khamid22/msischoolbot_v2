"""Supported roles and normalization helpers."""

ROLE_OWNER = "owner"
ROLE_CEO = "ceo"
ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_CUSTOMER_SUPPORT = "customer_support"
ROLE_PARENT = "parent"
ROLE_STUDENT = "student"

ALL_ROLES = {
    ROLE_OWNER,
    ROLE_CEO,
    ROLE_ADMIN,
    ROLE_TEACHER,
    ROLE_CUSTOMER_SUPPORT,
    ROLE_PARENT,
    ROLE_STUDENT,
}


def normalize_role(role: str) -> str:
    """Normalizes a role string to lowercase and stripped of whitespace."""
    if not role:
        return ""
    return str(role).strip().lower()
