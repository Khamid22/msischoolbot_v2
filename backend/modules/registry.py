"""Application registry for module-owned HTTP and page adapters."""

from backend.modules.academics.director_page import register_academic_director_page_routes
from backend.modules.academics.hod_page import register_head_of_department_page_routes
from backend.modules.academics.rating_service import clear_group_cache
from backend.modules.admin.page import register_admin_page_routes
from backend.modules.parents.page import register_parent_invite_routes, register_parent_page_routes
from backend.modules.portal.web import register_portal_routes
from backend.modules.staff.ceo_page import register_ceo_page_routes
from backend.modules.staff.hr_page import register_hr_manager_page_routes
from backend.modules.staff.support_page import register_customer_support_page_routes
from backend.modules.students.page import register_student_page_routes
from backend.modules.teachers.page import register_teacher_page_routes


def register_module_pages(app) -> None:
    """Register page adapters without introducing role-to-role dependencies."""

    render_admin_page = register_admin_page_routes(
        app,
        clear_group_cache=clear_group_cache,
    )
    register_portal_routes(app, render_admin_page=render_admin_page)
    register_student_page_routes(app)
    register_teacher_page_routes(app)
    register_parent_page_routes(app)
    register_ceo_page_routes(app)
    register_hr_manager_page_routes(app)
    register_customer_support_page_routes(app)
    register_academic_director_page_routes(app)
    register_head_of_department_page_routes(app)
    register_parent_invite_routes(app)


__all__ = ["register_module_pages"]
