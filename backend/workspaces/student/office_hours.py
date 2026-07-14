from backend.core.web_responses import redirect
from backend.core.request_context import request
from backend.core.session import url_for, current_student_db_id
from backend.core.rendering import render_react_page, generate_csrf
from backend.modules.people.students import payload as payload_service
from backend.modules.people.students.service import list_enrolled_subject_options
from backend.modules.people.teachers.service import list_teachers


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
