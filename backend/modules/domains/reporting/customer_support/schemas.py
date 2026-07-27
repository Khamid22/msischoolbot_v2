"""Typed Customer Support operational dashboard projections."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from backend.core.api.schemas import ApiModel
from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketCategory,
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)

PositiveIdentifier = Annotated[int, Field(gt=0)]
DashboardPeriodDays = Literal[7, 30, 90]


class CustomerSupportDashboardFilters(ApiModel):
    """Filters applied after the caller's current assignments are resolved."""

    school_ids: frozenset[PositiveIdentifier] = Field(default_factory=frozenset)
    period_days: DashboardPeriodDays = 30
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


class CustomerSupportSchool(ApiModel):
    school_id: PositiveIdentifier
    school_name: str = Field(min_length=1, max_length=200)


class CustomerSupportDashboardMetrics(ApiModel):
    open_tickets: int = Field(default=0, ge=0)
    assigned_to_me: int = Field(default=0, ge=0)
    unassigned_tickets: int = Field(default=0, ge=0)
    escalated_tickets: int = Field(default=0, ge=0)
    sla_breached_tickets: int = Field(default=0, ge=0)
    waiting_on_requester_tickets: int = Field(default=0, ge=0)
    overdue_payment_accounts: int = Field(default=0, ge=0)
    students_without_active_parent_link: int = Field(default=0, ge=0)
    # Deprecated compatibility names kept until the prepared reporting tests migrate.
    overdue_tickets: int = Field(default=0, ge=0)
    parent_account_issues: int = Field(default=0, ge=0)
    teacher_account_issues: int = Field(default=0, ge=0)


class DailyTicketFlow(ApiModel):
    day: date
    opened: int = Field(ge=0)
    resolved: int = Field(ge=0)


class TicketAgeBucket(ApiModel):
    bucket: Literal["under_24h", "one_to_three_days", "four_to_seven_days", "eight_plus_days"]
    label: str
    count: int = Field(ge=0)


class TicketCategoryVolume(ApiModel):
    category: TicketCategory
    count: int = Field(ge=0)


class SchoolTicketWorkload(ApiModel):
    school_id: PositiveIdentifier
    school_name: str
    open_tickets: int = Field(ge=0)
    unassigned_tickets: int = Field(ge=0)
    sla_breached_tickets: int = Field(ge=0)


class CustomerSupportTicketSummary(ApiModel):
    ticket_id: PositiveIdentifier
    parent_id: PositiveIdentifier | None = None
    student_id: PositiveIdentifier | None = None
    student_row_id: PositiveIdentifier | None = None
    student_code: str = ""
    title: str = Field(min_length=1, max_length=300)
    requester_name: str = Field(default="", max_length=200)
    school_id: PositiveIdentifier
    school_name: str = Field(default="", max_length=200)
    requester_kind: Literal["parent", "teacher", "student", "other"] = "parent"
    requester_id: PositiveIdentifier | None = None
    category: TicketCategory = TicketCategory.OTHER
    status: TicketStatus
    priority: TicketPriority
    sla_state: TicketSlaState = TicketSlaState.ON_TRACK
    assigned_staff_id: PositiveIdentifier | None = None
    assigned_staff_name: str = Field(default="", max_length=200)
    created_at: datetime
    updated_at: datetime | None = None
    first_response_due_at: datetime | None = None
    resolution_due_at: datetime | None = None
    is_waiting_on_requester: bool = False


class CurrencyAmount(ApiModel):
    currency: str = Field(min_length=1, max_length=10)
    amount: Decimal = Field(ge=0)
    account_count: int = Field(ge=0)


class OverduePaymentAccount(ApiModel):
    payment_id: PositiveIdentifier
    student_id: PositiveIdentifier
    student_row_id: PositiveIdentifier | None = None
    student_code: str
    student_name: str
    school_id: PositiveIdentifier
    school_name: str
    due_date: date
    amount: Decimal = Field(ge=0)
    currency: str
    days_overdue: int = Field(ge=1)


class StudentWithoutParentLink(ApiModel):
    student_id: PositiveIdentifier
    student_row_id: PositiveIdentifier | None = None
    student_code: str
    student_name: str
    school_id: PositiveIdentifier
    school_name: str


class PaymentExceptionSummary(ApiModel):
    overdue_totals: list[CurrencyAmount] = Field(default_factory=list)
    due_soon_totals: list[CurrencyAmount] = Field(default_factory=list)
    top_overdue_accounts: list[OverduePaymentAccount] = Field(default_factory=list)


class AccountExceptionSummary(ApiModel):
    students_without_active_parent_link: list[StudentWithoutParentLink] = Field(
        default_factory=list
    )


class CustomerSupportActivitySummary(ApiModel):
    activity_id: str = Field(min_length=1, max_length=100)
    activity_type: Literal["ticket", "payment"]
    event_type: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    school_id: PositiveIdentifier
    school_name: str
    entity_id: PositiveIdentifier
    actor_staff_id: PositiveIdentifier | None = None
    actor_name: str = Field(default="", max_length=200)
    occurred_at: datetime


class CustomerSupportDashboardData(ApiModel):
    available_schools: list[CustomerSupportSchool] = Field(default_factory=list)
    metrics: CustomerSupportDashboardMetrics = Field(
        default_factory=CustomerSupportDashboardMetrics
    )
    daily_ticket_flow: list[DailyTicketFlow] = Field(default_factory=list)
    ticket_age_buckets: list[TicketAgeBucket] = Field(default_factory=list)
    ticket_categories: list[TicketCategoryVolume] = Field(default_factory=list)
    school_workload: list[SchoolTicketWorkload] = Field(default_factory=list)
    action_required_tickets: list[CustomerSupportTicketSummary] = Field(default_factory=list)
    oldest_open_tickets: list[CustomerSupportTicketSummary] = Field(default_factory=list)
    payment_exceptions: PaymentExceptionSummary = Field(default_factory=PaymentExceptionSummary)
    account_exceptions: AccountExceptionSummary = Field(default_factory=AccountExceptionSummary)
    recent_activity: list[CustomerSupportActivitySummary] = Field(default_factory=list)


class CustomerSupportDashboardResponse(CustomerSupportDashboardData):
    generated_at: datetime
    period_days: DashboardPeriodDays
    period_started_at: datetime
    period_ended_at: datetime
    effective_school_ids: list[PositiveIdentifier] = Field(default_factory=list)
    school_ids: list[PositiveIdentifier] = Field(default_factory=list)
    all_schools: bool = False
    available_schools: list[CustomerSupportSchool] = Field(default_factory=list)


__all__ = [
    "AccountExceptionSummary",
    "CurrencyAmount",
    "CustomerSupportActivitySummary",
    "CustomerSupportDashboardData",
    "CustomerSupportDashboardFilters",
    "CustomerSupportDashboardMetrics",
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
