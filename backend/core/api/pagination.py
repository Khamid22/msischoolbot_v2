"""Shared pagination policy for new collection endpoints."""

from __future__ import annotations

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def normalize_page_size(
    value: int | None,
    *,
    default: int = DEFAULT_PAGE_SIZE,
    maximum: int = MAX_PAGE_SIZE,
) -> int:
    if value is None:
        return default
    return min(max(1, int(value)), maximum)


__all__ = ["DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE", "normalize_page_size"]
