"""Parent portal page — rendered when a parent account logs in."""

from flask import session
from flask_wtf.csrf import generate_csrf

from web.backend.render import render_react_page
from web.backend.admin.services.parent_service import list_parent_children
from web.backend.services.announcements import list_announcements
from web.backend.services.resources import list_resources


def build_render_parent_page():
    def render_parent_page():
        try:
            admin_id = int(session.get("admin_id", 0) or 0)
        except (TypeError, ValueError):
            admin_id = 0

        children = list_parent_children(admin_id) if admin_id else []

        resources = []
        try:
            raw_resources = list_resources()
            resources = [dict(r) for r in raw_resources] if raw_resources else []
        except Exception:
            pass

        announcements = []
        try:
            raw_announcements = list_announcements()
            announcements = raw_announcements if raw_announcements else []
        except Exception:
            pass

        auth_login = str(session.get("auth_login", "")).strip()

        return render_react_page(
            "parent-home",
            {
                "authLogin": auth_login,
                "parentChildren": children,
                "resourcesList": resources,
                "adminAnnouncements": announcements,
                "currentSchool": "all",
                "csrfToken": generate_csrf(),
                "logoutUrl": "/logout",
            },
            title="Parent Portal",
            description="Track your children's academic progress.",
        )

    return render_parent_page


__all__ = ["build_render_parent_page"]
