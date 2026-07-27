"""Customer Support page shell routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from backend.core.web.workspace_rendering import render_role_home
from backend.core.access.pages import require_role


def register_customer_support_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("customer_support"))])

    @router.get("/customer-support", operation_id="customer_support_home")
    def customer_support_home():
        return RedirectResponse(url="/customer-support/dashboard", status_code=308)

    @router.get(
        "/customer-support/dashboard",
        operation_id="customer_support_dashboard",
    )
    def customer_support_dashboard():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Customer Support Dashboard",
            description="Monitor Customer Support operations.",
            view="dashboard",
        )

    @router.get(
        "/customer-support/payments",
        operation_id="customer_support_payments",
    )
    def customer_support_payments():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Payments Workspace",
            description="Review and manage student payment records.",
            view="payments",
        )

    @router.get(
        "/customer-support/parents",
        operation_id="customer_support_parents",
    )
    def customer_support_parents():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Parents",
            description="Find parents, manage profiles, and maintain verified student links.",
            view="parents",
        )

    @router.get(
        "/customer-support/students",
        operation_id="customer_support_students",
    )
    def customer_support_students():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Students",
            description="Find students, restore account access, and review records.",
            view="students",
        )

    @router.get(
        "/customer-support/teachers",
        operation_id="customer_support_teachers",
    )
    def customer_support_teachers():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Teachers",
            description="Find assigned-school teachers and review support information.",
            view="teachers",
        )

    @router.get(
        "/customer-support/tickets",
        operation_id="customer_support_tickets",
    )
    def customer_support_tickets():
        return render_role_home(
            "customer-support-home",
            "customer_support",
            title="Support Tickets",
            description="Manage incoming support requests and resolutions.",
            view="tickets",
        )

    @router.get("/support", include_in_schema=False)
    def legacy_customer_support_home():
        return RedirectResponse(url="/customer-support/dashboard", status_code=308)

    app.include_router(router)


__all__ = ["register_customer_support_page_routes"]
