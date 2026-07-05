"""Core runtime configuration helpers for MSI LMS Portal."""

from __future__ import annotations

import os


ACCOUNT_AUTH_V2_TRUE_VALUES = {"1", "true", "yes", "on"}


def account_auth_v2_enabled() -> bool:
    raw_value = str(os.environ.get("ACCOUNT_AUTH_V2_ENABLED", "") or "").strip().casefold()
    return raw_value in ACCOUNT_AUTH_V2_TRUE_VALUES


__all__ = [
    "ACCOUNT_AUTH_V2_TRUE_VALUES",
    "account_auth_v2_enabled",
]

