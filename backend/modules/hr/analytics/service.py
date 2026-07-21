"""Role-scoped recruitment analytics use cases."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from backend.core.access import CurrentUser
from backend.core.database import connect_auth_db
from backend.modules.hr.analytics import repository


TASHKENT = ZoneInfo("Asia/Tashkent")
ANALYTICS_ROLES = frozenset({"hr_manager", "ceo"})
PERIODS = frozenset({"today", "week", "month", "quarter", "year", "custom"})
OUTCOMES = ("teacher_academy", "active_teacher", "rejected", "candidate_withdrew")


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


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise HrAnalyticsError(f"{field} must use YYYY-MM-DD.") from exc


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _month_end(value: date) -> date:
    return value.replace(day=monthrange(value.year, value.month)[1])


def _previous_month(value: date) -> date:
    return (value.replace(day=1) - timedelta(days=1)).replace(day=1)


def _period_bounds(
    *,
    today: date,
    period: str,
    date_from: str,
    date_to: str,
) -> tuple[date, date, date, date, str]:
    normalized = (period or "").strip().lower()
    if date_from or date_to:
        normalized = "custom"
    if normalized not in PERIODS:
        raise HrAnalyticsError("Analytics period must be today, week, month, quarter, year, or custom.")

    if normalized == "custom":
        if not date_from or not date_to:
            raise HrAnalyticsError("Custom analytics ranges require both start and end dates.")
        start = _parse_date(date_from, field="Analytics start date")
        end = _parse_date(date_to, field="Analytics end date")
        if end > today:
            raise HrAnalyticsError("Analytics end date cannot be in the future.")
    elif normalized == "today":
        start = end = today
    elif normalized == "week":
        start = today - timedelta(days=today.weekday())
        end = today
    elif normalized == "month":
        start = _month_start(today)
        end = today
    elif normalized == "quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, quarter_month, 1)
        end = today
    else:
        start = date(today.year, 1, 1)
        end = today

    if start > end:
        raise HrAnalyticsError("The start date cannot be after the end date.")
    if (end - start).days > 3660:
        raise HrAnalyticsError("Analytics date range cannot exceed ten years.")

    if normalized == "today":
        comparison_start = comparison_end = start - timedelta(days=1)
    elif normalized == "week":
        comparison_start = start - timedelta(days=7)
        comparison_end = end - timedelta(days=7)
    elif normalized == "month":
        comparison_start = _previous_month(start)
        comparison_end = comparison_start.replace(
            day=min(end.day, monthrange(comparison_start.year, comparison_start.month)[1])
        )
    elif normalized == "quarter":
        prior_quarter_end = start - timedelta(days=1)
        comparison_start = date(
            prior_quarter_end.year,
            ((prior_quarter_end.month - 1) // 3) * 3 + 1,
            1,
        )
        comparison_end = min(
            comparison_start + (end - start),
            prior_quarter_end,
        )
    elif normalized == "year":
        comparison_start = date(start.year - 1, 1, 1)
        comparison_end = date(
            start.year - 1,
            end.month,
            min(end.day, monthrange(start.year - 1, end.month)[1]),
        )
    else:
        span = end - start
        comparison_end = start - timedelta(days=1)
        comparison_start = comparison_end - span

    return start, end, comparison_start, comparison_end, normalized


def _bucket_for(start: date, end: date) -> str:
    days = (end - start).days + 1
    if days <= 31:
        return "day"
    if days <= 180:
        return "week"
    return "month"


def _bucket_start(value: date, bucket: str) -> date:
    if bucket == "week":
        return value - timedelta(days=value.weekday())
    if bucket == "month":
        return value.replace(day=1)
    return value


def _next_bucket(value: date, bucket: str) -> date:
    if bucket == "day":
        return value + timedelta(days=1)
    if bucket == "week":
        return value + timedelta(days=7)
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _trend(rows: list[Any], *, start: date, end: date, bucket: str) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        item = _dict(row)
        counts[(str(item["bucket"]), str(item["event_type"]))] = int(item["candidates"] or 0)
    result: list[dict[str, Any]] = []
    cursor = _bucket_start(start, bucket)
    final_bucket = _bucket_start(end, bucket)
    while cursor <= final_bucket:
        key = cursor.isoformat()
        result.append(
            {
                "bucket": key,
                "applications": counts.get((key, "applications"), 0),
                "shortlisted": counts.get((key, "shortlisted"), 0),
                "hired": counts.get((key, "hired"), 0),
                "rejected": counts.get((key, "rejected"), 0),
            }
        )
        cursor = _next_bucket(cursor, bucket)
    return result


def _comparison_metric(current: Any, previous: Any) -> dict[str, Any]:
    current_value = float(current or 0)
    previous_value = float(previous or 0)
    delta = None
    if previous_value:
        delta = round((current_value - previous_value) / previous_value * 100, 1)
    return {
        "value": int(current_value),
        "previous": int(previous_value),
        "delta_percentage": delta,
    }


def options(user: CurrentUser) -> dict[str, Any]:
    _ensure_access(user)
    with connect_auth_db() as conn:
        rows = repository.options_rows(conn)
    positions = [_dict(row) for row in rows["positions"]]
    return {
        "sources": [_dict(row) for row in rows["sources"]],
        "subsources": [_dict(row) for row in rows["subsources"]],
        # Retain the original string list while exposing immutable IDs to the new UI.
        "positions": [str(row["label"]) for row in positions],
        "position_options": positions,
        "subjects": [_dict(row) for row in rows["subjects"]],
        "responsible_people": [_dict(row) for row in rows["responsible_people"]],
    }


def dashboard(
    user: CurrentUser,
    *,
    period: str = "",
    date_from: str = "",
    date_to: str = "",
    source: str = "",
    subsource: str = "",
    position: str = "",
    subject_id: int | None = None,
    responsible_account_id: int | None = None,
) -> dict[str, Any]:
    _ensure_access(user)
    today = datetime.now(TASHKENT).date()
    selected_period = period.strip().lower() or ("month" if user.role == "hr_manager" else "year")
    start, end, comparison_start, comparison_end, selected_period = _period_bounds(
        today=today,
        period=selected_period,
        date_from=date_from,
        date_to=date_to,
    )
    bucket = _bucket_for(start, end)
    now = datetime.now(UTC).isoformat()
    with connect_auth_db() as conn:
        if subsource and not source:
            raise HrAnalyticsError("Select a source before selecting a subsource.")
        if subsource:
            try:
                source_id = int(source)
                subsource_id = int(subsource)
            except (TypeError, ValueError) as exc:
                raise HrAnalyticsError(
                    "Source and subsource filters must use configured option IDs."
                ) from exc
            if not repository.subsource_matches_source(
                conn,
                source_id=source_id,
                subsource_id=subsource_id,
            ):
                raise HrAnalyticsError(
                    "The selected subsource does not belong to the selected source."
                )
        rows = repository.dashboard_rows(
            conn,
            date_from=start.isoformat(),
            date_to=end.isoformat(),
            comparison_from=comparison_start.isoformat(),
            comparison_to=comparison_end.isoformat(),
            bucket=bucket,
            now=now,
            source=source.strip(),
            subsource=subsource.strip(),
            position=position.strip(),
            subject_id=subject_id,
            responsible_account_id=responsible_account_id,
        )

    current = _dict(rows["current_summary"])
    comparison = _dict(rows["comparison_summary"])
    all_time = _dict(rows["total_summary"])
    events = _dict(rows["event_summary"])
    comparison_events = _dict(rows["comparison_event_summary"])
    all_time_events = _dict(rows["total_event_summary"])
    live = _dict(rows["live_summary"])
    stage_time = [_dict(row) for row in rows["time_in_stage"]]
    journey: list[dict[str, Any]] = []
    previous_count: int | None = None
    for row in rows["journey"]:
        stage_row = _dict(row)
        stage = str(stage_row["stage"])
        count = int(stage_row["candidates"] or 0)
        journey.append(
            {
                "stage": stage,
                "stage_label": str(stage_row.get("stage_label") or stage),
                "color_token": str(stage_row.get("color_token") or "neutral"),
                "candidates": count,
                "previous_stage_candidates": previous_count,
                "conversion_percentage": (
                    round(count / previous_count * 100, 1)
                    if previous_count
                    else None
                ),
            }
        )
        previous_count = count

    outcome_counts = {
        str(row["outcome"]): int(row["candidates"] or 0)
        for row in rows["outcomes"]
    }
    outcomes = [
        {"outcome": outcome, "candidates": outcome_counts.get(outcome, 0)}
        for outcome in OUTCOMES
    ]

    source_quality = [_dict(row) for row in rows["source_quality"]]
    source_totals: dict[str, dict[str, Any]] = {}
    for item in source_quality:
        source_name = str(item["source"])
        source_total = source_totals.setdefault(
            source_name,
            {"source": source_name, "candidates": 0, "shortlisted": 0, "hired": 0},
        )
        source_total["candidates"] += int(item.get("candidates") or 0)
        source_total["shortlisted"] += int(item.get("shortlisted") or 0)
        source_total["hired"] += int(item.get("hired") or 0)
    application_total = int(current.get("applications") or 0)
    source_distribution = sorted(
        (
            {
                **item,
                "percentage": round(item["candidates"] / application_total * 100, 1)
                if application_total
                else 0,
            }
            for item in source_totals.values()
        ),
        key=lambda item: (-item["candidates"], item["source"]),
    )
    source_conversion = [
        {
            "source": item["source"],
            "candidates": item["candidates"],
            "hired": item["hired"],
            "conversion_percentage": (
                round(item["hired"] / item["candidates"] * 100, 1)
                if item["candidates"]
                else 0
            ),
        }
        for item in source_distribution
    ]

    return {
        "role": user.role,
        "as_of": now,
        "range": {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "timezone": "Asia/Tashkent",
            "period": selected_period,
            "comparison_from": comparison_start.isoformat(),
            "comparison_to": comparison_end.isoformat(),
            "bucket": bucket,
        },
        "filters": {
            "source": source,
            "subsource": subsource,
            "position": position,
            "subject_id": subject_id,
            "responsible_account_id": responsible_account_id,
        },
        "summary_cards": {
            key: {
                **_comparison_metric(events.get(key), comparison_events.get(key)),
                "total": int(all_time_events.get(key) or 0),
            }
            for key in (
                "applications",
                "final_decision",
                "teacher_academy",
                "active_teachers",
                "rejected",
            )
        },
        "evaluation_kpis": {
            kind: {
                "total": int(events.get(f"{kind}_total") or 0),
                "unique_candidates": int(
                    events.get(f"{kind}_unique_candidates") or 0
                ),
                "passed": int(events.get(f"{kind}_passed") or 0),
                "failed": int(events.get(f"{kind}_failed") or 0),
                "pass_rate": (
                    round(
                        int(events.get(f"{kind}_passed") or 0)
                        / int(events.get(f"{kind}_unique_candidates") or 0)
                        * 100,
                        1,
                    )
                    if int(events.get(f"{kind}_unique_candidates") or 0)
                    else 0
                ),
            }
            for kind in ("interview", "demo", "subject_test")
        },
        "secondary_kpis": {
            "academy_accepted": int(events.get("teacher_academy") or 0),
            "academy_total": int(live.get("academy_roster_total") or 0),
            "active_teacher_total": int(
                live.get("active_teacher_roster_total") or 0
            ),
            "withdrawn": int(events.get("withdrawn") or 0),
            "withdrawn_total": int(all_time_events.get("withdrawn") or 0),
            "active_candidates": int(live.get("active_candidates") or 0),
            "average_time_to_hire_days": current.get("average_time_to_hire_days"),
            "overall_conversion_percentage": current.get("overall_conversion_percentage"),
            # Keep the legacy field while exposing explicit live/cohort scopes.
            "sla_breaches": int(live.get("sla_overdue_now") or 0),
            "sla_overdue_now": int(live.get("sla_overdue_now") or 0),
            "cohort_sla_breaches": int(current.get("cohort_sla_breaches") or 0),
        },
        # Compatibility for clients using the first analytics contract.
        "kpis": {
            "active_candidates": int(live.get("active_candidates") or 0),
            "new_this_month": int(current.get("applications") or 0),
            "hired_this_month": int(current.get("hired") or 0),
            "average_time_to_hire_days": current.get("average_time_to_hire_days"),
            "overall_conversion_percentage": current.get("overall_conversion_percentage"),
        },
        "funnel": journey,
        "journey": journey,
        "outcomes": outcomes,
        "activity_trend": _trend(
            rows["activity_trend"],
            start=start,
            end=end,
            bucket=bucket,
        ),
        "position_distribution": [_dict(row) for row in rows["position_distribution"]],
        "source_distribution": source_distribution,
        "source_quality": source_quality,
        "source_conversion": source_conversion,
        "time_in_stage": stage_time,
        "sla": {
            "breaches": int(current.get("cohort_sla_breaches") or 0),
            "overdue_now": int(live.get("sla_overdue_now") or 0),
            "bottlenecks": stage_time[:3],
        },
        "overdue_actions": [_dict(row) for row in rows["overdue_actions"]],
        "upcoming_appointments": [_dict(row) for row in rows["upcoming_appointments"]],
        "recent_candidates": [_dict(row) for row in rows["recent_candidates"]],
        "recent_activity": [_dict(row) for row in rows["recent_activity"]],
    }


__all__ = ["HrAnalyticsError", "dashboard", "options"]
