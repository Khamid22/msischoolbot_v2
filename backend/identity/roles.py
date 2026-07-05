"""Canonical portal roles and role routing helpers."""

VALID_ROLES = {
    "admin",
    "system_admin",
    "ceo",
    "hr_manager",
    "customer_support",
    "student",
    "teacher",
    "parent",
    "academic_director",
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
}

_ROLE_ALIASES = {
    "academicdirector": "academic_director",
    "academic-director": "academic_director",
    "academic_director": "academic_director",
    "academic director": "academic_director",
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
        .replace("-", " ")
        .replace("\u2013", " ")
        .replace("\u2014", " ")
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
    "VALID_ROLES",
    "ROLE_DASHBOARD_PATHS",
    "ROLE_DISPLAY_NAMES",
    "normalize_role",
    "is_valid_role",
    "dashboard_path_for_role",
    "role_display_name",
]
