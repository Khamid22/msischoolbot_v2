"""Compatibility facade for the legacy complaint service import path."""

from backend.modules.domains.support_cases.tickets.service import (
    VALID_COMPLAINT_CATEGORIES,
    VALID_COMPLAINT_STATUSES,
    add_complaint_reply,
    create_complaint,
    get_complaint,
    list_complaints,
    update_complaint,
)

__all__ = [
    "VALID_COMPLAINT_CATEGORIES",
    "VALID_COMPLAINT_STATUSES",
    "add_complaint_reply",
    "create_complaint",
    "get_complaint",
    "list_complaints",
    "update_complaint",
]
