from backend.core.request_context import request
from backend.core.session import url_for

from backend.core.rendering import render_react_page

from backend.modules.resources import service as resources_service
from backend.modules.students import payload as payload_service


def register_resources_routes(students):
    def _should_force_refresh():
        return False

    @students.get("/dashboard/{student_id}/resources")
    def student_resources(student_id: int):
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
            missing_message=(
                "We could not retrieve data for this student. Please search again."
            ),
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own resources.",
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

        grouped_resources = resources_service.list_resources_grouped_by_type_old_to_new(
            subject_name
        )
        back_url = url_for(
            "student.dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or group_name,
            school=school_code,
        )

        return render_react_page(
            "student-resources",
            {
                "backUrl": back_url,
                "subjectName": subject_name,
                "currentStudent": student,
                "groupedResources": grouped_resources,
                "embedMode": request.args.get("embed", "").strip(),
            },
            title="Subject Resources",
            description="Shared learning resources for the selected subject.",
            back_mode="history",
            back_url=back_url,
        )
