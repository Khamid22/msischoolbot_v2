"""Shared cache helpers for admin page bootstrap context."""

from __future__ import annotations

import os
import threading
import time
from typing import Any


_ADMIN_PAGE_CONTEXT_CACHE_LOCK = threading.Lock()
_ADMIN_PAGE_CONTEXT_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def invalidate_admin_page_context_cache() -> None:
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        _ADMIN_PAGE_CONTEXT_CACHE.clear()


def admin_page_context_cache_ttl_seconds() -> int:
    raw_value = str(os.environ.get("ADMIN_PAGE_CONTEXT_CACHE_SECONDS", "15") or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 15
    return max(parsed, 0)


def get_cached_admin_page_context(cache_key: tuple[Any, ...]) -> Any | None:
    now = time.time()
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        cached_entry = _ADMIN_PAGE_CONTEXT_CACHE.get(cache_key)
        if cached_entry and now < float(cached_entry.get("expires_at", 0)):
            return cached_entry.get("context")
    return None


def set_cached_admin_page_context(cache_key: tuple[Any, ...], context: Any) -> None:
    ttl_seconds = admin_page_context_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return

    now = time.time()
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        _ADMIN_PAGE_CONTEXT_CACHE[cache_key] = {
            "context": context,
            "expires_at": now + ttl_seconds,
        }
        expired_keys = [
            key
            for key, entry in _ADMIN_PAGE_CONTEXT_CACHE.items()
            if float(entry.get("expires_at", 0)) <= now
        ]
        for key in expired_keys:
            _ADMIN_PAGE_CONTEXT_CACHE.pop(key, None)
        if len(_ADMIN_PAGE_CONTEXT_CACHE) > 128:
            ordered_entries = sorted(
                _ADMIN_PAGE_CONTEXT_CACHE.items(),
                key=lambda item: float(item[1].get("expires_at", 0)),
            )
            for key, _entry in ordered_entries[: len(_ADMIN_PAGE_CONTEXT_CACHE) - 128]:
                _ADMIN_PAGE_CONTEXT_CACHE.pop(key, None)


__all__ = [
    "admin_page_context_cache_ttl_seconds",
    "get_cached_admin_page_context",
    "invalidate_admin_page_context_cache",
    "set_cached_admin_page_context",
]
