"""Public Customer Support dashboard reporting contract."""

from __future__ import annotations

from typing import Protocol

from backend.core.access.context import SchoolScope
from backend.modules.domains.reporting.customer_support.schemas import (
    CustomerSupportActivitySummary,
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardMetrics,
    CustomerSupportDashboardResponse,
    CustomerSupportTicketSummary,
    DashboardTicketPriority,
    SupportRequesterType,
    TicketStatus,
)


class CustomerSupportDashboardReader(Protocol):
    """Public read boundary consumed by Customer Support orchestration."""

    def get_dashboard(
        self,
        *,
        school_scope: SchoolScope,
        filters: CustomerSupportDashboardFilters | None = None,
    ) -> CustomerSupportDashboardResponse:
        """Return a dashboard limited to the supplied effective school scope."""


__all__ = [
    "CustomerSupportActivitySummary",
    "CustomerSupportDashboardFilters",
    "CustomerSupportDashboardMetrics",
    "CustomerSupportDashboardReader",
    "CustomerSupportDashboardResponse",
    "CustomerSupportTicketSummary",
    "DashboardTicketPriority",
    "SupportRequesterType",
    "TicketStatus",
]
