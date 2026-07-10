"""Academic Director role page routes."""

from fastapi import APIRouter, Depends

from backend.core.rendering import generate_csrf, render_react_page
from backend.modules.academics.postgres_service import list_academic_admin_rows
from backend.modules.announcements.service import list_announcements
from backend.modules.staff.page import render_role_home
from backend.modules.staff.workspace import academic_director_workspace_cards
from backend.modules.staff.registration import (
    list_active_subjects,
    list_head_of_department_accounts,
)
from backend.modules.teacher_academy.service import (
    list_academy_timetable_events,
    list_teacher_academy_page_context,
)
from backend.core.guards import require_role
from backend.core.performance import PagePerformanceTimer, log_page_performance
from backend.core.session import current_auth_login, current_auth_role


def _safe_academy_timetable_context():
    try:
        academy_lessons = list_academy_timetable_events()
    except Exception as exc:
        return {"academy_lessons": [], "warning": f"Teacher Academy lesson schedule could not be loaded: {exc}"}
    return {"academy_lessons": academy_lessons, "warning": ""}


def _safe_academic_workspace_context(*, include_heavy=True):
    try:
        return {"academic": list_academic_admin_rows(include_heavy=include_heavy), "warning": ""}
    except Exception as exc:
        return {
            "academic": {
                "schools": [],
                "subjects": [],
                "groups": [],
                "enrollments": [],
                "lessons": [],
                "schedules": [],
                "sessions": [],
                "curriculum_programs": [],
                "curriculum_items": [],
                "enrollment_summary": {},
            },
            "warning": f"Academic workspace could not be loaded: {exc}",
        }


def _safe_announcement_context():
    try:
        announcements = list_announcements(include_drafts=True)
    except Exception as exc:
        return {"announcements": [], "warning": f"Announcements could not be loaded: {exc}"}
    return {"announcements": announcements, "warning": ""}


def register_academic_director_page_routes(app):
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

    def _render_academic_workspace(workspace: str, *, title: str, description: str, include_heavy=True):
        timer = PagePerformanceTimer()
        context = _safe_academic_workspace_context(include_heavy=include_heavy)
        academic_context = context.get("academic", {})
        timer.mark("context_build")
        response = render_react_page(
            f"academic-director-{workspace}",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "academic_director",
                "workspace": workspace,
                "adminMode": "academic_director",
                "adminSchool": "all",
                "adminAcademicSchools": academic_context.get("schools", []),
                "adminAcademicSubjects": academic_context.get("subjects", []),
                "adminAcademicGroups": academic_context.get("groups", []),
                "adminAcademicEnrollments": academic_context.get("enrollments", []),
                "adminAcademicLessons": academic_context.get("lessons", []),
                "adminAcademicSchedules": academic_context.get("schedules", []),
                "adminAcademicSessions": academic_context.get("sessions", []),
                "adminAcademicCurriculumPrograms": academic_context.get("curriculum_programs", []),
                "adminAcademicCurriculumItems": academic_context.get("curriculum_items", []),
                "adminAcademicEnrollmentSummary": academic_context.get("enrollment_summary", {}),
                "adminAcademicContextMode": "full" if include_heavy else "summary",
                "warning": context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title=title,
            description=description,
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            f"academic_director_{workspace}",
            timer,
            response=response,
            rows={
                "academic_subjects": academic_context.get("subjects", []),
                "academic_groups": academic_context.get("groups", []),
                "academic_enrollments": academic_context.get("enrollments", []),
                "academic_lessons": academic_context.get("lessons", []),
                "academic_schedules": academic_context.get("schedules", []),
                "academic_sessions": academic_context.get("sessions", []),
            },
        )
        return response

    @router.get("/academic-director/groups", operation_id="academic_director_groups")
    def academic_director_groups():
        return _render_academic_workspace(
            "groups",
            title="Academic Director Groups",
            description="Academic Director group management.",
            include_heavy=True,
        )

    @router.get("/academic-director/subjects", operation_id="academic_director_subjects")
    def academic_director_subjects():
        return _render_academic_workspace(
            "subjects",
            title="Academic Director Subjects",
            description="Academic Director subject and curriculum management.",
            include_heavy=True,
        )

    @router.get("/academic-director/timetable", operation_id="academic_director_timetable")
    def academic_director_timetable():
        return _render_academic_workspace(
            "timetable",
            title="Academic Director Timetable",
            description="Academic Director group timetable workspace.",
            include_heavy=True,
        )

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
            view="profile",
        )

    @router.get("/academic-director/teacher-academy", operation_id="academic_director_teacher_academy")
    def academic_director_teacher_academy():
        timer = PagePerformanceTimer()
        academy_context = list_teacher_academy_page_context()
        timetable_context = _safe_academy_timetable_context()
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
                "adminAcademyLessonEvents": timetable_context.get("academy_lessons", []),
                "warning": timetable_context.get("warning", ""),
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
                "academy_lessons": timetable_context.get("academy_lessons", []),
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

    app.include_router(router)


__all__ = ["register_academic_director_page_routes"]
