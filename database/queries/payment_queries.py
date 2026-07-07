"""Compatibility wrapper for payment domain queries.

Payment query ownership moved to ``backend.domains.payments.queries``.

Temporary compatibility wrapper. Delete after payment imports migrate to
``backend.domains.payments.queries``.
"""

from backend.domains.payments.queries import *  # noqa: F401,F403
from backend.domains.payments.queries import __all__ as __all__
