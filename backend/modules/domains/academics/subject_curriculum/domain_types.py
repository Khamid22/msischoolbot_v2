"""Stable subject-curriculum vocabulary."""

from enum import StrEnum


class CurriculumVariant(StrEnum):
    PRIMARY = "primary"
    FUNDAMENTALS = "fundamentals"


class CurriculumItemType(StrEnum):
    LESSON = "lesson"
    EXAM = "exam"


class CurriculumRecordStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CurriculumAssetKind(StrEnum):
    FILE = "file"
    LINK = "link"
    VIDEO = "video"


class CurriculumContentBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    BULLETS = "bullets"
    NOTE = "note"


__all__ = [
    "CurriculumAssetKind",
    "CurriculumContentBlockType",
    "CurriculumItemType",
    "CurriculumRecordStatus",
    "CurriculumVariant",
]
