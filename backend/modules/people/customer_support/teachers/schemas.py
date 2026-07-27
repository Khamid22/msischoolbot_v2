"""Camel-case API models for the read-only Teacher Support directory."""

from __future__ import annotations

from backend.core.api import ApiModel
from backend.modules.people.customer_support.teachers.queries import (
    TeacherDetailResult,
    TeacherDirectoryItem,
    TeacherDirectoryPage,
)


class TeacherDirectoryItemResponse(ApiModel):
    teacher_id: int
    full_name: str
    login: str
    phone: str
    telegram_username: str
    account_status: str
    school_ids: list[int]
    school_names: list[str]
    subject_names: list[str]
    assigned_group_count: int

    @classmethod
    def from_item(
        cls,
        item: TeacherDirectoryItem,
    ) -> TeacherDirectoryItemResponse:
        return cls(
            teacher_id=item.teacher_id,
            full_name=item.full_name,
            login=item.login,
            phone=item.phone,
            telegram_username=item.telegram_username,
            account_status=item.account_status,
            school_ids=list(item.school_ids),
            school_names=list(item.school_names),
            subject_names=list(item.subject_names),
            assigned_group_count=item.assigned_group_count,
        )


class TeacherDirectoryPageResponse(ApiModel):
    items: list[TeacherDirectoryItemResponse]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None

    @classmethod
    def from_page(cls, page: TeacherDirectoryPage) -> TeacherDirectoryPageResponse:
        return cls(
            items=[TeacherDirectoryItemResponse.from_item(item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.next_cursor is not None,
            total=page.total,
        )


class TeacherDetailResponse(ApiModel):
    teacher: TeacherDirectoryItemResponse
    assigned_group_names: list[str]

    @classmethod
    def from_result(cls, result: TeacherDetailResult) -> TeacherDetailResponse:
        return cls(
            teacher=TeacherDirectoryItemResponse.from_item(result.teacher),
            assigned_group_names=list(result.assigned_group_names),
        )


__all__ = [
    "TeacherDetailResponse",
    "TeacherDirectoryItemResponse",
    "TeacherDirectoryPageResponse",
]
