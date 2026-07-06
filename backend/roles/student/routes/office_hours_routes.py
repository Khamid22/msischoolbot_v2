from backend.utils.response_helpers import jsonify, redirect
from backend.utils.context import request
from backend.utils.session import url_for, current_student_db_id
from backend.render import render_react_page, generate_csrf
from backend.roles.student.services import payload_service
from backend.domains.office_hours import service as oh_service
from backend.domains.students.service import list_enrolled_subject_options
from backend.domains.teachers.service import list_teachers


def register_office_hours_routes(students):
    @students.get("/dashboard/{student_id}/office-hours")
    def student_office_hours(student_id: int):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=False,
            missing_message="We could not retrieve data for this student. Please search again.",
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own office hours.",
        )
        if error_message:
            return render_react_page(
                    "student-not-found",
                    {"message": error_message, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=status_code)

        student = payload.get("student", {})
        if not isinstance(student, dict):
            return render_react_page(
                    "student-not-found",
                    {"message": "Student profile is unavailable.", "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=404)

        subject_name = str(student.get("subject", "")).strip()
        group_name = str(student.get("group", "")).strip()
        school_code = str(student.get("schoolCode", "")).strip() or requested_school

        back_url = url_for(
            "student.dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or group_name,
            school=school_code,
        )

        subjects_options = list_enrolled_subject_options(
            student_id=student_id,
            school_code=school_code,
            fallback_subject_name=subject_name,
        )

        # Get list of teachers for filtering
        teachers_list = list_teachers()

        return render_react_page(
            "student-office-hours",
            {
                "backUrl": back_url,
                "currentStudent": student,
                "subjects": subjects_options,
                "teachers": teachers_list,
                "csrfToken": generate_csrf(),
                "embedMode": request.args.get("embed", "").strip(),
            },
            title="Book Office Hour",
            description="Book an office hour session with a teacher.",
            back_mode="history",
            back_url=back_url,
        )

    @students.get("/api/office-hours/availability")
    def student_list_availability():
        teacher_id = request.args.get("teacher_id")
        subject_id = request.args.get("subject_id")
        starts_at_from = request.args.get("starts_at_from")

        try:
            t_id = int(teacher_id) if teacher_id else None
            s_id = int(subject_id) if subject_id else None
        except ValueError:
            return jsonify({"ok": False, "message": "Invalid query parameters."}, status_code=400)

        # Students only see active availabilities
        availabilities = oh_service.list_availabilities(
            teacher_id=t_id,
            subject_id=s_id,
            status='active',
            starts_at_from=starts_at_from
        )
        return jsonify({"ok": True, "availabilities": availabilities})

    @students.get("/api/office-hours/bookings")
    def student_list_bookings():
        student_row_id = current_student_db_id()
        if not student_row_id:
            return jsonify({"ok": False, "message": "Student session required."}, status_code=401)

        bookings = oh_service.list_bookings(
            student_row_id=student_row_id
        )
        return jsonify({"ok": True, "bookings": bookings})

    @students.post("/api/office-hours/bookings")
    def student_create_booking():
        from backend.roles.admin.routes.request_payload import request_payload
        payload = request_payload()
        student_row_id = current_student_db_id()
        if not student_row_id:
            return jsonify({"ok": False, "message": "Student session required."}, status_code=401)

        try:
            availability_id = int(payload.get("availability_id"))
            student_note = str(payload.get("student_note", ""))
            student_topic_request = str(payload.get("student_topic_request", "") or "").strip()
        except (TypeError, ValueError, KeyError):
            return jsonify({"ok": False, "message": "Missing or invalid payload parameters."}, status_code=400)

        try:
            booking_id = oh_service.create_booking(
                availability_id=availability_id,
                student_row_id=student_row_id,
                student_note=student_note,
                student_topic_request=student_topic_request,
            )
            return jsonify({"ok": True, "booking_id": booking_id})
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=400)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=500)

    @students.patch("/api/office-hours/bookings/{booking_id}")
    def student_cancel_booking(booking_id: int):
        from backend.roles.admin.routes.request_payload import request_payload
        payload = request_payload()
        status = payload.get("status")
        if status != "cancelled":
            return jsonify({"ok": False, "message": "Only 'cancelled' state transitions are allowed."}, status_code=400)
        student_row_id = current_student_db_id()
        if not student_row_id:
            return jsonify({"ok": False, "message": "Student session required."}, status_code=401)

        try:
            oh_service.update_booking_status(
                booking_id,
                'cancelled',
                'Cancelled by student.',
                student_row_id=student_row_id,
            )
            return jsonify({"ok": True})
        except PermissionError as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=403)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=500)
