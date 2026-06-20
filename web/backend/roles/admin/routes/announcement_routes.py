from flask import jsonify

from web.backend.roles.admin.routes.request_payload import request_payload
from web.backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from web.backend.utils.session import current_auth_login
from web.backend.domains.announcements.service import (
    create_announcement,
    delete_announcement,
    list_announcements,
    update_announcement,
)


def register_announcement_admin_routes(admin_blueprint):
    @admin_blueprint.get("/admin/api/announcements")
    def admin_list_announcements():
        return jsonify({"ok": True, "announcements": list_announcements()})

    @admin_blueprint.post("/admin/api/announcements")
    def admin_create_announcement():
        payload = request_payload()
        try:
            item = create_announcement(
                title=payload.get("title", ""),
                body=payload.get("body", ""),
                audience=payload.get("audience", "all"),
                priority=payload.get("priority", "info"),
                status=payload.get("status", "draft"),
                pinned=bool(payload.get("pinned")),
                author=current_auth_login() or "Admin",
                scheduled_at=payload.get("scheduled_at", ""),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "announcement": item})

    @admin_blueprint.patch("/admin/api/announcements/<int:announcement_id>")
    def admin_update_announcement(announcement_id):
        payload = request_payload()
        try:
            item = update_announcement(
                announcement_id,
                title=payload.get("title"),
                body=payload.get("body"),
                audience=payload.get("audience"),
                priority=payload.get("priority"),
                status=payload.get("status"),
                pinned=payload.get("pinned"),
                scheduled_at=payload.get("scheduled_at"),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "announcement": item})

    @admin_blueprint.delete("/admin/api/announcements/<int:announcement_id>")
    def admin_delete_announcement(announcement_id):
        deleted = delete_announcement(announcement_id)
        if not deleted:
            return jsonify({"ok": False, "message": "Announcement not found."}), 404
        invalidate_admin_page_context_cache()
        return jsonify({"ok": True})
