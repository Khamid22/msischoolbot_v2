"""Stable vocabulary for Customer Support operational reporting."""

from __future__ import annotations

from enum import StrEnum

from backend.modules.domains.support_cases.tickets.domain_types import TicketPriority


class SupportRequesterType(StrEnum):
    PARENT = "parent"
    TEACHER = "teacher"
    STUDENT = "student"
    OTHER = "other"


# Compatibility alias: the Support Cases domain owns the vocabulary.
DashboardTicketPriority = TicketPriority


__all__ = ["DashboardTicketPriority", "SupportRequesterType"]
