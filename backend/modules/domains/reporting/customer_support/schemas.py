"""Typed Customer Support dashboard filters and projections."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from backend.core.api.schemas import ApiModel
from backend.modules.domains.reporting.customer_support.domain_types import (
    DashboardTicketPriority,
    SupportRequesterType,
)
from backend.modules.domains.support_cases.tickets.domain_types import TicketStatus

PositiveIdentifier = Annotated[int, Field(gt=0)]


class CustomerSupportDashboardFilters(ApiModel):
    """Optional filters applied within the caller's effective school scope."""

    school_ids: frozenset[PositiveIdentifier] = Field(default_factory=frozenset)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    ticket_limit: int = Field(default=10, ge=1, le=50)
    activity_limit: int = Field(default=20, ge=1, le=100)

    @field_validator("started_at", "ended_at")
    @classmethod
    def require_timezone_aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Dashboard date filters must be timezone-aware.")
        return value

    @model_validator(mode="after")
    def require_ordered_period(self) -> Self:
        if (
            self.started_at is not None
            and self.ended_at is not None
            and self.started_at > self.ended_at
        ):
            raise ValueError("Dashboard start time must not be after its end time.")
        return self


class CustomerSupportDashboardMetrics(ApiModel):
    """Server-calculated operational totals for the dashboard."""

    open_tickets: int = Field(default=0, ge=0)
    unassigned_tickets: int = Field(default=0, ge=0)
    escalated_tickets: int = Field(default=0, ge=0)
    overdue_tickets: int = Field(default=0, ge=0)
    waiting_on_requester_tickets: int = Field(default=0, ge=0)
    parent_account_issues: int = Field(default=0, ge=0)
    teacher_account_issues: int = Field(default=0, ge=0)


class CustomerSupportTicketSummary(ApiModel):
    """Small ticket projection suitable for dashboard queues."""

    ticket_id: PositiveIdentifier
    title: str = Field(min_length=1, max_length=300)
    requester_kind: SupportRequesterType
    requester_id: PositiveIdentifier | None = None
    requester_name: str = Field(default="", max_length=200)
    school_id: PositiveIdentifier
    school_name: str = Field(default="", max_length=200)
    status: TicketStatus
    priority: DashboardTicketPriority
    assigned_account_id: PositiveIdentifier | None = None
    assigned_account_name: str = Field(default="", max_length=200)
    created_at: datetime
    first_response_due_at: datetime | None = None
    resolution_due_at: datetime | None = None


class CustomerSupportActivitySummary(ApiModel):
    """Audit/event projection shown in the recent-activity feed."""

    activity_id: PositiveIdentifier
    event_type: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    school_id: PositiveIdentifier
    actor_account_id: PositiveIdentifier | None = None
    actor_name: str = Field(default="", max_length=200)
    occurred_at: datetime


class CustomerSupportDashboardData(ApiModel):
    """Repository-produced data before query metadata is attached."""

    metrics: CustomerSupportDashboardMetrics = Field(
        default_factory=CustomerSupportDashboardMetrics
    )
    action_required_tickets: list[CustomerSupportTicketSummary] = Field(default_factory=list)
    oldest_open_tickets: list[CustomerSupportTicketSummary] = Field(default_factory=list)
    recent_activity: list[CustomerSupportActivitySummary] = Field(default_factory=list)


class CustomerSupportDashboardResponse(CustomerSupportDashboardData):
    """Complete school-scoped dashboard read model."""

    generated_at: datetime
    period_started_at: datetime
    period_ended_at: datetime
    school_ids: list[PositiveIdentifier] = Field(default_factory=list)
    all_schools: bool = False


__all__ = [
    "CustomerSupportActivitySummary",
    "CustomerSupportDashboardData",
    "CustomerSupportDashboardFilters",
    "CustomerSupportDashboardMetrics",
    "CustomerSupportDashboardResponse",
    "CustomerSupportTicketSummary",
    "DashboardTicketPriority",
    "SupportRequesterType",
    "TicketStatus",
]
