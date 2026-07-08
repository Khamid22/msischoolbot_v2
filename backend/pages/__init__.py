"""HTML/page-shell routers."""

from backend.pages.ceo import register_ceo_page_routes
from backend.pages.customer_support import register_customer_support_page_routes
from backend.pages.hr_manager import register_hr_manager_page_routes

__all__ = [
    "register_ceo_page_routes",
    "register_customer_support_page_routes",
    "register_hr_manager_page_routes",
]
