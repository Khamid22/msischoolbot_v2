"""Head of Department JSON/action API v1 routes."""

from fastapi import APIRouter, Depends

from backend.api.v1.teacher_academy.hod import register_teacher_academy_routes
from backend.core.access import require_role

router = APIRouter(prefix="/head-of-department", dependencies=[Depends(require_role("head_of_department"))])
register_teacher_academy_routes(router)


__all__ = ["router"]
