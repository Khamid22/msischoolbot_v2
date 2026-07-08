"""Compatibility wrapper for moved parent page and invite routes."""

from backend.pages.parent import (
    build_render_parent_page,
    register_parent_invite_routes,
    register_parent_page_routes,
)

__all__ = [
    "build_render_parent_page",
    "register_parent_invite_routes",
    "register_parent_page_routes",
]
