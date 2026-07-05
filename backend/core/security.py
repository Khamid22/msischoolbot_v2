"""Core security helpers for MSI LMS Portal."""

from __future__ import annotations

from typing import Any

from werkzeug.security import check_password_hash


def verify_password_hash(password_hash: Any, password: Any) -> bool:
    normalized_hash = str(password_hash or "").strip()
    if not normalized_hash:
        return False
    try:
        return bool(check_password_hash(normalized_hash, str(password or "")))
    except (TypeError, ValueError):
        return False


__all__ = ["verify_password_hash"]

