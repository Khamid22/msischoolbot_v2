"""Typed write boundary for Customer Support parent workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.core.access.context import ActorContext


@dataclass(frozen=True)
class UpdateParentCommand:
    parent_id: int
    expected_version: int
    display_name: str | None = None
    phone: str | None = None
    telegram_username: str | None = None
    preferred_language: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class SetParentLifecycleCommand:
    parent_id: int
    expected_version: int
    is_active: bool
    reason: str


@dataclass(frozen=True)
class LinkParentStudentCommand:
    parent_id: int
    student_id: int
    expected_version: int


@dataclass(frozen=True)
class UnlinkParentStudentCommand:
    parent_id: int
    student_id: int
    expected_version: int
    reason: str


@dataclass(frozen=True)
class ParentMutationResult:
    parent_id: int
    version: int


class CustomerSupportParentCommands(Protocol):
    def update_parent(
        self,
        actor: ActorContext,
        command: UpdateParentCommand,
    ) -> ParentMutationResult: ...

    def set_parent_lifecycle(
        self,
        actor: ActorContext,
        command: SetParentLifecycleCommand,
    ) -> ParentMutationResult: ...

    def link_student(
        self,
        actor: ActorContext,
        command: LinkParentStudentCommand,
    ) -> ParentMutationResult: ...

    def unlink_student(
        self,
        actor: ActorContext,
        command: UnlinkParentStudentCommand,
    ) -> ParentMutationResult: ...


__all__ = [
    "CustomerSupportParentCommands",
    "LinkParentStudentCommand",
    "ParentMutationResult",
    "SetParentLifecycleCommand",
    "UnlinkParentStudentCommand",
    "UpdateParentCommand",
]
