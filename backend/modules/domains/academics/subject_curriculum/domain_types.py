"""Stable subject-curriculum vocabulary."""

from enum import StrEnum


class CurriculumVariant(StrEnum):
    PRIMARY = "primary"
    FUNDAMENTALS = "fundamentals"


class CurriculumItemType(StrEnum):
    LESSON = "lesson"
    EXAM = "exam"


class CurriculumRecordStatus(StrEnum):
    DRAFT = "draft"
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
    CHECKLIST = "checklist"
    NOTE = "note"
    QUOTE = "quote"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    EMBED = "embed"
    LINK = "link"


class CurriculumAssetRenderKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    EMBED = "embed"
    LINK = "link"


class CurriculumConversionStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class CurriculumRevisionState(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    ABANDONED = "abandoned"


__all__ = [
    "CurriculumAssetKind",
    "CurriculumAssetRenderKind",
    "CurriculumContentBlockType",
    "CurriculumConversionStatus",
    "CurriculumItemType",
    "CurriculumRecordStatus",
    "CurriculumRevisionState",
    "CurriculumVariant",
]
