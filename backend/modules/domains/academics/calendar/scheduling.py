"""Shared teaching-date helpers for recurring academic schedules."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Mapping


def closure_ranges(rows: Iterable[Mapping]) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    for row in rows:
        start = row.get("start_date")
        end = row.get("end_date")
        if isinstance(start, date) and isinstance(end, date) and end >= start:
            ranges.append((start, end))
    return ranges


def date_is_closed(value: date, ranges: Iterable[tuple[date, date]]) -> bool:
    return any(start <= value <= end for start, end in ranges)


def generate_teaching_dates(
    *,
    start_date: date,
    count: int,
    weekdays: Iterable[int],
    blocked_dates: Iterable[date] = (),
    closures: Iterable[tuple[date, date]] = (),
    end_date: date | None = None,
) -> list[date]:
    """Return valid recurring teaching dates without expanding closure ranges."""

    wanted = {int(day) for day in weekdays if 0 <= int(day) <= 6}
    if not wanted:
        raise ValueError("Select at least one weekday.")
    requested = max(0, int(count or 0))
    blocked = {value for value in blocked_dates if isinstance(value, date)}
    closed = list(closures)
    result: list[date] = []
    cursor = start_date
    safety_limit = start_date + timedelta(days=3660)
    while (requested <= 0 or len(result) < requested) and cursor <= safety_limit:
        if end_date is not None and cursor > end_date:
            break
        if (
            cursor.weekday() in wanted
            and cursor not in blocked
            and not date_is_closed(cursor, closed)
        ):
            result.append(cursor)
        cursor += timedelta(days=1)
    if requested > 0 and len(result) < requested:
        raise ValueError("The timetable could not find enough teaching dates outside school breaks.")
    return result


__all__ = ["closure_ranges", "date_is_closed", "generate_teaching_dates"]
