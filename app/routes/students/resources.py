from flask import render_template, request, url_for

from app.routes.students.services import payload_service, resources_service


def register_resources_routes(
    students,
    *,
    load_dashboard_payload,
):
    def _should_force_refresh():
        return False

    @students.get("/dashboard/<int:student_id>/resources")
    def student_resources(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()
        force_refresh = _should_force_refresh()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=force_refresh,
            load_dashboard_payload=load_dashboard_payload,
            missing_message=(
                "We could not retrieve data for this student. Please search again."
            ),
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own resources.",
        )
        if error_message:
            return (
                render_template(
                    "student/not_found.html",
                    message=error_message,
                ),
                status_code,
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

        grouped_resources = resources_service.list_resources_grouped_by_type(subject_name)
        back_url = url_for(
            "student.dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or group_name,
            school=school_code,
        )

        return render_template(
            "student/resources.html",
            current_student=student,
            student=student,
            student_id=student_id,
            subject_name=subject_name,
            grouped_resources=grouped_resources,
            back_url=back_url,
        )
