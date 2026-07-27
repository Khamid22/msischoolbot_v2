"""Customer Support operational dashboard transport."""

from __future__ import annotations

from enum import IntEnum
from typing import cast

from fastapi import APIRouter, Depends, Query, Request

from backend.application.container import AppContainer
from backend.application.customer_support import build_customer_support_dashboard
from backend.core.access import ActorContext, get_actor_context
from backend.core.api import ApiSuccess, api_error, api_success
from backend.modules.people.customer_support.dashboard.contracts import (
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardResponse,
    DashboardPeriodDays,
)
from backend.modules.people.customer_support.dashboard.queries import GetCustomerSupportDashboard
from backend.modules.people.customer_support.policies import CustomerSupportAccessError

router = APIRouter(prefix="/dashboard")


class DashboardPeriod(IntEnum):
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30
    NINETY_DAYS = 90


def get_dashboard_use_case(request: Request) -> GetCustomerSupportDashboard:
    container: AppContainer = request.app.state.container
    return build_customer_support_dashboard(container)


@router.get(
    "",
    response_model=ApiSuccess[CustomerSupportDashboardResponse],
    operation_id="api_v1_customer_support_dashboard",
)
def get_dashboard(
    period: DashboardPeriod = Query(default=DashboardPeriod.THIRTY_DAYS),
    school_id: int | None = Query(default=None, gt=0, alias="schoolId"),
    actor: ActorContext = Depends(get_actor_context),
    use_case: GetCustomerSupportDashboard = Depends(get_dashboard_use_case),
):
    try:
        response = use_case(
            actor,
            CustomerSupportDashboardFilters(
                period_days=cast(DashboardPeriodDays, int(period)),
                school_ids=frozenset({school_id}) if school_id is not None else frozenset(),
            ),
        )
    except (CustomerSupportAccessError, PermissionError) as exc:
        return api_error(str(exc), code="dashboard_scope_denied", status_code=403)
    except ValueError as exc:
        return api_error(str(exc), code="invalid_dashboard_filter", status_code=400)
    return api_success(response)


__all__ = ["get_dashboard_use_case", "router"]
