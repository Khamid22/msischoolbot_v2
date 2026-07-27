"""Typed read boundary for Customer Support parent workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from backend.core.access.context import ActorContext
from backend.core.api.pagination import DEFAULT_PAGE_SIZE
from backend.modules.people.customer_support.domain_types import DirectoryStatus


@dataclass(frozen=True)
class ParentDirectoryQuery:
    search_text: str = ""
    school_id: int | None = None
    status: DirectoryStatus = DirectoryStatus.ALL
    cursor: str | None = None
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class BalanceSummary:
    currency: str
    outstanding_amount: Decimal


@dataclass(frozen=True)
class LinkedStudentSummary:
    student_id: int
    full_name: str
    student_code: str
    school_id: int
    school_name: str
    is_active: bool


@dataclass(frozen=True)
class ParentDirectoryItem:
    parent_id: int
    display_name: str
    phone: str
    telegram_username: str
    status: str
    linked_student_count: int
    open_ticket_count: int
    school_ids: tuple[int, ...]
    version: int


@dataclass(frozen=True)
class ParentDirectoryPage:
    items: tuple[ParentDirectoryItem, ...]
    next_cursor: str | None
    total: int | None = None


@dataclass(frozen=True)
class ParentDetailResult:
    parent: ParentDirectoryItem
    preferred_language: str
    students: tuple[LinkedStudentSummary, ...]
    balances: tuple[BalanceSummary, ...]


class CustomerSupportParentQueries(Protocol):
    def list_parents(
        self,
        actor: ActorContext,
        query: ParentDirectoryQuery,
    ) -> ParentDirectoryPage: ...

    def get_parent(
        self,
        actor: ActorContext,
        parent_id: int,
    ) -> ParentDetailResult: ...


__all__ = [
    "BalanceSummary",
    "CustomerSupportParentQueries",
    "LinkedStudentSummary",
    "ParentDetailResult",
    "ParentDirectoryItem",
    "ParentDirectoryPage",
    "ParentDirectoryQuery",
]
