from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from app.config.schools import DEFAULT_SCHOOL_CODE, get_configured_school_spreadsheets

from .auth import SheetsDataError
from .constants import CACHE_TTL_SECONDS, WEBHOOK_CACHE_ENABLED, WEBHOOK_MAX_STALE_SECONDS
from .loader import load_from_google_sheets
from .utils import normalize_school_code


# Per-school-code cooperative lock that serializes all Google Sheets API calls.
# Using gevent.lock.Semaphore (falls back to threading.Lock) so the holder can
# yield during threadpool.spawn().get() without blocking the event loop, while
# still preventing concurrent httplib2 socket access which causes:
#   "This socket is already used by another greenlet"
_LOAD_LOCKS: dict[str, Any] = {}
_LOAD_LOCKS_META = threading.Lock()


def _get_load_lock(school_code: str) -> Any:
    with _LOAD_LOCKS_META:
        lock = _LOAD_LOCKS.get(school_code)
        if lock is None:
            try:
                from gevent.lock import Semaphore
                lock = Semaphore(1)
            except ImportError:
                lock = threading.Lock()
            _LOAD_LOCKS[school_code] = lock
        return lock


def _load_sheets_in_threadpool(school_code: str) -> dict:
    """Run load_from_google_sheets in gevent's thread pool.

    google-api-python-client uses httplib2 which does not cooperate with
    gevent's monkey-patched event loop even with patch_all().  Running the
    call inside a real OS thread (via gevent's threadpool) lets the event
    loop continue serving all other requests while waiting for Google Sheets.
    The calling greenlet suspends cooperatively until the thread finishes.
    """
    try:
        from gevent.hub import get_hub
        return get_hub().threadpool.spawn(load_from_google_sheets, school_code).get()
    except ImportError:
        return load_from_google_sheets(school_code)


@dataclass
class CacheEntry:
    dataset: dict[str, Any] | None = None
    expires_at: float = 0.0
    updated_at: float = 0.0
    dirty: bool = False


class SheetCache:
    def __init__(self):
        self._entries: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    @property
    def lock(self):
        return self._lock

    def get(self, school_code):
        entry = self._entries.get(school_code)
        if entry is None:
            return None
        return entry.dataset

    def get_last_updated(self, school_code):
        entry = self._entries.get(school_code)
        if entry is None:
            return None

        updated_at = float(entry.updated_at or 0.0)
        if updated_at <= 0:
            return None
        return updated_at

    def set(self, school_code, dataset, now):
        entry = self._entries.setdefault(school_code, CacheEntry())
        entry.dataset = dataset
        entry.updated_at = now
        entry.dirty = False
        entry.expires_at = now + CACHE_TTL_SECONDS

    def mark_dirty(self, school_code, clear_cached_data = False):
        entry = self._entries.setdefault(school_code, CacheEntry())
        entry.dirty = True
        entry.expires_at = 0.0
        if clear_cached_data:
            entry.dataset = None
            entry.updated_at = 0.0

    def is_fresh(self, school_code, now):
        entry = self._entries.get(school_code)
        if entry is None or not entry.dataset:
            return False

        if WEBHOOK_CACHE_ENABLED:
            if bool(entry.dirty):
                return False

            if WEBHOOK_MAX_STALE_SECONDS <= 0:
                return True

            updated_at = float(entry.updated_at or 0)
            if updated_at <= 0:
                return False
            return (now - updated_at) < WEBHOOK_MAX_STALE_SECONDS

        return now < float(entry.expires_at or 0)

    def keys(self):
        return list(self._entries.keys())


SHEET_CACHE = SheetCache()

# Tracks which schools are currently being revalidated in the background so we
# don't spawn duplicate refresh threads for the same school.
_REVALIDATING: set[str] = set()
_REVALIDATING_LOCK = threading.Lock()


def _revalidate_school(school_code: str) -> None:
    lock = _get_load_lock(school_code)
    lock.acquire()
    try:
        loaded_dataset = _load_sheets_in_threadpool(school_code)
        with SHEET_CACHE.lock:
            SHEET_CACHE.set(school_code, loaded_dataset, now=time.time())
    except Exception:
        return  # Keep existing stale data on failure
    finally:
        lock.release()


def _trigger_background_revalidation(school_code: str) -> None:
    """Kick off a one-shot background thread to refresh *school_code*.

    No-ops if a refresh is already in progress for that school.
    """
    with _REVALIDATING_LOCK:
        if school_code in _REVALIDATING:
            return
        _REVALIDATING.add(school_code)

    def _run() -> None:
        try:
            _revalidate_school(school_code)
        finally:
            with _REVALIDATING_LOCK:
                _REVALIDATING.discard(school_code)

    try:
        import gevent
        gevent.spawn(_run)
    except ImportError:
        threading.Thread(target=_run, daemon=True, name=f"sheets-revalidate-{school_code}").start()


def mark_school_dataset_dirty(school_codes = None, clear_cached_data = False):
    configured_codes = list(get_configured_school_spreadsheets().keys())

    if school_codes is None:
        target_codes = set(configured_codes)
    elif isinstance(school_codes, (list, tuple, set)):
        target_codes = {
            normalize_school_code(code)
            for code in school_codes
            if str(code or "").strip()
        }
    else:
        normalized_code = normalize_school_code(school_codes)
        target_codes = {normalized_code} if normalized_code else set()

    if not target_codes:
        target_codes = set(configured_codes)

    if not target_codes:
        target_codes = set(SHEET_CACHE.keys())

    with SHEET_CACHE.lock:
        for school_code in target_codes:
            SHEET_CACHE.mark_dirty(school_code, clear_cached_data=clear_cached_data)

    return sorted(target_codes)


def get_school_dataset(force_refresh = False, school_code = None):
    normalized_school_code = normalize_school_code(
        school_code
        or os.environ.get("ACTIVE_SCHOOL_CODE", DEFAULT_SCHOOL_CODE)
        or DEFAULT_SCHOOL_CODE
    )
    with SHEET_CACHE.lock:
        now = time.time()
        cached_dataset = SHEET_CACHE.get(normalized_school_code)
        if not force_refresh and SHEET_CACHE.is_fresh(normalized_school_code, now):
            return cached_dataset

    # Stale-while-revalidate: if we have any existing data (even stale), return
    # it immediately and refresh in the background so the next request is fresh.
    if not force_refresh and cached_dataset is not None:
        _trigger_background_revalidation(normalized_school_code)
        return cached_dataset

    # No data at all (cold start or force_refresh): serialize via per-school lock.
    # Multiple concurrent greenlets may reach this point simultaneously.  Only
    # the first one actually calls the Sheets API; the rest wait cooperatively
    # and then return from cache once the leader finishes.
    load_lock = _get_load_lock(normalized_school_code)
    load_lock.acquire()
    try:
        # Re-check cache — another greenlet may have loaded while we waited.
        if not force_refresh:
            with SHEET_CACHE.lock:
                now = time.time()
                cached_dataset = SHEET_CACHE.get(normalized_school_code)
                if cached_dataset is not None:
                    return cached_dataset

        try:
            loaded_dataset = _load_sheets_in_threadpool(normalized_school_code)
        except SheetsDataError:
            with SHEET_CACHE.lock:
                fallback_dataset = SHEET_CACHE.get(normalized_school_code)
                if fallback_dataset:
                    return fallback_dataset
            raise

        with SHEET_CACHE.lock:
            now = time.time()
            cached_dataset = SHEET_CACHE.get(normalized_school_code)
            if not force_refresh and SHEET_CACHE.is_fresh(normalized_school_code, now):
                return cached_dataset
            SHEET_CACHE.set(normalized_school_code, loaded_dataset, now=now)
            return loaded_dataset
    finally:
        load_lock.release()


def get_school_dataset_last_updated(school_code = None):
    normalized_school_code = normalize_school_code(
        school_code
        or os.environ.get("ACTIVE_SCHOOL_CODE", DEFAULT_SCHOOL_CODE)
        or DEFAULT_SCHOOL_CODE
    )
    with SHEET_CACHE.lock:
        return SHEET_CACHE.get_last_updated(normalized_school_code)
