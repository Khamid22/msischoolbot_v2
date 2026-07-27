"""Customer Support dashboard query orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.core.access.context import SchoolScope
from backend.core.clock import Clock, SystemClock
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.reporting.customer_support.repository import (
    CustomerSupportDashboardReadScope,
    CustomerSupportDashboardRepository,
)
from backend.modules.domains.reporting.customer_support.schemas import (
    CustomerSupportDashboardData,
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardResponse,
)

DEFAULT_DASHBOARD_LOOKBACK_DAYS = 30


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value


def _resolve_school_scope(
    school_scope: SchoolScope,
    requested_school_ids: frozenset[int],
) -> tuple[tuple[int, ...], bool]:
    if school_scope.all_schools:
        if requested_school_ids:
            return tuple(sorted(requested_school_ids)), False
        return (), True

    disallowed_school_ids = requested_school_ids - school_scope.allowed_school_ids
    if disallowed_school_ids:
        raise PermissionError("Dashboard filters include schools outside the actor's scope.")

    effective_school_ids = requested_school_ids or school_scope.allowed_school_ids
    return tuple(sorted(effective_school_ids)), False


def _empty_data() -> CustomerSupportDashboardData:
    return CustomerSupportDashboardData()


@dataclass(frozen=True)
class CustomerSupportDashboardQueries:
    """Build a scoped dashboard through one read-only transaction."""

    unit_of_work_factory: UnitOfWorkFactory
    repository: CustomerSupportDashboardRepository
    clock: Clock = field(default_factory=SystemClock)

    def get_dashboard(
        self,
        *,
        school_scope: SchoolScope,
        filters: CustomerSupportDashboardFilters | None = None,
    ) -> CustomerSupportDashboardResponse:
        selected_filters = filters or CustomerSupportDashboardFilters()
        generated_at = _require_aware(self.clock.now(), field_name="generated_at")
        ended_at = selected_filters.ended_at or generated_at
        started_at = selected_filters.started_at or (
            ended_at - timedelta(days=DEFAULT_DASHBOARD_LOOKBACK_DAYS)
        )
        if started_at > ended_at:
            raise ValueError("Dashboard start time must not be after its end time.")

        school_ids, all_schools = _resolve_school_scope(
            school_scope,
            selected_filters.school_ids,
        )
        read_scope = CustomerSupportDashboardReadScope(
            school_ids=school_ids,
            all_schools=all_schools,
            started_at=started_at,
            ended_at=ended_at,
            ticket_limit=selected_filters.ticket_limit,
            activity_limit=selected_filters.activity_limit,
        )

        dashboard_data = _empty_data()
        if read_scope.has_school_access:
            with self.unit_of_work_factory.read() as unit_of_work:
                dashboard_data = self.repository.load_dashboard(
                    unit_of_work.conn,
                    read_scope,
                )

        return CustomerSupportDashboardResponse(
            generated_at=generated_at,
            period_started_at=started_at,
            period_ended_at=ended_at,
            school_ids=list(school_ids),
            all_schools=all_schools,
            metrics=dashboard_data.metrics,
            action_required_tickets=dashboard_data.action_required_tickets,
            oldest_open_tickets=dashboard_data.oldest_open_tickets,
            recent_activity=dashboard_data.recent_activity,
        )


__all__ = [
    "DEFAULT_DASHBOARD_LOOKBACK_DAYS",
    "CustomerSupportDashboardQueries",
]
