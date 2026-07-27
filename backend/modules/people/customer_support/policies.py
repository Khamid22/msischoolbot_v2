"""Authorization rules shared by Customer Support use cases."""

from __future__ import annotations

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability, Role


class CustomerSupportAccessError(PermissionError):
    """Raised when a Customer Support actor exceeds their effective scope."""


def require_customer_support_actor(actor: ActorContext) -> None:
    if actor.role is not Role.CUSTOMER_SUPPORT:
        raise CustomerSupportAccessError("Customer Support access is required.")


def require_capability(actor: ActorContext, capability: Capability) -> None:
    require_customer_support_actor(actor)
    if not actor.has(capability):
        raise CustomerSupportAccessError(f"The {capability.value} capability is required.")


def require_school_access(actor: ActorContext, school_id: int) -> None:
    require_customer_support_actor(actor)
    if not actor.school_scope.allows(school_id):
        raise CustomerSupportAccessError("The selected school is outside your assigned scope.")


__all__ = [
    "CustomerSupportAccessError",
    "require_capability",
    "require_customer_support_actor",
    "require_school_access",
]
