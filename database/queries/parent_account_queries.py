"""Compatibility wrapper for parent domain account queries.

Parent query ownership moved to ``backend.domains.parents.queries`` in DB-4.
Keep this module temporarily so older imports continue to work while callers
migrate to the parent domain package.

Temporary compatibility wrapper. Delete after parent account imports migrate to
``backend.domains.parents.queries``.
"""

from backend.domains.parents.queries import *  # noqa: F401,F403
from backend.domains.parents.queries import __all__ as __all__
