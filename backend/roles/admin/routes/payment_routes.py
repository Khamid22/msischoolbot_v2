from backend.utils.response_helpers import jsonify
from backend.utils.context import session

from backend.roles.admin.routes.request_payload import request_payload
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.domains.payments.service import (
    create_student_payment,
    delete_student_payment,
    set_student_payment_paid,
    list_student_payments,
    summarize_payment_records,
)


def _current_admin_id():
    try:
        parsed = int(session.get("admin_id", 0))
    except (TypeError, ValueError):
        parsed = 0
    return parsed if parsed > 0 else 0


def register_admin_payment_routes(router):
    @router.get("/admin/api/students/<int:student_row_id>/payments")
    def admin_list_student_payments(student_row_id):
        payments = list_student_payments(student_row_id)
        return jsonify(
            {
                "ok": True,
                "payments": payments,
                "summary": summarize_payment_records(payments),
            }
        )

    @router.post("/admin/api/students/<int:student_row_id>/payments")
    def admin_create_student_payment(student_row_id):
        payload = request_payload()
        try:
            result = create_student_payment(
                student_row_id,
                payload,
                created_by_admin_id=_current_admin_id(),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        invalidate_admin_page_context_cache()
        return jsonify(
            {
                "ok": True,
                **result,
                "summary": summarize_payment_records(result["payments"]),
            }
        )

    @router.patch("/admin/api/student-payments/<int:payment_id>")
    def admin_mark_student_payment(payment_id):
        payload = request_payload()
        paid = bool(payload.get("paid", True))
        paid_at = payload.get("paid_at")
        try:
            result = set_student_payment_paid(payment_id, paid=paid, paid_at=paid_at)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        if result is None:
            return jsonify({"ok": False, "message": "Payment record was not found."}), 404

        invalidate_admin_page_context_cache()
        return jsonify(
            {
                "ok": True,
                **result,
                "summary": summarize_payment_records(result["payments"]),
            }
        )

    @router.delete("/admin/api/student-payments/<int:payment_id>")
    def admin_delete_student_payment(payment_id):
        try:
            result = delete_student_payment(payment_id)
        except (TypeError, ValueError) as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        if result is None:
            return jsonify({"ok": False, "message": "Payment record was not found."}), 404

        invalidate_admin_page_context_cache()
        return jsonify(
            {
                "ok": True,
                **result,
                "summary": summarize_payment_records(result["payments"]),
            }
        )


__all__ = ["register_admin_payment_routes"]
