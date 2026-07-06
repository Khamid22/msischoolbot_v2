"""Lightweight page performance logging helpers."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any


LOGGER = logging.getLogger("msi.performance")


class PagePerformanceTimer:
    """Track coarse route timings without logging private payload data."""

    def __init__(self) -> None:
        now = time.perf_counter()
        self._start = now
        self._last = now
        self.timings: dict[str, float] = {}

    def mark(self, label: str) -> None:
        now = time.perf_counter()
        self.timings[f"{label}_ms"] = round((now - self._last) * 1000, 2)
        self._last = now

    def total_ms(self) -> float:
        return round((time.perf_counter() - self._start) * 1000, 2)


def row_count(value: Any) -> int:
    if isinstance(value, Mapping):
        return len(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return 0


def response_html_size(response: Any) -> int:
    body = getattr(response, "body", b"") or b""
    if isinstance(body, str):
        return len(body.encode("utf-8"))
    try:
        return len(body)
    except TypeError:
        return 0


def log_page_performance(
    route_name: str,
    timer: PagePerformanceTimer,
    *,
    response: Any = None,
    rows: Mapping[str, Any] | None = None,
) -> None:
    row_counts = {
        str(key): row_count(value)
        for key, value in (rows or {}).items()
    }
    LOGGER.info(
        "page_performance route=%s total_ms=%s timings=%s html_bytes=%s rows=%s",
        route_name,
        timer.total_ms(),
        timer.timings,
        response_html_size(response),
        row_counts,
    )


__all__ = [
    "PagePerformanceTimer",
    "log_page_performance",
    "response_html_size",
    "row_count",
]
