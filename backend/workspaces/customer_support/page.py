"""Customer Support page shell routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from backend.workspaces.shared import render_role_home
from backend.modules.reporting.service import customer_support_workspace_cards
from backend.core.access.pages import require_role


def register_customer_support_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("customer_support"))])

    @router.get("/customer-support", operation_id="customer_support_home")
    def customer_support_home():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Customer Support Dashboard",
            description="Parent contacts, support tickets, payment follow-up, and student basics.",
            cards=customer_support_workspace_cards(),
        )

    @router.get("/support", include_in_schema=False)
    def legacy_customer_support_home():
        return RedirectResponse(url="/customer-support", status_code=308)

    app.include_router(router)


__all__ = ["register_customer_support_page_routes"]
