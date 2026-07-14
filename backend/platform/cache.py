"""Lazy shared Redis client; callers must retain a safe local fallback."""

from __future__ import annotations

import os
import threading


_CLIENT = None
_CLIENT_URL = ""
_LOCK = threading.Lock()


def get_redis_client():
    global _CLIENT, _CLIENT_URL
    redis_url = str(os.environ.get("REDIS_URL", "") or "").strip()
    if not redis_url:
        return None
    if _CLIENT is not None and _CLIENT_URL == redis_url:
        return _CLIENT
    with _LOCK:
        if _CLIENT is not None and _CLIENT_URL == redis_url:
            return _CLIENT
        import redis

        _CLIENT = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            health_check_interval=30,
        )
        _CLIENT_URL = redis_url
        return _CLIENT


__all__ = ["get_redis_client"]
