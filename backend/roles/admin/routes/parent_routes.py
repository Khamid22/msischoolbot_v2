from backend.utils.response_helpers import jsonify
from backend.utils.context import session

from backend.roles.admin.routes.request_payload import request_payload
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.roles.admin.services.parent_service import (
    assign_parent_child,
    delete_parent_account,
    remove_parent_child,
)


def _current_parent_admin_id():
    try:
        parsed = int(session.get("admin_id", 0))
    except (TypeError, ValueError):
        parsed = 0
    return parsed if parsed > 0 else 0


def register_admin_parent_routes(router):
    @router.post("/admin/parents/{parent_admin_id}/children")
    def admin_assign_selected_parent_child(parent_admin_id: int):
        payload = request_payload()
        student_row_id = payload.get("student_row_id") or payload.get("student_id")
        try:
            child = assign_parent_child(parent_admin_id, student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "child": child})

    @router.delete("/admin/parents/{parent_admin_id}/children/{student_row_id}")
    def admin_remove_selected_parent_child(parent_admin_id: int, student_row_id: int):
        try:
            removed = remove_parent_child(parent_admin_id, student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        if not removed:
            return jsonify({"ok": False, "message": "Child assignment was not found."}, status_code=404)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True})

    @router.delete("/admin/parents/{parent_admin_id}")
    def admin_delete_parent_account(parent_admin_id: int):
        try:
            deleted = delete_parent_account(parent_admin_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        if not deleted:
            return jsonify({"ok": False, "message": "Parent account was not found."}, status_code=404)

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
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True, "child": child})

    @router.delete("/admin/parent-children/{student_row_id}")
    def admin_remove_parent_child(student_row_id: int):
        try:
            removed = remove_parent_child(_current_parent_admin_id(), student_row_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)

        if not removed:
            return jsonify({"ok": False, "message": "Child assignment was not found."}, status_code=404)

        invalidate_admin_page_context_cache()
        return jsonify({"ok": True})


__all__ = ["register_admin_parent_routes"]
