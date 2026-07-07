"""Compatibility wrapper for student domain queries.

Student query ownership moved to ``backend.domains.students.queries`` in DB-3.
Keep this module temporarily so older imports continue to work while callers
migrate to the student domain package.

Temporary compatibility wrapper. Delete after student dashboard imports migrate
to ``backend.domains.students.queries``.
"""

from backend.domains.students.queries import *  # noqa: F401,F403
from backend.domains.students.queries import __all__ as __all__
