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
from backend.modules.people.customer_support.scope import CustomerSupportScopeProvider


@dataclass(frozen=True)
class GetCustomerSupportDashboard:
    reader: CustomerSupportDashboardReader
    scope_resolver: CustomerSupportScopeProvider | None = None

    def __call__(
        self,
        actor: ActorContext,
        filters: CustomerSupportDashboardFilters | None = None,
    ) -> CustomerSupportDashboardResponse:
        require_capability(actor, Capability.VIEW_DASHBOARD)
        scoped_actor = (
            self.scope_resolver.resolve(actor) if self.scope_resolver is not None else actor
        )
        if scoped_actor.staff_id is None:
            return self.reader.get_dashboard(
                school_scope=scoped_actor.school_scope,
                filters=filters,
            )
        return self.reader.get_dashboard(
            school_scope=scoped_actor.school_scope,
            actor_staff_id=scoped_actor.staff_id,
            filters=filters,
        )


__all__ = ["GetCustomerSupportDashboard"]
