from flask import jsonify, request

from web.backend.roles.admin.routes.request_payload import request_payload
from web.backend.domains.complaints.service import (
    create_complaint,
    list_complaints,
    update_complaint,
)
from web.backend.roles.admin.services.page_service import invalidate_admin_page_context_cache


def register_admin_complaint_routes(router):
    @router.get("/admin/api/complaints")
    def admin_list_complaints():
        parent_admin_id = request.args.get("parent_admin_id", 0)
        try:
            complaints = list_complaints(parent_admin_id)
        except (TypeError, ValueError):
            complaints = list_complaints(0)
        return jsonify({"ok": True, "complaints": complaints})

    @router.post("/admin/api/complaints")
    def admin_create_complaint():
        payload = request_payload()
        parent_admin_id = payload.get("parent_admin_id")
        student_row_id = payload.get("student_row_id") or payload.get("student_id")
        try:
            complaint = create_complaint(parent_admin_id, student_row_id, payload)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "complaint": complaint})

    @router.patch("/admin/api/complaints/<int:complaint_id>")
    def admin_update_complaint(complaint_id):
        payload = request_payload()
        try:
            complaint = update_complaint(complaint_id, payload)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        if complaint is None:
            return jsonify({"ok": False, "message": "Complaint was not found."}), 404

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "complaint": complaint})


__all__ = ["register_admin_complaint_routes"]
