"""Academic Director role page routes."""

from fastapi import APIRouter, Depends

from backend.roles.role_home import render_role_home
from backend.roles.workspace_counts import academic_director_workspace_cards
from backend.utils.guards import require_role


def register_academic_director_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("academic_director"))])

    @router.get("/academic-director", operation_id="academic_director_home")
    @router.get("/academic_director", include_in_schema=False)
    def academic_director_home():
        return render_role_home(
            "academic-director-home",
            "academic_director",
            title="Academic Director Dashboard",
            description="Groups, teachers, subjects, attendance, and academic progress.",
            cards=academic_director_workspace_cards(),
        )

    app.include_router(router)


__all__ = ["register_academic_director_page_routes"]
