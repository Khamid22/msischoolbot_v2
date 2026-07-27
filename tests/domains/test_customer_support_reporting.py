"""Focused tests for the prepared Customer Support reporting boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.core.access.context import SchoolScope
from backend.core.clock import FixedClock
from backend.core.unit_of_work import Connection, UnitOfWorkFactory
from backend.modules.domains.reporting.customer_support.queries import (
    DEFAULT_DASHBOARD_LOOKBACK_DAYS,
    CustomerSupportDashboardQueries,
)
from backend.modules.domains.reporting.customer_support.repository import (
    CustomerSupportDashboardReadScope,
)
from backend.modules.domains.reporting.customer_support.schemas import (
    CustomerSupportDashboardData,
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardMetrics,
    CustomerSupportTicketSummary,
)


class _Result:
    pass


class _Connection:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.rollback_count = 0
        self.close_count = 0

    def execute(self, sql: str, params: object = None) -> _Result:
        self.statements.append(sql)
        return _Result()

    def commit(self) -> None:
        raise AssertionError("Dashboard queries must not commit.")

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.close_count += 1


class _Repository:
    def __init__(self, data: CustomerSupportDashboardData) -> None:
        self.data = data
        self.connection: Connection | None = None
        self.scope: CustomerSupportDashboardReadScope | None = None

    def load_dashboard(
        self,
        conn: Connection,
        scope: CustomerSupportDashboardReadScope,
    ) -> CustomerSupportDashboardData:
        self.connection = conn
        self.scope = scope
        return self.data


def _queries(
    connection: _Connection,
    repository: _Repository,
    now: datetime,
) -> CustomerSupportDashboardQueries:
    return CustomerSupportDashboardQueries(
        unit_of_work_factory=UnitOfWorkFactory(lambda: connection),
        repository=repository,
        clock=FixedClock(now),
    )


def test_dashboard_query_resolves_assigned_scope_and_uses_read_only_transaction():
    now = datetime(2026, 7, 27, 9, 30, tzinfo=UTC)
    connection = _Connection()
    ticket = CustomerSupportTicketSummary(
        ticket_id=41,
        title="Parent cannot access the portal",
        requester_kind="parent",
        requester_id=12,
        school_id=7,
        status="new",
        priority="high",
        created_at=now - timedelta(hours=2),
    )
    repository = _Repository(
        CustomerSupportDashboardData(
            metrics=CustomerSupportDashboardMetrics(
                open_tickets=4,
                unassigned_tickets=2,
            ),
            action_required_tickets=[ticket],
        )
    )

    result = _queries(connection, repository, now).get_dashboard(
        school_scope=SchoolScope(allowed_school_ids=frozenset({9, 7})),
        filters=CustomerSupportDashboardFilters(ticket_limit=5),
    )

    assert result.school_ids == [7, 9]
    assert result.all_schools is False
    assert result.period_started_at == now - timedelta(days=DEFAULT_DASHBOARD_LOOKBACK_DAYS)
    assert result.metrics.open_tickets == 4
    assert result.action_required_tickets == [ticket]
    assert repository.connection is connection
    assert repository.scope is not None
    assert repository.scope.school_ids == (7, 9)
    assert repository.scope.ticket_limit == 5
    assert connection.statements == ["SET TRANSACTION READ ONLY"]
    assert connection.rollback_count == 1
    assert connection.close_count == 1


def test_dashboard_query_rejects_requested_schools_outside_assignment():
    now = datetime(2026, 7, 27, tzinfo=UTC)
    connection = _Connection()
    repository = _Repository(CustomerSupportDashboardData())

    with pytest.raises(PermissionError, match="outside"):
        _queries(connection, repository, now).get_dashboard(
            school_scope=SchoolScope(allowed_school_ids=frozenset({7})),
            filters=CustomerSupportDashboardFilters(school_ids=frozenset({8})),
        )

    assert repository.scope is None
    assert connection.statements == []


def test_empty_assigned_scope_returns_empty_dashboard_without_database_access():
    now = datetime(2026, 7, 27, tzinfo=UTC)
    connection = _Connection()
    repository = _Repository(CustomerSupportDashboardData())

    result = _queries(connection, repository, now).get_dashboard(
        school_scope=SchoolScope(),
    )

    assert result.school_ids == []
    assert result.all_schools is False
    assert result.metrics == CustomerSupportDashboardMetrics()
    assert repository.scope is None
    assert connection.statements == []


def test_all_schools_scope_can_be_narrowed_and_serializes_camel_case():
    now = datetime(2026, 7, 27, tzinfo=UTC)
    connection = _Connection()
    repository = _Repository(CustomerSupportDashboardData())

    result = _queries(connection, repository, now).get_dashboard(
        school_scope=SchoolScope(all_schools=True),
        filters=CustomerSupportDashboardFilters(school_ids=frozenset({4, 2})),
    )

    assert repository.scope is not None
    assert repository.scope.school_ids == (2, 4)
    assert repository.scope.all_schools is False
    payload = result.model_dump(by_alias=True)
    assert payload["schoolIds"] == [2, 4]
    assert payload["periodStartedAt"] == now - timedelta(days=DEFAULT_DASHBOARD_LOOKBACK_DAYS)


def test_dashboard_filters_require_aware_ordered_dates():
    with pytest.raises(ValueError, match="timezone-aware"):
        CustomerSupportDashboardFilters(started_at=datetime(2026, 7, 1))

    with pytest.raises(ValueError, match="must not be after"):
        CustomerSupportDashboardFilters(
            started_at=datetime(2026, 7, 28, tzinfo=UTC),
            ended_at=datetime(2026, 7, 27, tzinfo=UTC),
        )
