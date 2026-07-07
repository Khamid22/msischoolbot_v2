"""Single role registry: canonical roles, normalization, routing and display helpers."""

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

# Roles a session may carry; "owner" normalizes to admin and is never stored.
VALID_ROLES = {
    ROLE_ADMIN,
    ROLE_SYSTEM_ADMIN,
    ROLE_CEO,
    ROLE_HR_MANAGER,
    ROLE_CUSTOMER_SUPPORT,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLE_PARENT,
    ROLE_ACADEMIC_DIRECTOR,
    ROLE_HEAD_OF_DEPARTMENT,
}

ROLE_DASHBOARD_PATHS = {
    "admin": "/admin",
    "system_admin": "/admin",
    "ceo": "/ceo",
    "hr_manager": "/hr",
    "customer_support": "/support",
    "student": "/student",
    "teacher": "/teacher",
    "parent": "/parent",
    "academic_director": "/academic-director",
    "head_of_department": "/head-of-department",
}

ROLE_DISPLAY_NAMES = {
    "admin": "Admin",
    "system_admin": "System Admin",
    "ceo": "CEO",
    "hr_manager": "HR Manager",
    "customer_support": "Customer Support",
    "student": "Student",
    "teacher": "Teacher",
    "parent": "Parent",
    "academic_director": "Academic Director",
    "head_of_department": "Head of Department",
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
    "hr": "hr_manager",
    "hr-manager": "hr_manager",
    "hr_manager": "hr_manager",
    "hr manager": "hr_manager",
    "customersupport": "customer_support",
    "customer-support": "customer_support",
    "customer_support": "customer_support",
    "customer support": "customer_support",
    "support": "customer_support",
    "sales": "customer_support",
    "ceo": "ceo",
    "systemadmin": "system_admin",
    "system-admin": "system_admin",
    "system_admin": "system_admin",
    "system admin": "system_admin",
    "admin": "admin",
    "owner": "admin",
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
    "ROLE_OWNER",
    "ROLE_SYSTEM_ADMIN",
    "ROLE_CEO",
    "ROLE_ADMIN",
    "ROLE_TEACHER",
    "ROLE_CUSTOMER_SUPPORT",
    "ROLE_HR_MANAGER",
    "ROLE_PARENT",
    "ROLE_STUDENT",
    "ROLE_ACADEMIC_DIRECTOR",
    "ROLE_HEAD_OF_DEPARTMENT",
    "ALL_ROLES",
    "VALID_ROLES",
    "ROLE_DASHBOARD_PATHS",
    "ROLE_DISPLAY_NAMES",
    "normalize_role",
    "is_valid_role",
    "dashboard_path_for_role",
    "role_display_name",
]
