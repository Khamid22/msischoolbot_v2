from flask import render_template, request, session, url_for

try:
    from ...services.resources_service import list_resources_grouped_by_type
except ImportError:
    from services.resources_service import list_resources_grouped_by_type


def register_resources_routes(
    app,
    *,
    load_dashboard_payload,
):
    def _normalize_text(value):
        return " ".join(str(value or "").strip().casefold().split())

    def _current_auth_role():
        return str(session.get("auth_role", "")).strip().lower()

    def _current_student_sheet_id():
        raw_value = session.get("student_sheet_id")
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _current_student_full_name():
        return str(session.get("student_full_name", "")).strip()

    def _should_force_refresh():
        return False

    def _is_student_owner_of_payload(student_id, payload):
        own_full_name = _normalize_text(_current_student_full_name())
        if own_full_name:
            payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
            payload_full_name = _normalize_text(payload_student.get("fullName", ""))
            return bool(payload_full_name) and payload_full_name == own_full_name

        own_sheet_student_id = _current_student_sheet_id()
        return own_sheet_student_id is not None and int(student_id) == own_sheet_student_id

    @app.get("/dashboard/<int:student_id>/resources")
    def student_resources(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()
        force_refresh = _should_force_refresh()

        payload, _dataset, payload_error = load_dashboard_payload(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=force_refresh,
        )
        if payload_error:
            return (
                render_template(
                    "student/not_found.html",
                    message=payload_error,
                ),
                503,
            )

        if not payload:
            return (
                render_template(
                    "student/not_found.html",
                    message="We could not retrieve data for this student. Please search again.",
                ),
                404,
            )

        if _current_auth_role() == "student" and not _is_student_owner_of_payload(
            student_id, payload
        ):
            if not _current_student_sheet_id() and not _current_student_full_name():
                return (
                    render_template(
                        "student/not_found.html",
                        message="Student session is invalid. Please login again.",
                    ),
                    401,
                )
            return (
                render_template(
                    "student/not_found.html",
                    message="Access denied: you can open only your own resources.",
                ),
                403,
            )

        student = payload.get("student", {})
        if not isinstance(student, dict):
            return (
                render_template(
                    "student/not_found.html",
                    message="Student profile is unavailable.",
                ),
                404,
            )

        subject_name = str(student.get("subject", "")).strip()
        group_name = str(student.get("group", "")).strip()
        school_code = str(student.get("schoolCode", "")).strip() or requested_school

        grouped_resources = list_resources_grouped_by_type(subject_name)
        back_url = url_for(
            "dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or group_name,
            school=school_code,
        )

        return render_template(
            "student/resources.html",
            current_student=student,
            student_id=student_id,
            subject_name=subject_name,
            grouped_resources=grouped_resources,
            back_url=back_url,
        )


__all__ = ["register_resources_routes"]
