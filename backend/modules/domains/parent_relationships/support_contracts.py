"""School-scoped parent records exposed to support orchestrators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.core.access.context import SchoolScope


@dataclass(frozen=True)
class ParentSupportProfile:
    parent_id: int
    display_name: str
    phone: str
    telegram_username: str
    preferred_language: str
    status: str
    linked_student_ids: tuple[int, ...]
    school_ids: tuple[int, ...]
    version: int


@dataclass(frozen=True)
class ParentSupportProfilePage:
    items: tuple[ParentSupportProfile, ...]
    next_cursor: str | None
    total: int | None = None


class ParentSupportReader(Protocol):
    def search_parents(
        self,
        *,
        school_scope: SchoolScope,
        search_text: str,
        school_id: int | None,
        status: str,
        cursor: str | None,
        page_size: int,
    ) -> ParentSupportProfilePage: ...

    def get_parent(
        self,
        *,
        school_scope: SchoolScope,
        parent_id: int,
    ) -> ParentSupportProfile: ...


__all__ = [
    "ParentSupportProfile",
    "ParentSupportProfilePage",
    "ParentSupportReader",
]
