"""Shared time vocabulary for business modules."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

SCHOOL_TIMEZONE_NAME = "Asia/Tashkent"
SCHOOL_TIMEZONE = ZoneInfo(SCHOOL_TIMEZONE_NAME)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def school_now() -> datetime:
    """Return the current timestamp in the configured school timezone."""

    return utc_now().astimezone(SCHOOL_TIMEZONE)


__all__ = ["SCHOOL_TIMEZONE", "SCHOOL_TIMEZONE_NAME", "school_now", "utc_now"]
