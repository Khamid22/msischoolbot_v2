"""Typed authenticated actor and school-scope context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.core.access.capabilities import access_defaults_for_role, capabilities_for_role
from backend.core.access.domain_types import (
    Capability,
    Domain,
    ObjectScope,
    Role,
    SchoolScopeMode,
)


@dataclass(frozen=True)
class SchoolScope:
    allowed_school_ids: frozenset[int] = frozenset()
    all_schools: bool = False

    def allows(self, school_id: int) -> bool:
        return self.all_schools or int(school_id) in self.allowed_school_ids


@dataclass(frozen=True)
class ActorContext:
    account_id: int | None
    role: Role
    capabilities: frozenset[Capability]
    school_scope: SchoolScope
    allowed_domains: frozenset[Domain] = frozenset()
    school_scope_mode: SchoolScopeMode = SchoolScopeMode.ASSIGNED_SCHOOLS
    object_scope: ObjectScope = ObjectScope.OWN_RECORDS
    request_id: str = ""
    correlation_id: str = ""
    profile_id: int | None = None
    staff_id: int | None = None
    teacher_id: int | None = None
    student_id: int | None = None
    parent_id: int | None = None
    assigned_subject_ids: frozenset[int] = frozenset()
    assigned_group_ids: frozenset[int] = frozenset()

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def can_use_domain(self, domain: Domain) -> bool:
        return domain in self.allowed_domains


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _school_ids(session: Mapping[str, Any]) -> frozenset[int]:
    raw_values = (
        session.get("allowed_school_ids")
        or session.get("school_ids")
        or session.get("school_id")
        or ()
    )
    if isinstance(raw_values, str):
        raw_values = raw_values.replace(";", ",").split(",")
    if not isinstance(raw_values, list | tuple | set | frozenset):
        raw_values = (raw_values,)
    return frozenset(
        school_id
        for school_id in (_positive_int(value) for value in raw_values)
        if school_id is not None
    )


def _assigned_ids(session: Mapping[str, Any], *keys: str) -> frozenset[int]:
    raw_values: Any = ()
    for key in keys:
        if session.get(key) not in (None, ""):
            raw_values = session[key]
            break
    if isinstance(raw_values, str):
        raw_values = raw_values.replace(";", ",").split(",")
    if not isinstance(raw_values, list | tuple | set | frozenset):
        raw_values = (raw_values,)
    return frozenset(
        item_id for item_id in (_positive_int(value) for value in raw_values) if item_id is not None
    )


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def actor_context_from_session(
    session: Mapping[str, Any],
    *,
    request_id: str = "",
    correlation_id: str = "",
) -> ActorContext:
    role = Role(str(session.get("auth_role") or "").strip())
    defaults = access_defaults_for_role(role)
    if defaults is None:
        raise ValueError(f"No access defaults registered for {role.value}")
    return ActorContext(
        account_id=_positive_int(session.get("account_id")),
        role=role,
        capabilities=capabilities_for_role(role),
        school_scope=SchoolScope(
            allowed_school_ids=_school_ids(session),
            all_schools=(
                defaults.school_scope_mode is SchoolScopeMode.ALL_SCHOOLS
                or _is_true(session.get("all_schools"))
            ),
        ),
        allowed_domains=defaults.allowed_domains,
        school_scope_mode=defaults.school_scope_mode,
        object_scope=defaults.object_scope,
        request_id=request_id,
        correlation_id=correlation_id or request_id,
        profile_id=_positive_int(session.get("profile_id")),
        staff_id=_positive_int(session.get("staff_id")),
        teacher_id=_positive_int(session.get("teacher_id")),
        student_id=_positive_int(session.get("student_db_id")),
        parent_id=_positive_int(session.get("parent_id")),
        assigned_subject_ids=_assigned_ids(
            session,
            "assigned_subject_ids",
            "subject_ids",
            "subject_id",
        ),
        assigned_group_ids=_assigned_ids(
            session,
            "assigned_group_ids",
            "group_ids",
            "group_id",
        ),
    )


resolve_actor_context = actor_context_from_session


__all__ = [
    "ActorContext",
    "SchoolScope",
    "actor_context_from_session",
    "resolve_actor_context",
]
