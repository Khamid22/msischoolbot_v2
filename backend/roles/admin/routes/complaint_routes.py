from backend.utils.response_helpers import jsonify
from backend.utils.context import request
from backend.utils.session import current_admin_role, current_auth_login

from backend.roles.admin.routes.request_payload import request_payload
from backend.domains.complaints.service import (
    add_complaint_reply,
    create_complaint,
    get_complaint,
    list_complaints,
    update_complaint,
)
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache


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
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "complaint": complaint})

    @router.patch("/admin/api/complaints/{complaint_id}")
    def admin_update_complaint(complaint_id: int):
        payload = request_payload()
        try:
            complaint = update_complaint(complaint_id, payload)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        if complaint is None:
            return jsonify({"ok": False, "message": "Complaint was not found."}, status_code=404)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "complaint": complaint})

    @router.get("/admin/api/complaints/{complaint_id}")
    def admin_get_complaint(complaint_id: int):
        complaint = get_complaint(complaint_id)
        if complaint is None:
            return jsonify({"ok": False, "message": "Complaint was not found."}, status_code=404)
        return jsonify({"ok": True, "complaint": complaint})

    @router.post("/admin/api/complaints/{complaint_id}/replies")
    def admin_reply_complaint(complaint_id: int):
        payload = request_payload()
        author_role = current_admin_role() or "admin"
        author_login = current_auth_login()
        try:
            complaint = add_complaint_reply(
                complaint_id,
                payload,
                author_role=author_role,
                author_login=author_login,
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        if complaint is None:
            return jsonify({"ok": False, "message": "Complaint was not found."}, status_code=404)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "complaint": complaint})


__all__ = ["register_admin_complaint_routes"]
