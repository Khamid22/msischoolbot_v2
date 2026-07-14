"""System-admin academic router assembled from focused route modules."""

from fastapi import APIRouter

from backend.internal_operations.academics.class_routes import router as class_router
from backend.internal_operations.academics.curriculum_routes import (
    router as curriculum_router,
)
from backend.internal_operations.academics.gradebook_routes import (
    router as gradebook_router,
)
from backend.internal_operations.academics.group_routes import router as group_router
from backend.internal_operations.academics.timetable_routes import (
    router as timetable_router,
)


router = APIRouter(prefix="/academic")
router.include_router(class_router)
router.include_router(group_router)
router.include_router(curriculum_router)
router.include_router(timetable_router)
router.include_router(gradebook_router)


__all__ = ["router"]
