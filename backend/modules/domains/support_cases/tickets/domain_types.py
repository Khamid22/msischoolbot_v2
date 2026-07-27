"""Stable database and wire vocabulary for support tickets."""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Final


class TicketStatus(StrEnum):
    """Persisted lifecycle states supported by the current ticket table."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class TicketCategory(StrEnum):
    """Persisted ticket categories; display labels belong in the frontend."""

    COMPLAINT = "complaint"
    DIRECT_CONTACT = "direct_contact"
    PAYMENT = "payment"
    TEACHER = "teacher"
    LESSON_QUALITY = "lesson_quality"
    SCHEDULE = "schedule"
    ATTENDANCE = "attendance"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    OTHER = "other"


TICKET_STATUS_ALIASES: Final = MappingProxyType(
    {
        "progress": TicketStatus.IN_PROGRESS.value,
        "open": TicketStatus.IN_PROGRESS.value,
        "done": TicketStatus.RESOLVED.value,
        "closed": TicketStatus.RESOLVED.value,
    }
)
VALID_TICKET_STATUSES: Final = frozenset(status.value for status in TicketStatus)
VALID_TICKET_CATEGORIES: Final = frozenset(category.value for category in TicketCategory)


def normalize_ticket_status(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    normalized = TICKET_STATUS_ALIASES.get(normalized, normalized)
    if normalized in VALID_TICKET_STATUSES:
        return normalized
    return TicketStatus.NEW.value


def normalize_ticket_category(value: object) -> str:
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if normalized in VALID_TICKET_CATEGORIES:
        return normalized
    return TicketCategory.OTHER.value


__all__ = [
    "TICKET_STATUS_ALIASES",
    "VALID_TICKET_CATEGORIES",
    "VALID_TICKET_STATUSES",
    "TicketCategory",
    "TicketStatus",
    "normalize_ticket_category",
    "normalize_ticket_status",
]
