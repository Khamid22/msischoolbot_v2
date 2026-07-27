"""Public communication use cases."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.api.pagination import DEFAULT_PAGE_SIZE, normalize_page_size
from backend.core.unit_of_work import Connection
from backend.modules.domains.communications import announcements_repository
from backend.modules.domains.communications.announcements_service import list_announcements
from backend.modules.domains.communications.chat_service import (
    MAX_BODY,
    delete_message,
    edit_message,
    list_messages,
    send_message,
    student_can_access_room,
    validate_room,
)


@dataclass(frozen=True)
class PublishedAnnouncement:
    announcement_id: int
    title: str
    body: str
    priority: str
    is_pinned: bool
    published_at: str


def list_parent_announcements(
    conn: Connection,
    *,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[PublishedAnnouncement, ...]:
    rows = announcements_repository.list_published_announcement_rows_for_audience(
        conn,
        "parents",
    )
    return tuple(
        PublishedAnnouncement(
            announcement_id=int(row["id"]),
            title=str(row["title"] or "").strip(),
            body=str(row["body"] or "").strip(),
            priority=str(row["priority"] or "info").strip().casefold(),
            is_pinned=bool(row["pinned"]),
            published_at=str(row["published_at"] or row["updated_at"] or ""),
        )
        for row in rows[: normalize_page_size(limit)]
    )

__all__ = [
    "MAX_BODY",
    "PublishedAnnouncement",
    "delete_message",
    "edit_message",
    "list_announcements",
    "list_parent_announcements",
    "list_messages",
    "send_message",
    "student_can_access_room",
    "validate_room",
]
