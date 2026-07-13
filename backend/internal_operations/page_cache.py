"""Shared cache helpers for admin page bootstrap context."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from backend.core.redis_client import get_redis_client


_ADMIN_PAGE_CONTEXT_CACHE_LOCK = threading.Lock()
_ADMIN_PAGE_CONTEXT_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}
_CACHE_VERSION_KEY = "msi:admin-page-context:version"
_LOCAL_CACHE_VERSION = "0"
_LAST_VERSION_CHECK_AT = 0.0


def _distributed_version(*, force=False) -> str:
    global _LOCAL_CACHE_VERSION, _LAST_VERSION_CHECK_AT
    now = time.monotonic()
    if not force and now - _LAST_VERSION_CHECK_AT < 1.0:
        return _LOCAL_CACHE_VERSION
    client = get_redis_client()
    if client is None:
        return _LOCAL_CACHE_VERSION
    try:
        version = str(client.get(_CACHE_VERSION_KEY) or "0")
    except Exception:
        return _LOCAL_CACHE_VERSION
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        if version != _LOCAL_CACHE_VERSION:
            _ADMIN_PAGE_CONTEXT_CACHE.clear()
            _LOCAL_CACHE_VERSION = version
        _LAST_VERSION_CHECK_AT = now
    return version


def invalidate_admin_page_context_cache() -> None:
    global _LOCAL_CACHE_VERSION, _LAST_VERSION_CHECK_AT
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        _ADMIN_PAGE_CONTEXT_CACHE.clear()
    client = get_redis_client()
    if client is not None:
        try:
            _LOCAL_CACHE_VERSION = str(client.incr(_CACHE_VERSION_KEY))
            _LAST_VERSION_CHECK_AT = time.monotonic()
        except Exception:
            pass


def admin_page_context_cache_ttl_seconds() -> int:
    raw_value = str(os.environ.get("ADMIN_PAGE_CONTEXT_CACHE_SECONDS", "15") or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 15
    return max(parsed, 0)


def get_cached_admin_page_context(cache_key: tuple[Any, ...]) -> Any | None:
    _distributed_version()
    now = time.time()
    with _ADMIN_PAGE_CONTEXT_CACHE_LOCK:
        cached_entry = _ADMIN_PAGE_CONTEXT_CACHE.get(cache_key)
        if cached_entry and now < float(cached_entry.get("expires_at", 0)):
            return cached_entry.get("context")
    return None


def set_cached_admin_page_context(cache_key: tuple[Any, ...], context: Any) -> None:
    _distributed_version()
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
