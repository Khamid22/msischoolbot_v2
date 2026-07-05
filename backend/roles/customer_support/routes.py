"""Customer Support role page routes."""

from fastapi import APIRouter, Depends

from backend.roles.role_home import render_role_home
from backend.utils.guards import require_role


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
            cards=[
                {"label": "Parent Search", "value": "Shell"},
                {"label": "Payment Status", "value": "Placeholder"},
                {"label": "Parent Invites", "value": "Placeholder"},
            ],
        )

    app.include_router(router)


__all__ = ["register_customer_support_page_routes"]
