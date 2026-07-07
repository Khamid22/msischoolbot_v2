"""Teacher API v1 router."""

from fastapi import APIRouter, Depends

from backend.api.v1.teacher.office_hours import router as office_hours_router
from backend.security import require_role

router = APIRouter(prefix="/teacher", dependencies=[Depends(require_role("teacher"))])
router.include_router(office_hours_router)

__all__ = ["router"]
