"""HR/CEO recruitment analytics API."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, get_current_user, require_role
from backend.core.api import api_success
from backend.modules.domains.reporting.recruitment import service


router = APIRouter(
    prefix="/hr/analytics",
    tags=["hr-recruitment-analytics"],
    dependencies=[Depends(require_role("hr_manager", "ceo"))],
)


def _call(operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return operation(*args, **kwargs)
    except service.HrAnalyticsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/options", operation_id="api_v1_hr_analytics_options")
def options(user: CurrentUser = Depends(get_current_user)):
    return api_success(_call(service.options, user))


@router.get("/dashboard", operation_id="api_v1_hr_analytics_dashboard")
def dashboard(
    period: str = "",
    date_from: str = "",
    date_to: str = "",
    source: str = "",
    subsource: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return api_success(
        _call(
            service.dashboard,
            user,
            period=period,
            date_from=date_from,
            date_to=date_to,
            source=source,
            subsource=subsource,
            position=position,
            subject_id=subject_id,
            responsible_account_id=responsible_account_id,
        )
    )


__all__ = ["router"]
