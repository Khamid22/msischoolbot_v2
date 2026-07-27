"""Application-owned rate limiter construction."""

from slowapi import Limiter
from slowapi.util import get_remote_address


def create_limiter(redis_url: str = "") -> Limiter:
    """Create an isolated limiter for one application container."""

    return Limiter(
        key_func=get_remote_address,
        storage_uri=str(redis_url or "").strip() or "memory://",
        swallow_errors=True,
    )


__all__ = ["create_limiter"]
