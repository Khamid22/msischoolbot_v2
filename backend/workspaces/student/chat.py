from backend.core.web.request_context import request
from backend.modules.identity.session import url_for

from backend.core.web.rendering import render_react_page
from backend.modules.people.students import payload as payload_service
from backend.modules.identity.session import current_auth_login


def register_chat_page_routes(students):

    @students.get("/dashboard/{student_id}/chat")
    def chat_room(student_id: int):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()
        requested_school = request.args.get("school", "").strip()

        payload, _dataset, error_message, status_code = payload_service.load_student_payload_for_view(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
            requested_school=requested_school,
            force_refresh=False,
            missing_message="We could not retrieve data for this student.",
            session_invalid_message="Student session is invalid. Please login again.",
            forbidden_message="Access denied: you can open only your own chat.",
        )

        if error_message:
            return render_react_page(
                    "student-not-found",
                    {"message": error_message, "returnUrl": url_for("student.home")},
                    title="Student Not Found", status_code=status_code)

        payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
        current_subject = str(payload_student.get("subject", "")).strip()
        current_group = str(payload_student.get("group", "")).strip()
        school_code = str(payload_student.get("schoolCode", "")).strip() or requested_school
        student_login = current_auth_login()

        back_url = url_for(
            "student.dashboard",
            student_id=student_id,
            subject=requested_subject or current_subject,
            group=requested_group or current_group,
            school=school_code,
        )

        available_rooms = [
            {"key": "global", "label": "Global", "icon": "globe"},
        ]
        if current_subject:
            available_rooms.append({
                "key": f"subject:{current_subject}",
                "label": current_subject,
                "icon": "layers",
            })
        if current_group:
            available_rooms.append({
                "key": f"group:{current_group}",
                "label": current_group,
                "icon": "users",
            })

        return render_react_page(
            "student-chat",
            {
                "backUrl": back_url,
                "currentStudent": {
                    "fullName": str(payload_student.get("fullName", "")).strip(),
                    "studentLogin": student_login,
                    "subject": current_subject,
                    "group": current_group,
                },
                "availableRooms": available_rooms,
            },
            title="Chat Room",
            description="Student chat room — global, subject, and group channels.",
            back_mode="history",
            back_url=back_url,
        )
