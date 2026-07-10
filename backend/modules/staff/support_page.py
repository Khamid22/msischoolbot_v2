"""Customer Support page shell routes."""

from fastapi import APIRouter, Depends

from backend.modules.staff.page import render_role_home
from backend.modules.staff.workspace import customer_support_workspace_cards
from backend.core.guards import require_role


def register_customer_support_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("customer_support"))])

    @router.get("/support", operation_id="customer_support_home")
    @router.get("/customer-support", include_in_schema=False)
    def customer_support_home():
        return render_role_home(
            "support-home",
            "customer_support",
            title="Customer Support Dashboard",
            description="Parent contacts, support tickets, payment follow-up, and student basics.",
            cards=customer_support_workspace_cards(),
        )

    app.include_router(router)


__all__ = ["register_customer_support_page_routes"]
