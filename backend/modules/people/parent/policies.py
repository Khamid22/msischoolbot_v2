"""Authorization policies for parent-owned workspace use cases."""

from __future__ import annotations

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability, Role


class ParentAccessError(PermissionError):
    pass


class ParentRecordNotFoundError(LookupError):
    pass


def require_parent_capability(
    actor: ActorContext,
    capability: Capability,
) -> int:
    if actor.role is not Role.PARENT:
        raise ParentAccessError("Parent access is required.")
    if not actor.has(capability):
        raise ParentAccessError(f"The {capability.value} capability is required.")
    if actor.parent_id is None:
        raise ParentAccessError("The parent session is incomplete.")
    return actor.parent_id


__all__ = [
    "ParentAccessError",
    "ParentRecordNotFoundError",
    "require_parent_capability",
]
