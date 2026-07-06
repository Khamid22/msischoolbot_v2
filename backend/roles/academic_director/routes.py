"""Academic Director role page routes."""

from fastapi import APIRouter, Depends

from backend.render import generate_csrf, render_react_page
from backend.domains.announcements.service import list_announcements
from backend.roles.role_home import render_role_home
from backend.roles.workspace_counts import academic_director_workspace_cards
from backend.roles.academic_director.staff_registration import (
    create_head_of_department_account,
    list_active_subjects,
    list_head_of_department_accounts,
)
from backend.roles.admin.services.academic_service import list_admin_academic_context
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.roles.admin.services.teacher_academy_service import list_teacher_academy_page_context
from backend.utils.context import request
from backend.utils.guards import require_role
from backend.utils.performance import PagePerformanceTimer, log_page_performance
from backend.utils.response_helpers import jsonify
from backend.utils.session import current_auth_login, current_auth_role


def _safe_academic_context():
    try:
        context = list_admin_academic_context()
    except Exception as exc:
        return {"schedules": [], "sessions": [], "warning": f"Academic timetable could not be loaded: {exc}"}
    return {
        "schedules": context.get("schedules", []),
        "sessions": context.get("sessions", []),
        "warning": "",
    }


def _safe_announcement_context():
    try:
        announcements = list_announcements(include_drafts=True)
    except Exception as exc:
        return {"announcements": [], "warning": f"Announcements could not be loaded: {exc}"}
    return {"announcements": announcements, "warning": ""}


def register_academic_director_page_routes(app, *, render_admin_page=None):
    router = APIRouter(dependencies=[Depends(require_role("academic_director"))])

    @router.get("/academic-director", operation_id="academic_director_home")
    @router.get("/academic_director", include_in_schema=False)
    def academic_director_home():
        timer = PagePerformanceTimer()
        cards = academic_director_workspace_cards()
        timer.mark("context_build")
        response = render_role_home(
            "academic-director-home",
            "academic_director",
            title="Academic Director Dashboard",
            description="Groups, teachers, subjects, attendance, and academic progress.",
            cards=cards,
        )
        timer.mark("render")
        log_page_performance(
            "academic_director_home",
            timer,
            response=response,
            rows={"cards": cards},
        )
        return response

    @router.get("/academic-director/timetable", operation_id="academic_director_timetable")
    def academic_director_timetable():
        timer = PagePerformanceTimer()
        academic_context = _safe_academic_context()
        timer.mark("context_build")
        response = render_react_page(
            "academic-director-timetable",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "academic_director",
                "workspace": "timetable",
                "adminAcademicSchedules": academic_context.get("schedules", []),
                "adminAcademicSessions": academic_context.get("sessions", []),
                "warning": academic_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Academic Director Timetable",
            description="Academic timetable workspace.",
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            "academic_director_timetable",
            timer,
            response=response,
            rows={
                "schedules": academic_context.get("schedules", []),
                "sessions": academic_context.get("sessions", []),
            },
        )
        return response

    @router.get("/academic-director/announcements", operation_id="academic_director_announcements")
    def academic_director_announcements():
        timer = PagePerformanceTimer()
        announcement_context = _safe_announcement_context()
        timer.mark("context_build")
        response = render_react_page(
            "academic-director-announcements",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "academic_director",
                "workspace": "announcements",
                "adminAnnouncements": announcement_context.get("announcements", []),
                "warning": announcement_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Academic Director Announcements",
            description="Academic announcements workspace.",
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            "academic_director_announcements",
            timer,
            response=response,
            rows={"announcements": announcement_context.get("announcements", [])},
        )
        return response

    @router.get("/academic-director/profile", operation_id="academic_director_profile")
    def academic_director_profile():
        return render_role_home(
            "academic-director-home",
            "academic_director",
            title="Academic Director Profile",
            description="Academic Director profile and logout.",
            cards=academic_director_workspace_cards(),
        )

    @router.get("/academic-director/teacher-academy", operation_id="academic_director_teacher_academy")
    def academic_director_teacher_academy():
        timer = PagePerformanceTimer()
        academy_context = list_teacher_academy_page_context()
        timer.mark("context_build")
        response = render_react_page(
            "academic-director-academy",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "adminMode": "academic_director",
                "adminSchool": "all",
                "adminTeachers": academy_context["teachers"],
                "adminTeacherAcademy": academy_context["academy_teachers"],
                "adminGroupOptions": academy_context["group_options"],
                "adminAcademicSubjects": academy_context["subjects"],
                "adminAcademicCurriculumPrograms": academy_context["curriculum_programs"],
                "adminAcademicCurriculumItems": academy_context["curriculum_items"],
                "csrfToken": generate_csrf(),
            },
            title="Academic Director Teacher Academy",
            description="Academic Director Teacher Academy management.",
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            "academic_director_teacher_academy",
            timer,
            response=response,
            rows={
                "teachers": academy_context["teachers"],
                "academy_teachers": academy_context["academy_teachers"],
                "group_options": academy_context["group_options"],
                "subjects": academy_context["subjects"],
                "curriculum_programs": academy_context["curriculum_programs"],
                "curriculum_items": academy_context["curriculum_items"],
            },
        )
        return response

    @router.get("/academic-director/head-of-departments", operation_id="academic_director_head_of_departments")
    def academic_director_head_of_departments():
        timer = PagePerformanceTimer()
        hod_context = list_head_of_department_accounts()
        timer.mark("context_build")
        response = render_react_page(
            "academic-director-head-of-departments",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "headOfDepartments": hod_context.get("items", []),
                "subjectOptions": list_active_subjects(),
                "warning": hod_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Academic Director Head of Departments",
            description="Manage subject department heads and Teacher Academy access.",
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            "academic_director_head_of_departments",
            timer,
            response=response,
            rows={"head_of_departments": hod_context.get("items", [])},
        )
        return response

    @router.post("/academic-director/api/head-of-departments", operation_id="academic_director_create_hod")
    def academic_director_create_hod():
        created, error_message, credentials = create_head_of_department_account(
            display_name=request.form.get("hod_display_name", ""),
            subject_id=request.form.get("hod_subject_id", ""),
            created_by=current_auth_login() or "Academic Director",
        )
        if not created:
            return jsonify(
                {"ok": False, "message": error_message or "Unable to create Head of Department."},
                status_code=400,
            )
        invalidate_admin_page_context_cache()
        return jsonify(
            {
                "ok": True,
                "message": "Head of Department account created.",
                "credentials": {
                    "role": "head_of_department",
                    "login": credentials.get("login", ""),
                    "temporary_password": credentials.get("temporary_password", ""),
                    "display_name": credentials.get("display_name", ""),
                    "subject_name": credentials.get("subject_name", ""),
                },
                "headOfDepartment": {
                    "login": credentials.get("login", ""),
                    "display_name": credentials.get("display_name", ""),
                    "role": "head_of_department",
                    "status": "active",
                    "subject_name": credentials.get("subject_name", ""),
                },
            }
        )

    app.include_router(router)


__all__ = ["register_academic_director_page_routes"]
