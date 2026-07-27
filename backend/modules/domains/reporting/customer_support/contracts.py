"""Public Customer Support dashboard reporting contract."""

from __future__ import annotations

from typing import Protocol

from backend.core.access.context import SchoolScope
from backend.modules.domains.reporting.customer_support.schemas import (
    AccountExceptionSummary,
    CurrencyAmount,
    CustomerSupportActivitySummary,
    CustomerSupportDashboardData,
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardMetrics,
    CustomerSupportDashboardResponse,
    CustomerSupportSchool,
    CustomerSupportTicketSummary,
    DailyTicketFlow,
    DashboardPeriodDays,
    OverduePaymentAccount,
    PaymentExceptionSummary,
    SchoolTicketWorkload,
    StudentWithoutParentLink,
    TicketAgeBucket,
    TicketCategoryVolume,
)


class CustomerSupportDashboardReader(Protocol):
    """Public read boundary consumed by Customer Support orchestration."""

    def get_dashboard(
        self,
        *,
        school_scope: SchoolScope,
        actor_staff_id: int | None = None,
        filters: CustomerSupportDashboardFilters | None = None,
    ) -> CustomerSupportDashboardResponse:
        """Return a dashboard limited to the supplied effective school scope."""


__all__ = [
    "AccountExceptionSummary",
    "CurrencyAmount",
    "CustomerSupportActivitySummary",
    "CustomerSupportDashboardData",
    "CustomerSupportDashboardFilters",
    "CustomerSupportDashboardMetrics",
    "CustomerSupportDashboardReader",
    "CustomerSupportDashboardResponse",
    "CustomerSupportSchool",
    "CustomerSupportTicketSummary",
    "DailyTicketFlow",
    "DashboardPeriodDays",
    "OverduePaymentAccount",
    "PaymentExceptionSummary",
    "SchoolTicketWorkload",
    "StudentWithoutParentLink",
    "TicketAgeBucket",
    "TicketCategoryVolume",
]
