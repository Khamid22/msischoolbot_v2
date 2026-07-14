"""HR Manager page shell routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from backend.workspaces.shared import render_role_home
from backend.modules.reporting.service import hr_manager_workspace_cards
from backend.core.access.pages import require_role


def register_hr_manager_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("hr_manager"))])

    @router.get("/hr-manager", operation_id="hr_manager_home")
    def hr_manager_home():
        return render_role_home(
            "hr-manager-home",
            "hr_manager",
            title="HR Manager Dashboard",
            description="Teacher candidates, interviews, academy records, and staff profiles.",
            cards=hr_manager_workspace_cards(),
        )

    @router.get("/hr", include_in_schema=False)
    def legacy_hr_manager_home():
        return RedirectResponse(url="/hr-manager", status_code=308)

    app.include_router(router)


__all__ = ["register_hr_manager_page_routes"]
