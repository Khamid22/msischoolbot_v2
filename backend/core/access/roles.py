"""Single role registry: canonical roles, normalization, routing and display helpers."""

from backend.core.access.domain_types import Role


ROLE_CEO = Role.CEO.value
ROLE_TEACHER = Role.TEACHER.value
ROLE_CUSTOMER_SUPPORT = Role.CUSTOMER_SUPPORT.value
ROLE_PARENT = Role.PARENT.value
ROLE_STUDENT = Role.STUDENT.value
ROLE_ACADEMIC_DIRECTOR = Role.ACADEMIC_DIRECTOR.value
ROLE_HEAD_OF_DEPARTMENT = Role.HEAD_OF_DEPARTMENT.value
ROLE_HR_MANAGER = Role.HR_MANAGER.value

WORKSPACE_ROLES = {
    ROLE_CEO,
    ROLE_ACADEMIC_DIRECTOR,
    ROLE_HEAD_OF_DEPARTMENT,
    ROLE_CUSTOMER_SUPPORT,
    ROLE_STUDENT,
    ROLE_PARENT,
    ROLE_TEACHER,
    ROLE_HR_MANAGER,
}

# Staff roles that have a dedicated browser workspace.
NON_PORTAL_STAFF_ROLES: set[str] = set()

ALL_ROLES = {
    ROLE_CEO,
    ROLE_TEACHER,
    ROLE_CUSTOMER_SUPPORT,
    ROLE_PARENT,
    ROLE_STUDENT,
    ROLE_ACADEMIC_DIRECTOR,
    ROLE_HEAD_OF_DEPARTMENT,
    ROLE_HR_MANAGER,
}

# Roles a canonical account or authenticated session may carry.
VALID_ROLES = set(ALL_ROLES)

ROLE_DASHBOARD_PATHS = {
    "ceo": "/ceo",
    "customer_support": "/customer-support",
    "student": "/student",
    "parent": "/parent",
    "teacher": "/teacher",
    "academic_director": "/academic-director",
    "head_of_department": "/head-of-departments",
    "hr_manager": "/hr-manager",
}

ROLE_DISPLAY_NAMES = {
    "ceo": "CEO",
    "customer_support": "Customer Support",
    "student": "Student",
    "parent": "Parent",
    "teacher": "Teacher",
    "academic_director": "Academic Director",
    "head_of_department": "Head of Departments",
    "hr_manager": "HR Manager",
}

_ROLE_ALIASES = {
    "academicdirector": "academic_director",
    "academic-director": "academic_director",
    "academic_director": "academic_director",
    "academic director": "academic_director",
    "headofdepartment": "head_of_department",
    "head-of-department": "head_of_department",
    "head_of_department": "head_of_department",
    "head of department": "head_of_department",
    "hod": "head_of_department",
    "hrmanager": "hr_manager",
    "hr-manager": "hr_manager",
    "hr_manager": "hr_manager",
    "hr manager": "hr_manager",
    "hr": "hr_manager",
    "customersupport": "customer_support",
    "customer-support": "customer_support",
    "customer_support": "customer_support",
    "customer support": "customer_support",
    "support": "customer_support",
    "sales": "customer_support",
    "ceo": "ceo",
    "student": "student",
    "teacher": "teacher",
    "parent": "parent",
}


def normalize_role(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    separated = (
        raw.replace("_", " ")
        .replace("–", " ")
        .replace("—", " ")
        .replace("-", " ")
    )
    words = " ".join(separated.split()).casefold()
    compact = words.replace(" ", "")
    direct = raw.strip().casefold()
    return (
        _ROLE_ALIASES.get(direct)
        or _ROLE_ALIASES.get(words)
        or _ROLE_ALIASES.get(compact)
        or ""
    )


def is_valid_role(role) -> bool:
    return normalize_role(role) in VALID_ROLES


def dashboard_path_for_role(role) -> str:
    return ROLE_DASHBOARD_PATHS.get(normalize_role(role), "/")


def role_display_name(role) -> str:
    normalized = normalize_role(role)
    return ROLE_DISPLAY_NAMES.get(normalized, "Unknown Role")


__all__ = [
    "ROLE_CEO",
    "ROLE_TEACHER",
    "ROLE_CUSTOMER_SUPPORT",
    "ROLE_PARENT",
    "ROLE_STUDENT",
    "ROLE_ACADEMIC_DIRECTOR",
    "ROLE_HEAD_OF_DEPARTMENT",
    "ROLE_HR_MANAGER",
    "WORKSPACE_ROLES",
    "NON_PORTAL_STAFF_ROLES",
    "ALL_ROLES",
    "VALID_ROLES",
    "ROLE_DASHBOARD_PATHS",
    "ROLE_DISPLAY_NAMES",
    "normalize_role",
    "is_valid_role",
    "dashboard_path_for_role",
    "role_display_name",
]
