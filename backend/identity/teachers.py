"""Compatibility wrapper for teacher domain services.

Teacher service ownership moved to ``backend.domains.teachers.service`` in DB-2.
Keep this module temporarily so account-service and older imports continue to
work during the migration.
"""

from backend.domains.teachers.service import *  # noqa: F401,F403
from backend.domains.teachers.service import __all__ as __all__
