"""Auth API routes for MSI LMS Portal."""

from fastapi import APIRouter, Depends

from backend.api import ApiSuccess, api_success
from backend.security import CurrentUser, get_current_user as get_current_user_dependency, role_has_permission
from backend.security.permissions import ALL_PERMISSIONS

router = APIRouter()


@router.get("/api/v1/auth/me", response_model=ApiSuccess, tags=["identity"])
def get_current_user(user: CurrentUser = Depends(get_current_user_dependency)):
    """
    Returns the authenticated user's profile metadata and resolved permissions.
    """
    role = user.role

    # Compile a dictionary of permissions that this user has
    user_permissions = {perm: role_has_permission(role, perm) for perm in ALL_PERMISSIONS}

    data = {
        "login": user.login,
        "role": role,
        "permissions": user_permissions,
    }
    return api_success(data)


__all__ = ["get_current_user", "router"]
