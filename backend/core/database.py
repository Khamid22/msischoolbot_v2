"""Database compatibility helpers for MSI LMS Portal.

This module is a future core import path only. Runtime code can continue using
legacy imports while refactor phases gradually move database access here.
"""

from backend.identity.common import connect

__all__ = ["connect"]
