"""CEO role page routes."""

from fastapi import APIRouter, Depends

from backend.roles.role_home import render_role_home
from backend.utils.guards import require_role


def register_ceo_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("ceo"))])

    @router.get("/ceo")
    def ceo_home():
        return render_role_home(
            "ceo-home",
            "ceo",
            title="CEO Dashboard",
            description="School performance, finance, staff health, and strategic decisions.",
            cards=[
                {"label": "Company Overview", "value": "Shell"},
                {"label": "Payments Summary", "value": "Placeholder"},
                {"label": "Academic Performance", "value": "Placeholder"},
            ],
        )

    app.include_router(router)


__all__ = ["register_ceo_page_routes"]
