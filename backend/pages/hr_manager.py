"""HR Manager page shell routes."""

from fastapi import APIRouter, Depends

from backend.roles.role_home import render_role_home
from backend.roles.workspace_counts import hr_manager_workspace_cards
from backend.utils.guards import require_role


def register_hr_manager_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("hr_manager"))])

    @router.get("/hr", operation_id="hr_manager_home")
    @router.get("/hr-manager", include_in_schema=False)
    def hr_home():
        return render_role_home(
            "hr-home",
            "hr_manager",
            title="HR Manager Dashboard",
            description="Teacher candidates, interviews, academy records, and staff profiles.",
            cards=hr_manager_workspace_cards(),
        )

    app.include_router(router)


__all__ = ["register_hr_manager_page_routes"]
