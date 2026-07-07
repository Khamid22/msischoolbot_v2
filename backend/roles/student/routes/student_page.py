from fastapi import APIRouter, Depends, Request


from backend.utils.context import session
from backend.utils.session import url_for
from backend.render import generate_csrf

from backend.render import render_react_page

from backend.domains.identity.routes import register_user_auth_routes
from backend.roles.parent.routes import build_render_parent_page
from backend.roles.student.routes.dashboard import register_dashboard_routes
from backend.roles.student.routes.rating_board import register_rating_board_routes
from backend.roles.student.routes.chat_page import register_chat_page_routes
from backend.roles.student.routes.resources import register_resources_routes
from backend.roles.student.routes.office_hours_routes import register_office_hours_routes
from backend.domains.students.service import (
    get_student_db_id_by_enrollment_id,
    record_student_activity,
)
from backend.roles.student.services.page_service import build_student_panel_context
from backend.utils.session import (
    current_auth_login,
    current_auth_role,
    current_student_db_id,
    current_student_enrollment_id,
    current_student_school_code,
)
from backend.roles.student.routes.students import register_student_routes
from backend.utils.performance import PagePerformanceTimer, log_page_performance


def register_student_page_routes(app, *, render_admin_page):
    def should_force_refresh():
        return False

    def render_login_page(auth_error="", auth_login_input=""):
        return render_react_page(
            "login",
            {
                "authError": auth_error,
                "authLoginInput": auth_login_input,
                "submitUrl": url_for("student.login"),
                "csrfToken": generate_csrf(),
            },
            title="MSI School Portal",
            description="Login to continue.",
        )

    def render_student_panel(form_data, panel_error=""):
        timer = PagePerformanceTimer()
        context = build_student_panel_context(
            form_data=form_data,
            student_school_code=current_student_school_code(),
            force_refresh=should_force_refresh(),
        )
        timer.mark("context_build")

        response = render_react_page(
            "student-home",
            {
                "subjects": context["subjects"],
                "groupsBySubject": context["groups_by_subject"],
                "studentsBySubjectGroup": context["students_by_subject_group"],
                "formData": context["form_data"],
                "error": panel_error or context["load_error"] or "",
                "authLogin": current_auth_login(),
                "csrfToken": generate_csrf(),
                "logoutUrl": url_for("student.logout"),
                "searchUrl": url_for("student.search_student_form"),
            },
            title="MSI School Portal",
            description="Select stream, group, and student.",
        )
        timer.mark("render")
        log_page_performance(
            "student_home",
            timer,
            response=response,
            rows={
                "subjects": context["subjects"],
                "groups_by_subject": context["groups_by_subject"],
                "students_by_subject_group": context["students_by_subject_group"],
            },
        )
        return response

    def track_student_activity(request_obj: Request):
        if current_auth_role() != "student":
            return
        student_db_id = current_student_db_id()
        if student_db_id is not None:
            record_student_activity(student_db_id)

    students = APIRouter(dependencies=[Depends(track_student_activity)])

    register_user_auth_routes(
        students,
        render_login_page=render_login_page,
        render_admin_page=render_admin_page,
        render_parent_page=build_render_parent_page(),
    )
    register_student_routes(students, render_student_panel=render_student_panel)
    register_dashboard_routes(students)
    register_rating_board_routes(students)
    register_resources_routes(students)
    register_chat_page_routes(students)
    register_office_hours_routes(students)
    app.include_router(students)
