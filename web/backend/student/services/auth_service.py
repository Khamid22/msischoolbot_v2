# Canonical auth logic lives in web/backend/services/auth.py. This module used
# to hold a forked copy that had diverged only in admin-only and dead code; it
# is now a thin re-export so the student/bot path and the admin path share one
# implementation.
from web.backend.services.auth import *  # noqa: F401,F403
