"""Head of Department workspace routes."""

from fastapi import APIRouter, Depends

from backend.roles.head_of_department.workspace_cards import head_of_department_workspace_cards
from backend.roles.role_home import render_role_home
from backend.utils.guards import require_role


def register_head_of_department_page_routes(app, *, render_admin_page=None):
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

    @router.get("/head-of-department/teacher-academy", operation_id="head_of_department_teacher_academy")
    def head_of_department_teacher_academy():
        if callable(render_admin_page):
            return render_admin_page(admin_panel="teachers", admin_mode="head_of_department")
        return render_role_home(
            "head-of-department-home",
            "head_of_department",
            title="Teacher Academy",
            description="Teacher Academy management is temporarily unavailable.",
            cards=head_of_department_workspace_cards(),
        )

    app.include_router(router)


__all__ = ["register_head_of_department_page_routes"]
