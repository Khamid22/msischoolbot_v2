"""Admin API v1 router.

Preserves the legacy admin-session gate exactly: a session whose auth_role
normalizes to "admin" (which includes owner logins) may call admin APIs.
Sub-role scoping via admin_role is a later hardening step.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.internal_operations.academics.routes import router as academic_router
from backend.modules.communications.announcements_api import router as announcements_router
from backend.modules.communications.chat_api import router as chat_router
from backend.internal_operations.support.api_routes import router as complaints_router
from backend.internal_operations.people.parents.api_routes import router as parents_router
from backend.internal_operations.finance.api_routes import router as payments_router
from backend.internal_operations.academics.office_hours_routes import router as office_hours_router
from backend.internal_operations.resources.api_routes import progress_router as resource_progress_router
from backend.internal_operations.resources.api_routes import router as resources_router
from backend.internal_operations.people.students.api_routes import router as students_router
from backend.core.access.roles import normalize_role


def require_admin_session(request: Request):
    if normalize_role(request.session.get("auth_role")) != "admin":
        raise HTTPException(status_code=401, detail="Admin authentication required.")


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin_session)])
router.include_router(academic_router)
router.include_router(announcements_router)
router.include_router(chat_router)
router.include_router(complaints_router)
router.include_router(parents_router)
router.include_router(payments_router)
router.include_router(office_hours_router)
router.include_router(resource_progress_router)
router.include_router(resources_router)
router.include_router(students_router)

__all__ = ["router"]
