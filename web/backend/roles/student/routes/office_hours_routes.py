from web.backend.utils.response_helpers import jsonify, redirect
from web.backend.utils.context import request
from web.backend.utils.session import url_for, current_student_db_id
from web.backend.render import render_react_page, generate_csrf
from web.backend.roles.student.services import payload_service
from web.backend.domains.office_hours import service as oh_service


def _list_enrolled_subject_options(student_id, school_code, fallback_subject_name):
    from shared.db import connect_auth_db

    subject_name = str(fallback_subject_name or "").strip()
    fallback = [{"id": 0, "name": subject_name}] if subject_name else []
    school_code = str(school_code or "").strip()

    try:
        with connect_auth_db() as conn:
            current = conn.execute(
                """
                SELECT
                    st.id AS internal_student_id,
                    st.legacy_student_row_id,
                    st.full_name,
                    sch.school_key
                FROM msi_v2.students st
                LEFT JOIN msi_v2.schools sch ON sch.id = st.school_id
                LEFT JOIN msi_v2.group_students gs ON gs.student_id = st.id
                WHERE COALESCE(gs.legacy_public_dashboard_id, st.legacy_public_dashboard_id) = %s
                  AND (%s = '' OR lower(sch.school_key) = lower(%s))
                LIMIT 1
                """,
                (student_id, school_code, school_code),
            ).fetchone()
            if not current:
                return fallback

            internal_student_id = current.get("internal_student_id")
            rows = conn.execute(
                """
                SELECT DISTINCT subj.id, subj.subject_name AS name
                FROM msi_v2.group_students gs
                JOIN msi_v2.groups g ON g.id = gs.group_id
                JOIN msi_v2.subject_programs sp ON sp.id = g.program_id
                JOIN msi_v2.subjects subj ON subj.id = sp.subject_id
                WHERE gs.student_id = %s
                  AND gs.enrollment_status = 'active'
                  AND subj.status = 'active'
                ORDER BY subj.subject_name
                """,
                (internal_student_id,),
            ).fetchall()
    except Exception:
        return fallback

    subjects = [
        {"id": int(row["id"]), "name": str(row["name"] or "").strip()}
        for row in rows
        if row.get("id") and str(row.get("name") or "").strip()
    ]
    return subjects or fallback


def register_office_hours_routes(
    students,
    *,
    load_dashboard_payload,
):
    @students.get("/dashboard/<int:student_id>/office-hours")
    def student_office_hours(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=False,
            load_dashboard_payload=load_dashboard_payload,
            missing_message="We could not retrieve data for this student. Please search again.",
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own office hours.",
        )
        if error_message:
            return (
                render_react_page(
                    "student-not-found",
                    {"message": error_message, "returnUrl": url_for("student.home")},
                    title="Student Not Found",
                ),
                status_code,
            )

        student = payload.get("student", {})
        if not isinstance(student, dict):
            return (
                render_react_page(
                    "student-not-found",
                    {"message": "Student profile is unavailable.", "returnUrl": url_for("student.home")},
                    title="Student Not Found",
                ),
                404,
            )

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

        subjects_options = _list_enrolled_subject_options(
            student_id=student_id,
            school_code=school_code,
            fallback_subject_name=subject_name,
        )

        # Get list of teachers for filtering
        from shared.identity.account_service import list_teachers
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
            return jsonify({"ok": False, "message": "Invalid query parameters."}), 400

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
            return jsonify({"ok": False, "message": "Student session required."}), 401

        bookings = oh_service.list_bookings(
            student_row_id=student_row_id
        )
        return jsonify({"ok": True, "bookings": bookings})

    @students.post("/api/office-hours/bookings")
    def student_create_booking():
        from web.backend.roles.admin.routes.request_payload import request_payload
        payload = request_payload()
        student_row_id = current_student_db_id()
        if not student_row_id:
            return jsonify({"ok": False, "message": "Student session required."}), 401

        try:
            availability_id = int(payload.get("availability_id"))
            student_note = str(payload.get("student_note", ""))
            student_topic_request = str(payload.get("student_topic_request", "") or "").strip()
        except (TypeError, ValueError, KeyError):
            return jsonify({"ok": False, "message": "Missing or invalid payload parameters."}), 400

        try:
            booking_id = oh_service.create_booking(
                availability_id=availability_id,
                student_row_id=student_row_id,
                student_note=student_note,
                student_topic_request=student_topic_request,
            )
            return jsonify({"ok": True, "booking_id": booking_id})
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @students.patch("/api/office-hours/bookings/<int:booking_id>")
    def student_cancel_booking(booking_id):
        from web.backend.roles.admin.routes.request_payload import request_payload
        payload = request_payload()
        status = payload.get("status")
        if status != "cancelled":
            return jsonify({"ok": False, "message": "Only 'cancelled' state transitions are allowed."}), 400
        student_row_id = current_student_db_id()
        if not student_row_id:
            return jsonify({"ok": False, "message": "Student session required."}), 401

        try:
            oh_service.update_booking_status(
                booking_id,
                'cancelled',
                'Cancelled by student.',
                student_row_id=student_row_id,
            )
            return jsonify({"ok": True})
        except PermissionError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 403
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500
