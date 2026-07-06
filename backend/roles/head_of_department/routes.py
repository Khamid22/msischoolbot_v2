"""Head of Department workspace routes."""

from fastapi import APIRouter, Depends

from backend.domains.announcements.service import list_announcements
from backend.render import generate_csrf, render_react_page
from backend.roles.admin.services.academic_service import list_admin_academic_context
from backend.domains.teacher_academy.service import (
    list_academy_timetable_events,
    list_teacher_academy_page_context,
)
from backend.roles.head_of_department.academy_scope import (
    current_hod_subject_ids,
    can_current_user_manage_academy_assignment,
    can_current_user_manage_academy_teacher,
    filter_rows_by_subject_scope,
)
from backend.roles.head_of_department.workspace_cards import head_of_department_workspace_cards
from backend.roles.common.teacher_academy_api import (
    academy_error,
    add_assessment_response,
    update_assignment_response,
    update_status_response,
)
from backend.roles.role_home import render_role_home
from backend.utils.guards import require_role
from backend.utils.session import current_auth_login, current_auth_role


def _to_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _filter_subject_rows(rows, subject_ids):
    scoped_ids = set(subject_ids or [])
    if not scoped_ids:
        return []
    return [
        row for row in rows
        if _to_int(row.get("subject_id") or row.get("id") or row.get("subjectId")) in scoped_ids
    ]


def _head_of_department_academy_context():
    context = list_teacher_academy_page_context()
    subject_ids = current_hod_subject_ids()
    context["academy_teachers"] = filter_rows_by_subject_scope(
        context.get("academy_teachers") or [],
        subject_ids,
    )
    context["subjects"] = _filter_subject_rows(context.get("subjects") or [], subject_ids)
    context["curriculum_programs"] = _filter_subject_rows(
        context.get("curriculum_programs") or [],
        subject_ids,
    )
    program_ids = {
        _to_int(row.get("id"))
        for row in context.get("curriculum_programs") or []
        if _to_int(row.get("id"))
    }
    context["curriculum_items"] = [
        row for row in context.get("curriculum_items") or []
        if _to_int(row.get("program_id") or row.get("programId")) in program_ids
    ]
    return context


def _head_of_department_timetable_context():
    try:
        context = list_admin_academic_context()
        subject_ids = current_hod_subject_ids()
        academy_lessons = list_academy_timetable_events(subject_ids)
    except Exception as exc:
        return {"schedules": [], "sessions": [], "academy_lessons": [], "warning": f"Subject timetable could not be loaded: {exc}"}
    return {
        "schedules": filter_rows_by_subject_scope(context.get("schedules") or [], subject_ids),
        "sessions": filter_rows_by_subject_scope(context.get("sessions") or [], subject_ids),
        "academy_lessons": academy_lessons,
        "warning": "",
    }


def _head_of_department_announcement_context():
    try:
        announcements = list_announcements(include_drafts=True)
    except Exception as exc:
        return {"announcements": [], "warning": f"Announcements could not be loaded: {exc}"}
    return {"announcements": announcements, "warning": ""}


def register_head_of_department_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("head_of_department"))])

    @router.get("/head-of-department", operation_id="head_of_department_home")
    def head_of_department_home():
        return render_role_home(
            "head-of-department-home",
            "head_of_department",
            title="Head of Department Dashboard",
            description="Subject-scoped Teacher Academy management, teacher profiles, and journeys.",
            cards=head_of_department_workspace_cards(),
        )

    @router.get("/head-of-department/timetable", operation_id="head_of_department_timetable")
    def head_of_department_timetable():
        timetable_context = _head_of_department_timetable_context()
        return render_react_page(
            "head-of-department-timetable",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "head_of_department",
                "workspace": "timetable",
                "adminAcademicSchedules": timetable_context.get("schedules", []),
                "adminAcademicSessions": timetable_context.get("sessions", []),
                "adminAcademyLessonEvents": timetable_context.get("academy_lessons", []),
                "warning": timetable_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Head of Department Timetable",
            description="Subject-scoped timetable workspace.",
            telegram=True,
        )

    @router.get("/head-of-department/announcements", operation_id="head_of_department_announcements")
    def head_of_department_announcements():
        announcement_context = _head_of_department_announcement_context()
        return render_react_page(
            "head-of-department-announcements",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "head_of_department",
                "workspace": "announcements",
                "adminAnnouncements": announcement_context.get("announcements", []),
                "warning": announcement_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Head of Department Announcements",
            description="Subject-scoped announcements workspace.",
            telegram=True,
        )

    @router.get("/head-of-department/profile", operation_id="head_of_department_profile")
    def head_of_department_profile():
        return render_role_home(
            "head-of-department-home",
            "head_of_department",
            title="Head of Department Profile",
            description="Head of Department profile and logout.",
            cards=head_of_department_workspace_cards(),
        )

    @router.get("/head-of-department/teacher-academy", operation_id="head_of_department_teacher_academy")
    def head_of_department_teacher_academy():
        academy_context = _head_of_department_academy_context()
        return render_react_page(
            "head-of-department-academy",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "adminMode": "head_of_department",
                "adminSchool": "all",
                "adminTeachers": academy_context.get("teachers", []),
                "adminTeacherAcademy": academy_context.get("academy_teachers", []),
                "adminGroupOptions": academy_context.get("group_options", []),
                "adminAcademicSubjects": academy_context.get("subjects", []),
                "adminAcademicCurriculumPrograms": academy_context.get("curriculum_programs", []),
                "adminAcademicCurriculumItems": academy_context.get("curriculum_items", []),
                "csrfToken": generate_csrf(),
            },
            title="Head of Department Teacher Academy",
            description="Subject-scoped Teacher Academy management.",
            telegram=True,
        )

    @router.post(
        "/head-of-department/api/teacher-academy/assignments/{assignment_id}",
        operation_id="head_of_department_update_academy_assignment",
    )
    def head_of_department_update_academy_assignment_api(assignment_id: int):
        if not can_current_user_manage_academy_assignment(assignment_id):
            return academy_error("This Teacher Academy lesson is outside your subject scope.", status=403)
        return update_assignment_response(assignment_id)

    @router.post(
        "/head-of-department/api/teacher-academy/{academy_teacher_id}/assessments",
        operation_id="head_of_department_add_academy_assessment",
    )
    def head_of_department_add_academy_assessment_api(academy_teacher_id: int):
        if not can_current_user_manage_academy_teacher(academy_teacher_id):
            return academy_error("This Teacher Academy teacher is outside your subject scope.", status=403)
        return add_assessment_response(academy_teacher_id, created_by_label="Head of Department")

    @router.post(
        "/head-of-department/api/teacher-academy/{academy_teacher_id}/status",
        operation_id="head_of_department_update_academy_status",
    )
    def head_of_department_update_academy_status_api(academy_teacher_id: int):
        if not can_current_user_manage_academy_teacher(academy_teacher_id):
            return academy_error("This Teacher Academy teacher is outside your subject scope.", status=403)
        return update_status_response(academy_teacher_id)

    app.include_router(router)


__all__ = ["register_head_of_department_page_routes"]
