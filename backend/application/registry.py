"""Application registry for module-owned HTTP and page adapters."""

from backend.workspaces.academic_director.page import register_academic_director_page_routes
from backend.workspaces.head_of_departments.page import register_head_of_department_page_routes
from backend.modules.academics.rating import clear_group_cache
from backend.internal_operations.page import register_internal_operations_page_routes
from backend.workspaces.parent.page import register_parent_invite_routes, register_parent_page_routes
from backend.modules.accounts.page import register_portal_routes
from backend.workspaces.ceo.page import register_ceo_page_routes
from backend.workspaces.hr_manager.page import register_hr_manager_page_routes
from backend.workspaces.customer_support.page import register_customer_support_page_routes
from backend.workspaces.student.page import register_student_page_routes
from backend.workspaces.teacher.page import register_teacher_page_routes


def register_application_pages(app) -> None:
    """Register page adapters without introducing role-to-role dependencies."""

    register_internal_operations_page_routes(
        app,
        clear_group_cache=clear_group_cache,
    )
    register_portal_routes(app)
    register_student_page_routes(app)
    register_parent_page_routes(app)
    register_ceo_page_routes(app)
    register_hr_manager_page_routes(app)
    register_customer_support_page_routes(app)
    register_teacher_page_routes(app)
    register_academic_director_page_routes(app)
    register_head_of_department_page_routes(app)
    register_parent_invite_routes(app)


__all__ = ["register_application_pages"]
