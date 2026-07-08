"""HTML/page-shell routers."""

from backend.pages.academic_director import register_academic_director_page_routes
from backend.pages.ceo import register_ceo_page_routes
from backend.pages.customer_support import register_customer_support_page_routes
from backend.pages.head_of_department import register_head_of_department_page_routes
from backend.pages.hr_manager import register_hr_manager_page_routes
from backend.pages.teacher import register_teacher_page_routes

__all__ = [
    "register_academic_director_page_routes",
    "register_ceo_page_routes",
    "register_customer_support_page_routes",
    "register_head_of_department_page_routes",
    "register_hr_manager_page_routes",
    "register_teacher_page_routes",
]
