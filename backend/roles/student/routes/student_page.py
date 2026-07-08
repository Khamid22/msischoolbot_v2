"""Compatibility wrapper for the moved student page registry."""

from backend.pages.student import register_student_page_routes

__all__ = ["register_student_page_routes"]
