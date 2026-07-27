"""Stable Customer Support workspace vocabulary."""

from __future__ import annotations

from enum import StrEnum


class CustomerSupportSection(StrEnum):
    DASHBOARD = "dashboard"
    PARENTS = "parents"
    TEACHERS = "teachers"
    TICKETS = "tickets"


class DirectoryStatus(StrEnum):
    ALL = "all"
    ACTIVE = "active"
    PENDING = "pending"
    DISABLED = "disabled"
    ARCHIVED = "archived"


__all__ = ["CustomerSupportSection", "DirectoryStatus"]
