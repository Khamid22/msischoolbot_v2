"""Explicit module and workspace registration types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

from backend.core.access.capabilities import access_defaults_for_role
from backend.core.access.domain_types import (
    Capability,
    Domain,
    ObjectScope,
    PersonType,
    Role,
    SchoolScopeMode,
)
from backend.core.jobs import JobHandlerSpec


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    api_router: APIRouter | None = None
    job_handlers: tuple[JobHandlerSpec, ...] = ()
    health_checks: tuple[Callable[[], bool], ...] = ()


@dataclass(frozen=True)
class WorkspaceSpec:
    name: str
    register_pages: Callable[[FastAPI], None]


@dataclass(frozen=True)
class PersonModuleSpec:
    person_type: PersonType
    default_capabilities: frozenset[Capability]
    allowed_domains: frozenset[Domain]
    school_scope_mode: SchoolScopeMode
    object_scope: ObjectScope
    workspace_name: str

    @property
    def role(self) -> Role:
        return Role(self.person_type.value)


def build_person_module_spec(
    role: Role,
    *,
    workspace_name: str | None = None,
) -> PersonModuleSpec:
    defaults = access_defaults_for_role(role)
    if defaults is None:
        raise ValueError(f"No access defaults registered for {role.value}")
    return PersonModuleSpec(
        person_type=PersonType(role.value),
        default_capabilities=defaults.capabilities,
        allowed_domains=defaults.allowed_domains,
        school_scope_mode=defaults.school_scope_mode,
        object_scope=defaults.object_scope,
        workspace_name=workspace_name or role.value,
    )


class PersonModuleRegistry:
    def __init__(self, modules: tuple[PersonModuleSpec, ...]) -> None:
        by_person_type = {module.person_type: module for module in modules}
        if len(by_person_type) != len(modules):
            raise ValueError("A person module was registered more than once")
        missing = set(PersonType) - set(by_person_type)
        if missing:
            names = ", ".join(sorted(person_type.value for person_type in missing))
            raise ValueError(f"Missing person modules: {names}")
        self._modules = modules
        self._by_person_type = by_person_type

    @property
    def modules(self) -> tuple[PersonModuleSpec, ...]:
        return self._modules

    def for_person(self, person_type: PersonType | Role | str) -> PersonModuleSpec:
        normalized = PersonType(str(person_type))
        return self._by_person_type[normalized]


__all__ = [
    "ModuleSpec",
    "PersonModuleRegistry",
    "PersonModuleSpec",
    "WorkspaceSpec",
    "build_person_module_spec",
]
