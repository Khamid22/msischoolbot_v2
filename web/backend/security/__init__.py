"""Re-export role constants, permission constants, and FastAPI security dependencies."""

from web.backend.security.roles import (
    ROLE_OWNER,
    ROLE_CEO,
    ROLE_ADMIN,
    ROLE_TEACHER,
    ROLE_CUSTOMER_SUPPORT,
    ROLE_PARENT,
    ROLE_STUDENT,
    ALL_ROLES,
    normalize_role,
)
from web.backend.security.permissions import (
    PERMISSION_VIEW_DASHBOARD,
    PERMISSION_MANAGE_STUDENTS,
    PERMISSION_MANAGE_TEACHERS,
    PERMISSION_MANAGE_PARENTS,
    PERMISSION_MANAGE_ANNOUNCEMENTS,
    PERMISSION_MANAGE_RESOURCES,
    PERMISSION_MANAGE_COMPLAINTS,
    PERMISSION_MANAGE_PAYMENTS,
    PERMISSION_MANAGE_ACADEMICS,
    PERMISSION_SYSTEM_SETTINGS,
    ALL_PERMISSIONS,
    role_has_permission,
)
from web.backend.security.dependencies import (
    get_current_user_role,
    require_role,
    require_permission,
)

__all__ = [
    "ROLE_OWNER",
    "ROLE_CEO",
    "ROLE_ADMIN",
    "ROLE_TEACHER",
    "ROLE_CUSTOMER_SUPPORT",
    "ROLE_PARENT",
    "ROLE_STUDENT",
    "ALL_ROLES",
    "normalize_role",
    "PERMISSION_VIEW_DASHBOARD",
    "PERMISSION_MANAGE_STUDENTS",
    "PERMISSION_MANAGE_TEACHERS",
    "PERMISSION_MANAGE_PARENTS",
    "PERMISSION_MANAGE_ANNOUNCEMENTS",
    "PERMISSION_MANAGE_RESOURCES",
    "PERMISSION_MANAGE_COMPLAINTS",
    "PERMISSION_MANAGE_PAYMENTS",
    "PERMISSION_MANAGE_ACADEMICS",
    "PERMISSION_SYSTEM_SETTINGS",
    "ALL_PERMISSIONS",
    "role_has_permission",
    "get_current_user_role",
    "require_role",
    "require_permission",
]
