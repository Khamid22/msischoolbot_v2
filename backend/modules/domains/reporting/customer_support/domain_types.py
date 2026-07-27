"""Stable vocabulary for Customer Support operational reporting."""

from __future__ import annotations

from enum import StrEnum


class SupportRequesterType(StrEnum):
    PARENT = "parent"
    TEACHER = "teacher"
    STUDENT = "student"
    OTHER = "other"


class DashboardTicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


__all__ = ["DashboardTicketPriority", "SupportRequesterType"]
