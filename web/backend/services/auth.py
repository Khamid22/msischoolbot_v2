# Canonical implementation moved to shared/auth.py (framework-free, shared by the
# web backend and the Telegram bot). Kept as a shim so existing
# `from web.backend.services.auth import ...` call sites keep working.
from common.auth import *  # noqa: F401,F403
