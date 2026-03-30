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

    # Never hold the global cache lock during remote I/O.
    try:
        loaded_dataset = load_from_google_sheets(normalized_school_code)
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


def get_school_dataset_last_updated(school_code = None):
    normalized_school_code = normalize_school_code(
        school_code
        or os.environ.get("ACTIVE_SCHOOL_CODE", DEFAULT_SCHOOL_CODE)
        or DEFAULT_SCHOOL_CODE
    )
    with SHEET_CACHE.lock:
        return SHEET_CACHE.get_last_updated(normalized_school_code)
