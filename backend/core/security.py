"""Core security helpers for MSI LMS Portal."""

from __future__ import annotations

from typing import Any

# Stored hashes are Werkzeug-format, so verification must stay compatible with
# existing rows until the credential storage format changes deliberately.
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
