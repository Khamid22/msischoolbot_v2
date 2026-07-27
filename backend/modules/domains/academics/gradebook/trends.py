"""Gradebook trends operations."""

import re
from datetime import date

from backend.core.database import connect_auth_db
from backend.modules.domains.academics.gradebook import repository

def _gradebook_trend_month_range(through, months):
    through_text = str(through or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", through_text):
        raise ValueError("through must use YYYY-MM format.")
    try:
        through_month = date.fromisoformat(f"{through_text}-01")
    except ValueError as exc:
        raise ValueError("through must be a valid calendar month.") from exc

    try:
        month_count = int(months)
    except (TypeError, ValueError) as exc:
        raise ValueError("months must be a whole number from 3 to 12.") from exc
    if month_count < 3 or month_count > 12:
        raise ValueError("months must be between 3 and 12.")

    absolute_month = through_month.year * 12 + through_month.month - month_count
    start_year, start_month_zero = divmod(absolute_month, 12)
    start_month = date(start_year, start_month_zero + 1, 1)
    next_absolute_month = through_month.year * 12 + through_month.month
    next_year, next_month_zero = divmod(next_absolute_month, 12)
    end_month = date(next_year, next_month_zero + 1, 1)
    return start_month, through_month, end_month, month_count


def get_group_gradebook_trends(group_id, *, through, months=6):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required")
    start_month, through_month, end_month, month_count = _gradebook_trend_month_range(
        through, months
    )

    with connect_auth_db() as conn:
        group_row = repository.get_active_group_identity(conn, group_id)
        if not group_row:
            return None

        rows = repository.list_monthly_trend_rows(
            conn,
            group_id=int(group_row["id"]),
            school_id=int(group_row["school_id"]),
            start_month=start_month,
            through_month=through_month,
            end_month=end_month,
        )

    def optional_float(value):
        return None if value is None else float(value)

    trend_items = []
    for row in rows:
        month_start = row["month_start"]
        closure_titles = [str(value) for value in (row.get("closure_titles") or [])]
        trend_items.append({
            "month": month_start.strftime("%Y-%m"),
            "label": month_start.strftime("%b %Y"),
            "avgAAP": optional_float(row["avg_aap"]),
            "avgAR": optional_float(row["avg_ar"]),
            "avgPerformance": optional_float(row["avg_performance"]),
            "lessonCount": int(row["lesson_count"] or 0),
            "studentsWithData": int(row["students_with_data"] or 0),
            "homeworkRecordCount": int(row["homework_record_count"] or 0),
            "attendanceRecordCount": int(row["attendance_record_count"] or 0),
            "hasClosure": bool(closure_titles),
            "closureTitles": closure_titles,
        })

    return {
        "range": {
            "from": start_month.strftime("%Y-%m"),
            "through": through_month.strftime("%Y-%m"),
            "months": month_count,
        },
        "items": trend_items,
    }
