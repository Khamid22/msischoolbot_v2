from web.backend.utils.response_helpers import jsonify
from web.backend.utils.context import session

from web.backend.roles.admin.routes.request_payload import request_payload
from web.backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from web.backend.roles.admin.services.parent_service import (
    assign_parent_child,
    create_parent_account,
    remove_parent_child,
    update_parent_profile,
)


_PARENT_PROFILE_FIELDS = ("display_name", "phone", "email", "telegram_username", "notes")


def _parent_profile_from_payload(payload):
    return {field: str(payload.get(field) or "").strip() for field in _PARENT_PROFILE_FIELDS}


def _current_parent_admin_id():
    try:
        parsed = int(session.get("admin_id", 0))
    except (TypeError, ValueError):
        parsed = 0
    return parsed if parsed > 0 else 0


def register_admin_parent_routes(router):
    @router.post("/admin/parents")
    def admin_create_parent_account():
        payload = request_payload()
        try:
            parent = create_parent_account(
                payload.get("login"),
                payload.get("password"),
                profile=_parent_profile_from_payload(payload),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "parent": parent})

    @router.patch("/admin/parents/<int:parent_admin_id>")
    def admin_update_parent_profile(parent_admin_id):
        payload = request_payload()
        try:
            parent = update_parent_profile(
                parent_admin_id,
                _parent_profile_from_payload(payload),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "parent": parent})

    @router.post("/admin/parents/<int:parent_admin_id>/children")
    def admin_assign_selected_parent_child(parent_admin_id):
        payload = request_payload()
        student_row_id = payload.get("student_row_id") or payload.get("student_id")
        try:
            child = assign_parent_child(parent_admin_id, student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "child": child})

    @router.delete("/admin/parents/<int:parent_admin_id>/children/<int:student_row_id>")
    def admin_remove_selected_parent_child(parent_admin_id, student_row_id):
        try:
            removed = remove_parent_child(parent_admin_id, student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        if not removed:
            return jsonify({"ok": False, "message": "Child assignment was not found."}), 404

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True})

    @router.post("/admin/parent-children")
    def admin_assign_parent_child():
        payload = request_payload()
        parent_admin_id = payload.get("parent_admin_id") or _current_parent_admin_id()
        student_row_id = payload.get("student_row_id") or payload.get("student_id")
        try:
            child = assign_parent_child(parent_admin_id, student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "child": child})

    @router.delete("/admin/parent-children/<int:student_row_id>")
    def admin_remove_parent_child(student_row_id):
        try:
            removed = remove_parent_child(_current_parent_admin_id(), student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        if not removed:
            return jsonify({"ok": False, "message": "Child assignment was not found."}), 404

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True})


__all__ = ["register_admin_parent_routes"]
