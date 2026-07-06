"""Compatibility wrapper for the previous account auth import path."""

from __future__ import annotations

import sys

from backend.identity import account_auth as _account_auth

globals().update(_account_auth.__dict__)
sys.modules[__name__] = _account_auth
