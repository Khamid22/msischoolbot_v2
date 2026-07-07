"""Admin API v1 router.

Preserves the legacy admin-session gate exactly: a session whose auth_role
normalizes to "admin" (which includes owner logins) may call admin APIs.
Sub-role scoping via admin_role is a later hardening step.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.v1.admin.chat import router as chat_router
from backend.api.v1.admin.office_hours import router as office_hours_router
from backend.security.roles import normalize_role


def require_admin_session(request: Request):
    if normalize_role(request.session.get("auth_role")) != "admin":
        raise HTTPException(status_code=401, detail="Admin authentication required.")


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin_session)])
router.include_router(chat_router)
router.include_router(office_hours_router)

__all__ = ["router"]
