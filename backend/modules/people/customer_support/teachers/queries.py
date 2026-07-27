"""Typed, read-only boundary for Customer Support Active Teacher lookup."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability
from backend.core.api.pagination import DEFAULT_PAGE_SIZE
from backend.modules.domains.teacher_records.support_contracts import (
    TeacherSupportProfile,
    TeacherSupportReader,
)
from backend.modules.people.customer_support.domain_types import DirectoryStatus
from backend.modules.people.customer_support.policies import require_capability
from backend.modules.people.customer_support.scope import (
    CustomerSupportScopeProvider,
)


@dataclass(frozen=True)
class TeacherDirectoryQuery:
    search_text: str = ""
    school_id: int | None = None
    status: DirectoryStatus = DirectoryStatus.ALL
    cursor: str | None = None
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class TeacherDirectoryItem:
    teacher_id: int
    full_name: str
    login: str
    phone: str
    telegram_username: str
    account_status: str
    school_ids: tuple[int, ...]
    school_names: tuple[str, ...]
    subject_names: tuple[str, ...]
    assigned_group_count: int


@dataclass(frozen=True)
class TeacherDirectoryPage:
    items: tuple[TeacherDirectoryItem, ...]
    next_cursor: str | None
    total: int | None = None


@dataclass(frozen=True)
class TeacherDetailResult:
    teacher: TeacherDirectoryItem
    assigned_group_names: tuple[str, ...]


def _directory_item(profile: TeacherSupportProfile) -> TeacherDirectoryItem:
    return TeacherDirectoryItem(
        teacher_id=profile.teacher_id,
        full_name=profile.full_name,
        login=profile.login,
        phone=profile.phone,
        telegram_username=profile.telegram_username,
        account_status=profile.account_status,
        school_ids=profile.school_ids,
        school_names=profile.school_names,
        subject_names=profile.subject_names,
        assigned_group_count=len(profile.assigned_group_ids),
    )


@dataclass(frozen=True)
class CustomerSupportTeacherQueries:
    reader: TeacherSupportReader
    scope_resolver: CustomerSupportScopeProvider

    def list_teachers(
        self,
        actor: ActorContext,
        query: TeacherDirectoryQuery,
    ) -> TeacherDirectoryPage:
        require_capability(actor, Capability.VIEW_TEACHER_SUPPORT_INFO)
        scoped_actor = self.scope_resolver.resolve(actor)
        result = self.reader.search_teachers(
            school_scope=scoped_actor.school_scope,
            search_text=query.search_text,
            school_id=query.school_id,
            status=query.status.value,
            cursor=query.cursor,
            page_size=query.page_size,
        )
        return TeacherDirectoryPage(
            items=tuple(_directory_item(profile) for profile in result.items),
            next_cursor=result.next_cursor,
            total=result.total,
        )

    def get_teacher(
        self,
        actor: ActorContext,
        teacher_id: int,
    ) -> TeacherDetailResult:
        require_capability(actor, Capability.VIEW_TEACHER_SUPPORT_INFO)
        scoped_actor = self.scope_resolver.resolve(actor)
        profile = self.reader.get_teacher(
            school_scope=scoped_actor.school_scope,
            teacher_id=teacher_id,
        )
        return TeacherDetailResult(
            teacher=_directory_item(profile),
            assigned_group_names=profile.assigned_group_names,
        )


__all__ = [
    "CustomerSupportTeacherQueries",
    "TeacherDetailResult",
    "TeacherDirectoryItem",
    "TeacherDirectoryPage",
    "TeacherDirectoryQuery",
]
