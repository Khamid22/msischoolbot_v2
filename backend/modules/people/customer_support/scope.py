"""Resolve effective Customer Support school scope from current assignments."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from backend.core.access.context import ActorContext, SchoolScope
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.identity.contracts import (
    get_staff_school_scope_assignment,
)
from backend.modules.domains.organization.contracts import list_school_references
from backend.modules.people.customer_support.policies import (
    CustomerSupportAccessError,
    require_customer_support_actor,
)

ALL_SCHOOLS_SCOPE_TOKENS = frozenset({"*", "all", "all schools"})


def _scope_tokens(raw_scope: str) -> frozenset[str]:
    normalized = str(raw_scope or "").replace(";", ",").replace("|", ",")
    return frozenset(token.strip().casefold() for token in normalized.split(",") if token.strip())


class CustomerSupportScopeProvider(Protocol):
    def resolve(self, actor: ActorContext) -> ActorContext: ...


@dataclass(frozen=True)
class CustomerSupportScopeResolver:
    unit_of_work_factory: UnitOfWorkFactory

    def resolve(self, actor: ActorContext) -> ActorContext:
        require_customer_support_actor(actor)
        with self.unit_of_work_factory.read() as unit_of_work:
            assignment = get_staff_school_scope_assignment(
                unit_of_work.conn,
                staff_id=actor.staff_id,
                account_id=actor.account_id,
            )
            schools = list_school_references(unit_of_work.conn)

        if assignment is None:
            raise CustomerSupportAccessError(
                "Customer Support school assignments could not be resolved."
            )

        tokens = _scope_tokens(assignment.raw_scope)
        all_schools = not tokens or bool(tokens & ALL_SCHOOLS_SCOPE_TOKENS)
        allowed_school_ids = frozenset(
            school.school_id
            for school in schools
            if all_schools
            or str(school.school_id) in tokens
            or school.code.casefold() in tokens
            or school.name.casefold() in tokens
        )
        return replace(
            actor,
            school_scope=SchoolScope(
                allowed_school_ids=allowed_school_ids,
                all_schools=all_schools,
            ),
        )


__all__ = [
    "ALL_SCHOOLS_SCOPE_TOKENS",
    "CustomerSupportScopeProvider",
    "CustomerSupportScopeResolver",
]
