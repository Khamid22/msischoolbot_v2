"""Core runtime configuration helpers for MSI LMS Portal.

The repository root still exposes ``config.py`` for existing bot/web imports.
New backend modules should prefer this package path.
"""

from __future__ import annotations

from config import Settings, WebSettings, get_settings, get_web_settings

__all__ = ["Settings", "WebSettings", "get_settings", "get_web_settings"]
