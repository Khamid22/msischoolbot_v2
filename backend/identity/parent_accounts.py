"""Compatibility wrapper for parent account workflows.

Parent account ownership moved to ``backend.domains.parents.service`` in DB-4.
Keep this module temporarily so older imports continue to work while callers
migrate to the parent domain package.

Temporary compatibility wrapper. Delete after identity and parent role imports
migrate to ``backend.domains.parents.service``.
"""

from backend.domains.parents.service import (  # noqa: F401
    link_parent_via_invite,
    parent_children,
    parent_from_telegram_user_id,
)

__all__ = [
    "link_parent_via_invite",
    "parent_children",
    "parent_from_telegram_user_id",
]
