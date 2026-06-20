import os
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from web.backend.security import get_current_user_role, role_has_permission
from web.backend.security.permissions import ALL_PERMISSIONS
from web.backend.api import api_success, api_message, ApiMessage, ApiSuccess
from web.backend.utils import session as session_utils

router = APIRouter()

# Set at startup in server.py
STATIC_FOLDER = ""


@router.get("/manifest.webmanifest")
def manifest():
    path = os.path.join(STATIC_FOLDER, "manifest.webmanifest")
    if not os.path.isfile(path):
        return {"error": "manifest not found"}
    return FileResponse(
        path,
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/sw.js")
def service_worker():
    path = os.path.join(STATIC_FOLDER, "js", "sw.js")
    if not os.path.isfile(path):
        return {"error": "service worker not found"}
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/api/v1/system/status", response_model=ApiMessage, tags=["system"])
def system_status():
    """Returns the status of the MSI School backend API."""
    return api_message("MSI School Backend API is running and operational.")


@router.get("/api/v1/auth/me", response_model=ApiSuccess, tags=["identity"])
def get_current_user(role: str = Depends(get_current_user_role)):
    """
    Returns the authenticated user's profile metadata and resolved permissions.
    """
    login = session_utils.current_auth_login()

    # Compile a dictionary of permissions that this user has
    user_permissions = {
        perm: role_has_permission(role, perm)
        for perm in ALL_PERMISSIONS
    }

    data = {
        "login": login,
        "role": role,
        "permissions": user_permissions,
    }
    return api_success(data)

