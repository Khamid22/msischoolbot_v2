"""School-scoped Active Teacher records exposed to support orchestrators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.core.access.context import SchoolScope


class TeacherSupportError(ValueError):
    """Base error for the school-scoped teacher support reader."""


class TeacherSupportNotFoundError(TeacherSupportError):
    """Raised when a visible teacher record does not exist."""


class TeacherSupportScopeError(TeacherSupportError):
    """Raised when a query requests a school outside the supplied scope."""


class TeacherSupportCursorError(TeacherSupportError):
    """Raised when a directory cursor cannot be decoded."""


@dataclass(frozen=True)
class TeacherSupportProfile:
    teacher_id: int
    full_name: str
    login: str
    phone: str
    telegram_username: str
    account_status: str
    school_ids: tuple[int, ...]
    school_names: tuple[str, ...]
    subject_names: tuple[str, ...]
    assigned_group_ids: tuple[int, ...]
    assigned_group_names: tuple[str, ...]


@dataclass(frozen=True)
class TeacherSupportProfilePage:
    items: tuple[TeacherSupportProfile, ...]
    next_cursor: str | None
    total: int | None = None


class TeacherSupportReader(Protocol):
    def search_teachers(
        self,
        *,
        school_scope: SchoolScope,
        search_text: str,
        school_id: int | None,
        status: str,
        cursor: str | None,
        page_size: int,
    ) -> TeacherSupportProfilePage: ...

    def get_teacher(
        self,
        *,
        school_scope: SchoolScope,
        teacher_id: int,
    ) -> TeacherSupportProfile: ...


__all__ = [
    "TeacherSupportProfile",
    "TeacherSupportProfilePage",
    "TeacherSupportReader",
    "TeacherSupportCursorError",
    "TeacherSupportError",
    "TeacherSupportNotFoundError",
    "TeacherSupportScopeError",
]
