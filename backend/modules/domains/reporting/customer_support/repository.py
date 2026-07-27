"""Persistence port for the Customer Support dashboard read model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.core.unit_of_work import Connection
from backend.modules.domains.reporting.customer_support.schemas import (
    CustomerSupportDashboardData,
)


@dataclass(frozen=True)
class CustomerSupportDashboardReadScope:
    """Resolved query scope passed explicitly to every dashboard read."""

    school_ids: tuple[int, ...]
    all_schools: bool
    available_school_ids: tuple[int, ...]
    has_all_school_access: bool
    started_at: datetime
    ended_at: datetime
    ticket_limit: int
    activity_limit: int
    actor_staff_id: int | None

    @property
    def has_school_access(self) -> bool:
        return self.all_schools or bool(self.school_ids)


class CustomerSupportDashboardRepository(Protocol):
    """Repository implemented when the supporting projections are persisted."""

    def load_dashboard(
        self,
        conn: Connection,
        scope: CustomerSupportDashboardReadScope,
    ) -> CustomerSupportDashboardData:
        """Load one consistent, server-calculated dashboard snapshot."""


__all__ = [
    "CustomerSupportDashboardReadScope",
    "CustomerSupportDashboardRepository",
]
