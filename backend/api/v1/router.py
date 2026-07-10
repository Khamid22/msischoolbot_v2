"""API v1 router registry."""

from fastapi import APIRouter

from backend.api.v1.academics.director_router import router as academic_director_router
from backend.api.v1.admin.routes import router as admin_router
from backend.api.v1.staff.ceo import router as ceo_router
from backend.api.v1.staff.support import router as customer_support_router
from backend.api.v1.academics.hod_router import router as head_of_department_router
from backend.api.v1.staff.hr import router as hr_manager_router
from backend.api.v1.parents.routes import router as parent_router
from backend.api.v1.students.routes import router as student_router
from backend.api.v1.teachers.routes import router as teacher_router

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
