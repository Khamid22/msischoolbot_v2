"""CEO page shell routes."""

from fastapi import APIRouter, Depends

from backend.core.web.workspace_rendering import render_role_home
from backend.modules.people.ceo.contracts import (
    ceo_workspace_cards,
    register_ceo_recruitment_routes,
)
from backend.core.access.pages import require_role


def register_ceo_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("ceo"))])

    @router.get("/ceo")
    def ceo_home():
        return render_role_home(
            "ceo-home",
            "ceo",
            title="CEO Dashboard",
            description="School performance, finance, staff health, and strategic decisions.",
            cards=ceo_workspace_cards(),
        )

    app.include_router(router)


def register_ceo_recruitment_page_routes(app):
    register_ceo_recruitment_routes(app)


__all__ = ["register_ceo_page_routes", "register_ceo_recruitment_page_routes"]
