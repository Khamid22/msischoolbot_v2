"""Compatibility wrapper for teacher domain queries.

Teacher query ownership moved to ``backend.domains.teachers.queries`` in DB-2.
Keep this module temporarily so older imports continue to work while callers
migrate to the teacher domain package.

Temporary compatibility wrapper. Delete after tests and Teacher Academy helpers
import ``backend.domains.teachers.queries`` directly.
"""

from backend.domains.teachers.queries import *  # noqa: F401,F403
from backend.domains.teachers.queries import __all__ as __all__
