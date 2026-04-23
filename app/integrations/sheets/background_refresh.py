from __future__ import annotations

import logging
import os
import threading
import time

from app.config.schools import get_configured_school_spreadsheets

from .cache import SHEET_CACHE, get_school_dataset
from .constants import CACHE_TTL_SECONDS, WEBHOOK_CACHE_ENABLED

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60

REFRESH_AHEAD_SECONDS = max(120, CACHE_TTL_SECONDS // 5)

_started = False
_start_lock = threading.Lock()


def _is_startup_prewarm_enabled() -> bool:
    raw = str(os.environ.get("SHEETS_STARTUP_PREWARM", "1") or "").strip()
    return raw.casefold() not in {"0", "false", "no", "off"}


def _prewarm_cache() -> None:
    configured_codes = list(get_configured_school_spreadsheets().keys())
    if not configured_codes:
        return

    for school_code in configured_codes:
        with SHEET_CACHE.school_lock(school_code):
            cached = SHEET_CACHE.get(school_code)
        if cached is not None:
            continue

        logger.info("Startup pre-warm: loading '%s' from Google Sheets", school_code)
        try:
            get_school_dataset(force_refresh=False, school_code=school_code)
            logger.info("Startup pre-warm: '%s' ready", school_code)
        except Exception as exc:
            logger.warning("Startup pre-warm: failed to load '%s': %s", school_code, exc)


def _refresh_loop() -> None:
    while True:
        try:
            _refresh_stale_schools()
        except Exception:
            logger.exception("Background Sheets refresh: unexpected error")

        time.sleep(CHECK_INTERVAL_SECONDS)


def _refresh_stale_schools() -> None:
    if WEBHOOK_CACHE_ENABLED:
        return

    configured_codes = list(get_configured_school_spreadsheets().keys())
    if not configured_codes:
        return

    now = time.time()
    for school_code in configured_codes:
        with SHEET_CACHE.school_lock(school_code):
            entry = SHEET_CACHE._entries.get(school_code)

        if entry is None or not entry.dataset:
            continue

        expires_at = float(entry.expires_at or 0)
        time_until_expiry = expires_at - now

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
    global _started
    with _start_lock:
        if _started:
            return
        _started = True

    # Always run in native daemon threads. Running Sheets I/O in gevent greenlets
    # can block the hub in environments where DNS/network calls are not fully
    # cooperative, which stalls the web server.
    if _is_startup_prewarm_enabled():
        threading.Thread(
            target=_prewarm_cache,
            name="sheets-cache-prewarm",
            daemon=True,
        ).start()
    threading.Thread(
        target=_refresh_loop,
        name="sheets-cache-refresh",
        daemon=True,
    ).start()

    logger.info(
        "Background Sheets refresh started (check_interval=%ss, refresh_ahead=%ss, prewarm=%s)",
        CHECK_INTERVAL_SECONDS,
        REFRESH_AHEAD_SECONDS,
        _is_startup_prewarm_enabled(),
    )
