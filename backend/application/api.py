from fastapi import APIRouter

from backend.modules.people.academic_director.workspace.api import router as academic_director_router
from backend.modules.people.ceo.workspace.api import router as ceo_router
from backend.modules.people.customer_support.workspace.api import router as customer_support_router
from backend.modules.people.head_of_department.workspace.api import router as head_of_department_router
from backend.modules.people.parent.workspace.api import router as parent_router
from backend.modules.people.student.workspace.api import router as student_router
from backend.modules.domains.recruitment.api import router as recruitment_router
from backend.modules.domains.recruitment.handoff_api import router as recruitment_handoff_router
from backend.modules.domains.reporting.recruitment.api import router as hr_analytics_router
from backend.application.module_spec import ModuleSpec

router = APIRouter(prefix="/api/v1")

API_MODULES = (
    ModuleSpec("academic_director", academic_director_router),
    ModuleSpec("head_of_department", head_of_department_router),
    ModuleSpec("student", student_router),
    ModuleSpec("parent", parent_router),
    ModuleSpec("ceo", ceo_router),
    ModuleSpec("customer_support", customer_support_router),
    ModuleSpec("recruitment", recruitment_router),
    ModuleSpec("recruitment_handoffs", recruitment_handoff_router),
    ModuleSpec("hr_analytics", hr_analytics_router),
)

for module_spec in API_MODULES:
    if module_spec.api_router is not None:
        router.include_router(module_spec.api_router)

__all__ = ["API_MODULES", "router"]
