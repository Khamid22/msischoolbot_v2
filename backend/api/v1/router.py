"""API v1 router registry."""

from fastapi import APIRouter

from backend.api.v1.academic_director.router import router as academic_director_router
from backend.api.v1.admin.router import router as admin_router
from backend.api.v1.ceo.router import router as ceo_router
from backend.api.v1.customer_support.router import router as customer_support_router
from backend.api.v1.head_of_department.router import router as head_of_department_router
from backend.api.v1.hr_manager.router import router as hr_manager_router
from backend.api.v1.parent.router import router as parent_router
from backend.api.v1.student.router import router as student_router
from backend.api.v1.teacher.router import router as teacher_router

router = APIRouter(prefix="/api/v1")

router.include_router(academic_director_router)
router.include_router(head_of_department_router)
router.include_router(teacher_router)
router.include_router(student_router)
router.include_router(parent_router)
router.include_router(admin_router)
router.include_router(ceo_router)
router.include_router(hr_manager_router)
router.include_router(customer_support_router)

__all__ = ["router"]
