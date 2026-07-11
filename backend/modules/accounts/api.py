"""Canonical account API routes for MSI LMS Portal."""

from fastapi import APIRouter, Depends, Request

from backend.core.http import ApiSuccess, api_error, api_success
from backend.modules.accounts.schemas import PasswordChangeRequest, PasswordChangeResult
from backend.modules.accounts.service import change_own_password
from backend.core.access import CurrentUser, get_current_user as get_current_user_dependency, role_has_permission
from backend.core.access.permissions import ALL_PERMISSIONS

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
        "account_id": user.account_id,
        "login": user.login,
        "role": role,
        "must_change_password": user.must_change_password,
        "session_version": user.session_version,
        "permissions": user_permissions,
    }
    return api_success(data)


@router.patch(
    "/api/v1/auth/password",
    response_model=ApiSuccess[PasswordChangeResult],
    tags=["identity"],
)
def change_current_account_password(
    payload: PasswordChangeRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user_dependency),
):
    """Change the signed-in account password and refresh this session version."""

    outcome = change_own_password(
        user.account_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )
    if not outcome.changed:
        status_code = 401 if outcome.code == "current_password_incorrect" else 400
        return api_error(
            outcome.message or "Unable to change password.",
            code=outcome.code or "password_change_failed",
            status_code=status_code,
        )

    request.session["must_change_password"] = False
    request.session["session_version"] = outcome.session_version
    return api_success(
        PasswordChangeResult(
            changed=True,
            must_change_password=False,
            session_version=outcome.session_version,
        )
    )


__all__ = ["change_current_account_password", "get_current_user", "router"]
