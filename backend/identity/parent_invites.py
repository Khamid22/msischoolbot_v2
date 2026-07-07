"""Compatibility wrapper for parent invite helpers.

Parent invite ownership moved to ``backend.domains.parents.service`` in DB-4.
Keep this module temporarily so older imports continue to work while callers
migrate to the parent domain package.

Temporary compatibility wrapper. Delete after invite imports migrate to
``backend.domains.parents.service``.
"""

from backend.domains.parents.service import (  # noqa: F401
    PARENT_INVITE_MAX_AGE_SECONDS,
    PARENT_INVITE_SALT,
    create_parent_invite_code,
    create_parent_invite_token,
    get_parent_invite_token,
    load_parent_invite_code_payload,
    load_parent_invite_payload,
)

__all__ = [
    "PARENT_INVITE_MAX_AGE_SECONDS",
    "PARENT_INVITE_SALT",
    "create_parent_invite_code",
    "create_parent_invite_token",
    "get_parent_invite_token",
    "load_parent_invite_code_payload",
    "load_parent_invite_payload",
]
