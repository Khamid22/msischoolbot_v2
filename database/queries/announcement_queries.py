"""Compatibility wrapper for announcement domain queries.

Announcement query ownership moved to ``backend.domains.announcements.queries``
in DB-5. Keep this module temporarily so older imports continue to work while
callers migrate to the announcement domain package.

Temporary compatibility wrapper. Delete after announcement imports migrate to
``backend.domains.announcements.queries``.
"""

from backend.domains.announcements.queries import *  # noqa: F401,F403
from backend.domains.announcements.queries import __all__ as __all__
