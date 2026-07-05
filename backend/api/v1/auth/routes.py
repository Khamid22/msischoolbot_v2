"""Auth API routes for MSI LMS Portal."""

from fastapi import APIRouter, Depends

from backend.api import ApiSuccess, api_success
from backend.security import get_current_user_role, role_has_permission
from backend.security.permissions import ALL_PERMISSIONS
from backend.utils import session as session_utils

router = APIRouter()


@router.get("/api/v1/auth/me", response_model=ApiSuccess, tags=["identity"])
def get_current_user(role: str = Depends(get_current_user_role)):
    """
    Returns the authenticated user's profile metadata and resolved permissions.
    """
    login = session_utils.current_auth_login()

    # Compile a dictionary of permissions that this user has
    user_permissions = {perm: role_has_permission(role, perm) for perm in ALL_PERMISSIONS}

    data = {
        "login": login,
        "role": role,
        "permissions": user_permissions,
    }
    return api_success(data)


__all__ = ["get_current_user", "router"]
