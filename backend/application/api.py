"""API v1 router registry."""

from fastapi import APIRouter

from backend.workspaces.academic_director.api import router as academic_director_router
from backend.internal_operations.api_router import router as internal_operations_router
from backend.workspaces.ceo.api import router as ceo_router
from backend.workspaces.customer_support.api import router as customer_support_router
from backend.workspaces.head_of_departments.api import router as head_of_department_router
from backend.workspaces.hr_manager.api import router as hr_manager_router
from backend.workspaces.parent.api import router as parent_router
from backend.workspaces.student.api import router as student_router

router = APIRouter(prefix="/api/v1")

router.include_router(academic_director_router)
router.include_router(head_of_department_router)
router.include_router(student_router)
router.include_router(parent_router)
router.include_router(internal_operations_router)
router.include_router(ceo_router)
router.include_router(hr_manager_router)
router.include_router(customer_support_router)

__all__ = ["router"]
