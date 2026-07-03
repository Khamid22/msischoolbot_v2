"""Academic Director role page routes."""

from fastapi import APIRouter, Depends

from backend.roles.role_home import render_role_home
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
            description="Teacher Academy, curriculum progress, lesson observations, and quality control.",
            cards=[
                {"label": "Teacher Academy", "value": "Training"},
                {"label": "Curriculum", "value": "Progress"},
                {"label": "Reviews", "value": "Observations"},
            ],
        )

    app.include_router(router)


__all__ = ["register_academic_director_page_routes"]
