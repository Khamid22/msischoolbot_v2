"""Shared test setup.

These tests target *pure* logic (no live database). A couple of modules read
required env vars at import time (e.g. ``tgbot.settings`` -> ``config.get_settings``
needs BOT_TOKEN / MINI_APP_URL), so we seed safe placeholders before any test
imports run. ``DATABASE_URL`` is set so modules that build a connection string at
import don't raise; no test here actually opens a connection.
"""

import os

os.environ.setdefault("BOT_TOKEN", "123456:test-placeholder")
os.environ.setdefault("MINI_APP_URL", "https://example.com")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("DEMO_AUTH_ENABLED", "0")
