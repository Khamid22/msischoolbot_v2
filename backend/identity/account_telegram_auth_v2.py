"""Compatibility wrapper for the previous account Telegram auth import path."""

from __future__ import annotations

import sys

from backend.identity import account_telegram_auth as _account_telegram_auth

globals().update(_account_telegram_auth.__dict__)
sys.modules[__name__] = _account_telegram_auth
