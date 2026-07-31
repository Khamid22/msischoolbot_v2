"""Teacher role page routes: read-only Academy profile for signed-in academy teachers."""

from fastapi import APIRouter, Depends

from backend.core.access.pages import require_role
from backend.core.runtime.performance import PagePerformanceTimer, log_page_performance
from backend.core.web.rendering import generate_csrf, render_react_page
from backend.modules.people.teacher.contracts import (
    current_auth_login,
    current_teacher_id,
    current_teacher_staff_id,
    get_academy_teacher_for_teacher_account,
    get_active_teacher_workspace_profile,
    list_teacher_subject_curricula,
)


def _safe_teacher_academy_profile():
    try:
        return get_academy_teacher_for_teacher_account(
            current_teacher_id(),
            current_teacher_staff_id(),
        )
    except Exception:
        return None


def _safe_teacher_workspace_profile():
    try:
        return get_active_teacher_workspace_profile(current_teacher_id())
    except Exception:
        return None


def _safe_subject_curriculum_catalog():
    try:
        teacher_id = int(current_teacher_id() or 0)
        if teacher_id <= 0:
            return {"subjects": []}
        return list_teacher_subject_curricula(teacher_id).model_dump(
            mode="json",
            by_alias=True,
        )
    except Exception:
        return {"subjects": []}


def register_teacher_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("teacher"))])

    def render_teacher_workspace(initial_tab: str):
        timer = PagePerformanceTimer()
        academy_teacher = _safe_teacher_academy_profile()
        teacher_profile = _safe_teacher_workspace_profile()
        curriculum_catalog = _safe_subject_curriculum_catalog()
        timer.mark("context_build")
        response = render_react_page(
            "teacher-home",
            {
                "authLogin": current_auth_login(),
                "authRole": "teacher",
                "academyTeacher": academy_teacher,
                "teacherProfile": teacher_profile,
                "subjectCurriculumCatalog": curriculum_catalog,
                "initialTab": initial_tab,
                "csrfToken": generate_csrf(),
            },
            title="MSI School Portal",
            description="Your Teacher Academy profile.",
            telegram=True,
        )
        timer.mark("render")
        log_page_performance(
            "teacher_home",
            timer,
            response=response,
            rows={
                "academy_teacher": 1 if academy_teacher else 0,
                "teacher_profile": 1 if teacher_profile else 0,
                "curriculum_subjects": curriculum_catalog.get("subjects", []),
            },
        )
        return response

    @router.get("/teacher", operation_id="teacher_home")
    def teacher_home():
        return render_teacher_workspace("overview")

    @router.get(
        "/teacher/subject-curriculum",
        operation_id="teacher_subject_curriculum",
    )
    def teacher_subject_curriculum():
        return render_teacher_workspace("curriculum")

    app.include_router(router)


__all__ = ["register_teacher_page_routes"]
