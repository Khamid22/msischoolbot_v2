"""Role-scoped recruitment analytics use cases."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.hr.analytics import repository


TASHKENT = ZoneInfo("Asia/Tashkent")
ANALYTICS_ROLES = frozenset({"hr_manager", "ceo"})


class HrAnalyticsError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _ensure_access(user: CurrentUser) -> None:
    if user.role not in ANALYTICS_ROLES:
        raise HrAnalyticsError("HR analytics require HR Manager or CEO access.", status_code=403)


def _dict(row: Any) -> dict[str, Any]:
    result = dict(row or {})
    for key, value in list(result.items()):
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
    return result


def _parse_date(value: str, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HrAnalyticsError("Analytics dates must use YYYY-MM-DD.") from exc


def options(user: CurrentUser) -> dict[str, Any]:
    _ensure_access(user)
    with connect_auth_db() as conn:
        rows = repository.options_rows(conn)
    return {
        "sources": [str(row["value"]) for row in rows["sources"]],
        "positions": [str(row["value"]) for row in rows["positions"]],
        "subjects": [_dict(row) for row in rows["subjects"]],
        "responsible_people": [_dict(row) for row in rows["responsible_people"]],
    }


def dashboard(
    user: CurrentUser,
    *,
    date_from: str = "",
    date_to: str = "",
    source: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
) -> dict[str, Any]:
    _ensure_access(user)
    today = datetime.now(TASHKENT).date()
    end = _parse_date(date_to, today)
    start = _parse_date(date_from, end - timedelta(days=365))
    if start > end:
        raise HrAnalyticsError("The start date cannot be after the end date.")
    if (end - start).days > 3660:
        raise HrAnalyticsError("Analytics date range cannot exceed ten years.")
    month_from = today.replace(day=1)
    month_to = (month_from.replace(day=28) + timedelta(days=4)).replace(day=1)
    now = datetime.now(UTC).isoformat()
    with connect_auth_db() as conn:
        rows = repository.dashboard_rows(
            conn,
            date_from=start.isoformat(),
            date_to=end.isoformat(),
            month_from=month_from.isoformat(),
            month_to=month_to.isoformat(),
            now=now,
            source=source.strip(),
            position=position.strip(),
            subject_id=subject_id,
            responsible_account_id=responsible_account_id,
        )
    stage_time = [_dict(row) for row in rows["time_in_stage"]]
    funnel_counts = {str(row["stage"]): int(row["candidates"] or 0) for row in rows["funnel"]}
    funnel_order = (
        "new_candidate", "responded", "job_interview", "test_and_demo",
        "under_review", "teacher_academy", "active_teacher",
    )
    funnel: list[dict[str, Any]] = []
    previous_count: int | None = None
    for stage in funnel_order:
        count = funnel_counts.get(stage, 0)
        funnel.append(
            {
                "stage": stage,
                "candidates": count,
                "previous_stage_candidates": previous_count,
                "conversion_percentage": (
                    round(count / previous_count * 100, 1)
                    if previous_count and previous_count > 0
                    else None
                ),
            }
        )
        previous_count = count
    return {
        "range": {"from": start.isoformat(), "to": end.isoformat(), "timezone": "Asia/Tashkent"},
        "filters": {
            "source": source,
            "position": position,
            "subject_id": subject_id,
            "responsible_account_id": responsible_account_id,
        },
        "kpis": _dict(rows["kpis"]),
        "funnel": funnel,
        "source_conversion": [_dict(row) for row in rows["source_conversion"]],
        "time_in_stage": stage_time,
        "sla": {
            "breaches": sum(int(item.get("sla_breaches") or 0) for item in stage_time),
            "bottlenecks": stage_time[:3],
        },
        "overdue_actions": [_dict(row) for row in rows["overdue_actions"]],
        "upcoming_appointments": [_dict(row) for row in rows["upcoming_appointments"]],
    }


__all__ = ["HrAnalyticsError", "dashboard", "options"]
