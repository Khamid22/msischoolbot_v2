"""Authentication and authorization layer."""

from .forms import LoginForm, StudentPasswordChangeForm
from .policies import (
    is_admin_role,
    is_authenticated_session,
    is_student_role,
    normalize_auth_role,
)
from .session import (
    PortalUser,
    build_admin_user,
    build_student_user,
    configure_login_manager,
    load_portal_user,
)

__all__ = [
    "LoginForm",
    "StudentPasswordChangeForm",
    "PortalUser",
    "build_admin_user",
    "build_student_user",
    "load_portal_user",
    "configure_login_manager",
    "normalize_auth_role",
    "is_admin_role",
    "is_student_role",
    "is_authenticated_session",
]
