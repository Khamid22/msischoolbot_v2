"""Temporary compatibility wrapper for runtime configuration.

Configuration ownership lives in ``backend.core.runtime.config``. Keep this root module
until bot/web startup imports migrate fully to the core package path.

Temporary compatibility wrapper. Delete after all imports use
``backend.core.runtime.config``.
"""

from backend.core.runtime.config import Settings, WebSettings, get_settings, get_web_settings

__all__ = ["Settings", "WebSettings", "get_settings", "get_web_settings"]
