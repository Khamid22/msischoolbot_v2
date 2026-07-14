"""Teacher role page routes: read-only Academy profile for signed-in academy teachers."""

from fastapi import APIRouter, Depends

from backend.core.guards import require_role
from backend.core.performance import PagePerformanceTimer, log_page_performance
from backend.core.rendering import generate_csrf, render_react_page
from backend.core.session import (
    current_auth_login,
    current_teacher_id,
    current_teacher_staff_id,
)
from backend.modules.teacher_academy.read_service import (
    get_academy_teacher_for_teacher_account,
)


def _safe_teacher_academy_profile():
    try:
        return get_academy_teacher_for_teacher_account(
            current_teacher_id(),
            current_teacher_staff_id(),
        )
    except Exception:
        return None


def register_teacher_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("teacher"))])

    @router.get("/teacher", operation_id="teacher_home")
    def teacher_home():
        timer = PagePerformanceTimer()
        academy_teacher = _safe_teacher_academy_profile()
        timer.mark("context_build")
        response = render_react_page(
            "teacher-home",
            {
                "authLogin": current_auth_login(),
                "authRole": "teacher",
                "academyTeacher": academy_teacher,
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
            rows={"academy_teacher": 1 if academy_teacher else 0},
        )
        return response

    app.include_router(router)


__all__ = ["register_teacher_page_routes"]
