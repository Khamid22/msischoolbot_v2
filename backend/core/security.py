"""Core security helpers for MSI LMS Portal."""

from __future__ import annotations

from typing import Any

# The only module allowed to import werkzeug hashing: stored hashes are
# werkzeug-format, so verification must stay compatible with existing rows.
from werkzeug.security import check_password_hash, generate_password_hash as _werkzeug_generate


def verify_password_hash(password_hash: Any, password: Any) -> bool:
    normalized_hash = str(password_hash or "").strip()
    if not normalized_hash:
        return False
    try:
        return bool(check_password_hash(normalized_hash, str(password or "")))
    except (TypeError, ValueError):
        return False


def generate_password_hash(password: Any) -> str:
    return _werkzeug_generate(str(password or ""))


__all__ = ["verify_password_hash", "generate_password_hash"]

