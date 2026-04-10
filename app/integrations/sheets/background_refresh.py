"""Background thread that pre-warms the Google Sheets cache before it expires.

This prevents any user-facing request from ever blocking on a cold cache miss.
The thread wakes up every CHECK_INTERVAL_SECONDS and refreshes any school whose
cache will expire within REFRESH_AHEAD_SECONDS.
"""
from __future__ import annotations

import logging
import threading
import time

from app.config.schools import get_configured_school_spreadsheets

from .cache import SHEET_CACHE, get_school_dataset
from .constants import CACHE_TTL_SECONDS, WEBHOOK_CACHE_ENABLED

logger = logging.getLogger(__name__)

# How often the background thread checks whether a refresh is needed.
CHECK_INTERVAL_SECONDS = 60

# Refresh the cache this many seconds before it would actually expire.
# E.g. with a 600s TTL and 120s ahead, refresh happens at ~480s.
REFRESH_AHEAD_SECONDS = max(120, CACHE_TTL_SECONDS // 5)

_started = False
_start_lock = threading.Lock()


def _refresh_loop() -> None:
    # Wait a bit after startup so the first real request can warm the cache
    # naturally; the background thread then takes over from there.
    time.sleep(30)

    while True:
        try:
            _refresh_stale_schools()
        except Exception:
            logger.exception("Background Sheets refresh: unexpected error")

        time.sleep(CHECK_INTERVAL_SECONDS)


def _refresh_stale_schools() -> None:
    # In webhook mode the cache stays valid indefinitely until a webhook fires,
    # so background polling would just waste quota.
    if WEBHOOK_CACHE_ENABLED:
        return

    configured_codes = list(get_configured_school_spreadsheets().keys())
    if not configured_codes:
        return

    now = time.time()
    for school_code in configured_codes:
        with SHEET_CACHE.lock:
            entry = SHEET_CACHE._entries.get(school_code)

        if entry is None or not entry.dataset:
            # Cache is completely empty — let the first user request warm it.
            continue

        expires_at = float(entry.expires_at or 0)
        time_until_expiry = expires_at - now

        # Refresh if cache will expire within REFRESH_AHEAD_SECONDS.
        if time_until_expiry < REFRESH_AHEAD_SECONDS:
            logger.info(
                "Background refresh: refreshing '%s' (expires in %.0fs)",
                school_code,
                max(time_until_expiry, 0),
            )
            try:
                get_school_dataset(force_refresh=True, school_code=school_code)
                logger.info("Background refresh: '%s' refreshed successfully", school_code)
            except Exception as exc:
                logger.warning(
                    "Background refresh: failed to refresh '%s': %s",
                    school_code,
                    exc,
                )


def start_background_refresh() -> None:
    """Start the background cache-refresh daemon thread (idempotent)."""
    global _started
    with _start_lock:
        if _started:
            return
        _started = True

    thread = threading.Thread(
        target=_refresh_loop,
        name="sheets-cache-refresh",
        daemon=True,
    )
    thread.start()
    logger.info(
        "Background Sheets cache refresh started "
        "(check every %ds, refresh %ds ahead of expiry)",
        CHECK_INTERVAL_SECONDS,
        REFRESH_AHEAD_SECONDS,
    )
