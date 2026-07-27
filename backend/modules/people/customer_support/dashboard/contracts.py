"""Public Customer Support dashboard use-case contract."""

from backend.modules.domains.reporting.customer_support.contracts import (
    CustomerSupportActivitySummary,
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardMetrics,
    CustomerSupportDashboardResponse,
    CustomerSupportTicketSummary,
)
from backend.modules.people.customer_support.dashboard.queries import (
    GetCustomerSupportDashboard,
)

__all__ = [
    "CustomerSupportActivitySummary",
    "CustomerSupportDashboardFilters",
    "CustomerSupportDashboardMetrics",
    "CustomerSupportDashboardResponse",
    "CustomerSupportTicketSummary",
    "GetCustomerSupportDashboard",
]
