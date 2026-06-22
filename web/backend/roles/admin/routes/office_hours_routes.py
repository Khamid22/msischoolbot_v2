from web.backend.utils.response_helpers import jsonify
from web.backend.utils.context import request
from web.backend.roles.admin.routes.request_payload import request_payload
from web.backend.domains.office_hours import service as oh_service


def register_office_hours_admin_routes(router):
    @router.get("/admin/api/office-hours/availability")
    def admin_list_availability():
        teacher_id = request.args.get("teacher_id")
        subject_id = request.args.get("subject_id")
        status = request.args.get("status")
        starts_at_from = request.args.get("starts_at_from")

        try:
            t_id = int(teacher_id) if teacher_id else None
            s_id = int(subject_id) if subject_id else None
        except ValueError:
            return jsonify({"ok": False, "message": "Invalid query parameters."}), 400

        availabilities = oh_service.list_availabilities(
            teacher_id=t_id,
            subject_id=s_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return jsonify({"ok": True, "availabilities": availabilities})

    @router.post("/admin/api/office-hours/availability")
    def admin_create_availability():
        payload = request_payload()
        try:
            teacher_id = int(payload.get("teacher_id"))
            starts_at = str(payload.get("starts_at"))
            ends_at = str(payload.get("ends_at"))
            slot_minutes = int(payload.get("slot_minutes", 30))
            room = str(payload.get("room", ""))
            capacity = int(payload.get("capacity", 1))
            subject_id = int(payload.get("subject_id")) if payload.get("subject_id") else None
            planned_topic = str(payload.get("planned_topic", "") or "").strip()
        except (TypeError, ValueError, KeyError) as exc:
            return jsonify({"ok": False, "message": "Missing or invalid payload parameters."}), 400

        try:
            availability_id = oh_service.create_availability(
                teacher_id=teacher_id,
                subject_id=subject_id,
                starts_at=starts_at,
                ends_at=ends_at,
                slot_minutes=slot_minutes,
                room=room,
                capacity=capacity,
                planned_topic=planned_topic,
            )
            return jsonify({"ok": True, "availability_id": availability_id})
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @router.patch("/admin/api/office-hours/availability/<int:availability_id>")
    def admin_cancel_availability(availability_id):
        payload = request_payload()
        status = payload.get("status")
        if status != "cancelled":
            return jsonify({"ok": False, "message": "Only 'cancelled' state transitions are allowed."}), 400

        try:
            oh_service.cancel_availability(availability_id)
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @router.get("/admin/api/office-hours/bookings")
    def admin_list_bookings():
        availability_id = request.args.get("availability_id")
        teacher_id = request.args.get("teacher_id")
        student_row_id = request.args.get("student_row_id")
        subject_id = request.args.get("subject_id")
        status = request.args.get("status")
        starts_at_from = request.args.get("starts_at_from")

        try:
            a_id = int(availability_id) if availability_id else None
            t_id = int(teacher_id) if teacher_id else None
            s_row_id = int(student_row_id) if student_row_id else None
            s_id = int(subject_id) if subject_id else None
        except ValueError:
            return jsonify({"ok": False, "message": "Invalid query parameters."}), 400

        bookings = oh_service.list_bookings(
            availability_id=a_id,
            teacher_id=t_id,
            student_row_id=s_row_id,
            subject_id=s_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return jsonify({"ok": True, "bookings": bookings})

    @router.patch("/admin/api/office-hours/bookings/<int:booking_id>")
    def admin_update_booking_status(booking_id):
        payload = request_payload()
        status = payload.get("status")
        teacher_note = payload.get("teacher_note")

        if not status:
            return jsonify({"ok": False, "message": "Missing status parameter."}), 400

        try:
            oh_service.update_booking_status(booking_id, status, teacher_note)
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500
