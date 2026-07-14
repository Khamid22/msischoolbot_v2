"""Head of Department workspace routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from backend.modules.communications.announcements_service import list_announcements
from backend.core.web.rendering import generate_csrf, render_react_page
from backend.modules.teacher_academy.read_service import (
    list_academy_timetable_events,
    list_teacher_academy_page_context,
)
from backend.modules.teacher_academy.policies import (
    hod_subject_ids_for_context,
    filter_rows_by_subject_scope,
)
from backend.modules.academics.head_of_departments_cards import head_of_department_workspace_cards
from backend.workspaces.shared import render_role_home
from backend.core.access.pages import require_role
from backend.core.web.request_context import session
from backend.modules.identity.session import current_auth_login, current_auth_role, current_staff_id


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


def current_hod_subject_ids(conn=None):
    return hod_subject_ids_for_context(
        role=current_auth_role(),
        account_id=session.get("account_id"),
        staff_id=current_staff_id() or 0,
        conn=conn,
    )


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
    # The HoD timetable shows subject-scoped Teacher Academy lessons only —
    # regular gradebook sessions live in the admin panel.
    try:
        subject_ids = current_hod_subject_ids()
        academy_lessons = list_academy_timetable_events(subject_ids)
    except Exception as exc:
        return {"academy_lessons": [], "warning": f"Subject timetable could not be loaded: {exc}"}
    return {"academy_lessons": academy_lessons, "warning": ""}


def _head_of_department_announcement_context():
    try:
        announcements = list_announcements(include_drafts=True)
    except Exception as exc:
        return {"announcements": [], "warning": f"Announcements could not be loaded: {exc}"}
    return {"announcements": announcements, "warning": ""}


def register_head_of_department_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("head_of_department"))])

    @router.get("/head-of-departments", operation_id="head_of_departments_home")
    def head_of_department_home():
        return render_role_home(
            "head-of-departments-home",
            "head_of_department",
            title="Head of Departments Dashboard",
            description="Subject-scoped Teacher Academy management, teacher profiles, and journeys.",
            cards=head_of_department_workspace_cards(),
        )

    @router.get("/head-of-departments/timetable", operation_id="head_of_departments_timetable")
    def head_of_department_timetable():
        timetable_context = _head_of_department_timetable_context()
        return render_react_page(
            "head-of-departments-timetable",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "head_of_department",
                "workspace": "timetable",
                "adminAcademyLessonEvents": timetable_context.get("academy_lessons", []),
                "warning": timetable_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Head of Departments Timetable",
            description="Subject-scoped timetable workspace.",
            telegram=True,
        )

    @router.get("/head-of-departments/announcements", operation_id="head_of_departments_announcements")
    def head_of_department_announcements():
        announcement_context = _head_of_department_announcement_context()
        return render_react_page(
            "head-of-departments-announcements",
            {
                "authLogin": current_auth_login(),
                "authRole": current_auth_role(),
                "role": "head_of_department",
                "workspace": "announcements",
                "adminAnnouncements": announcement_context.get("announcements", []),
                "warning": announcement_context.get("warning", ""),
                "csrfToken": generate_csrf(),
            },
            title="Head of Departments Announcements",
            description="Subject-scoped announcements workspace.",
            telegram=True,
        )

    @router.get("/head-of-departments/profile", operation_id="head_of_departments_profile")
    def head_of_department_profile():
        return render_role_home(
            "head-of-departments-home",
            "head_of_department",
            title="Head of Departments Profile",
            description="Head of Departments profile and logout.",
            cards=head_of_department_workspace_cards(),
            view="profile",
        )

    @router.get("/head-of-departments/teacher-academy", operation_id="head_of_departments_teacher_academy")
    def head_of_department_teacher_academy():
        academy_context = _head_of_department_academy_context()
        return render_react_page(
            "head-of-departments-academy",
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
            title="Head of Departments Teacher Academy",
            description="Subject-scoped Teacher Academy management.",
            telegram=True,
        )

    @router.get("/head-of-department", include_in_schema=False)
    @router.get("/head-of-department/{legacy_path:path}", include_in_schema=False)
    def legacy_head_of_department_workspace(legacy_path: str = ""):
        suffix = f"/{legacy_path}" if legacy_path else ""
        return RedirectResponse(url=f"/head-of-departments{suffix}", status_code=308)

    app.include_router(router)


__all__ = ["register_head_of_department_page_routes"]
