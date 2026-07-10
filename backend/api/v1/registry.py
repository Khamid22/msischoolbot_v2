"""Application registry for module-owned HTTP and page adapters."""

from backend.pages.academics.director import register_academic_director_page_routes
from backend.pages.academics.hod import register_head_of_department_page_routes
from backend.services.academics.rating import clear_group_cache
from backend.pages.admin.home import register_admin_page_routes
from backend.pages.parents.home import register_parent_invite_routes, register_parent_page_routes
from backend.pages.portal.home import register_portal_routes
from backend.pages.staff.ceo import register_ceo_page_routes
from backend.pages.staff.hr import register_hr_manager_page_routes
from backend.pages.staff.support import register_customer_support_page_routes
from backend.pages.students.home import register_student_page_routes
from backend.pages.teachers.home import register_teacher_page_routes


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
