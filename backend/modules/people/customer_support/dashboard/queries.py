"""Customer Support authorization around the reporting dashboard contract."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability
from backend.modules.domains.reporting.customer_support.contracts import (
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardReader,
    CustomerSupportDashboardResponse,
)
from backend.modules.people.customer_support.policies import require_capability


@dataclass(frozen=True)
class GetCustomerSupportDashboard:
    reader: CustomerSupportDashboardReader

    def __call__(
        self,
        actor: ActorContext,
        filters: CustomerSupportDashboardFilters | None = None,
    ) -> CustomerSupportDashboardResponse:
        require_capability(actor, Capability.VIEW_DASHBOARD)
        return self.reader.get_dashboard(
            school_scope=actor.school_scope,
            filters=filters,
        )


__all__ = ["GetCustomerSupportDashboard"]
