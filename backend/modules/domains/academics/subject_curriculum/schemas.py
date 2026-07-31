"""Typed subject-curriculum API and contract models."""

from __future__ import annotations

from pydantic import Field, field_validator

from backend.core.api import ApiModel
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumContentBlockType,
    CurriculumItemType,
    CurriculumRecordStatus,
    CurriculumVariant,
)


class CurriculumContentBlock(ApiModel):
    block_type: CurriculumContentBlockType
    text: str = Field(min_length=1, max_length=10_000)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Content cannot be empty.")
        return normalized


class CurriculumAsset(ApiModel):
    asset_id: int
    asset_kind: CurriculumAssetKind
    title: str
    external_url: str = ""
    download_url: str = ""
    original_file_name: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    display_order: int = 1
    status: CurriculumRecordStatus = CurriculumRecordStatus.ACTIVE
    version: int = 1


class CurriculumItem(ApiModel):
    item_id: int
    item_order: int
    lesson_number: str
    item_type: CurriculumItemType
    title: str
    term_label: str = ""
    week_label: str = ""
    specification_points: str = ""
    book_pages: str = ""
    lesson_count: str = ""
    duration_hours: str = ""
    content_blocks: list[CurriculumContentBlock] = Field(default_factory=list)
    assets: list[CurriculumAsset] = Field(default_factory=list)
    status: CurriculumRecordStatus = CurriculumRecordStatus.ACTIVE
    version: int = 1
    updated_at: str = ""


class CurriculumVariantSummary(ApiModel):
    curriculum_id: int | None = None
    program_id: int | None = None
    curriculum_key: CurriculumVariant
    title: str
    item_count: int = 0
    lesson_count: int = 0
    exam_count: int = 0
    version: int = 1
    is_editable: bool = False
    has_updates: bool = False
    updated_at: str = ""


class SubjectCurriculumSummary(ApiModel):
    subject_id: int
    subject_key: str
    subject_name: str
    subject_short: str = ""
    variants: list[CurriculumVariantSummary] = Field(default_factory=list)


class SubjectCurriculumCatalog(ApiModel):
    subjects: list[SubjectCurriculumSummary] = Field(default_factory=list)


class CurriculumDetail(ApiModel):
    subject: SubjectCurriculumSummary
    variant: CurriculumVariantSummary
    items: list[CurriculumItem] = Field(default_factory=list)
    archived_items: list[CurriculumItem] = Field(default_factory=list)


class CurriculumItemWrite(ApiModel):
    lesson_number: str = Field(min_length=1, max_length=80)
    item_type: CurriculumItemType = CurriculumItemType.LESSON
    title: str = Field(min_length=1, max_length=300)
    term_label: str = Field(default="", max_length=120)
    week_label: str = Field(default="", max_length=120)
    specification_points: str = Field(default="", max_length=4_000)
    book_pages: str = Field(default="", max_length=300)
    lesson_count: str = Field(default="", max_length=80)
    duration_hours: str = Field(default="", max_length=80)
    content_blocks: list[CurriculumContentBlock] = Field(default_factory=list)
    expected_version: int | None = Field(default=None, ge=1)

    @field_validator("lesson_number", "title")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("This field is required.")
        return normalized


class CurriculumReorderRequest(ApiModel):
    item_ids: list[int] = Field(min_length=1)
    expected_curriculum_version: int = Field(ge=1)


class CurriculumArchiveRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=500)
    expected_version: int = Field(ge=1)


class CurriculumRestoreRequest(ApiModel):
    expected_version: int = Field(ge=1)


class CurriculumExternalAssetWrite(ApiModel):
    asset_kind: CurriculumAssetKind
    title: str = Field(min_length=1, max_length=200)
    external_url: str = Field(min_length=8, max_length=2_000)

    @field_validator("asset_kind")
    @classmethod
    def require_external_kind(cls, value: CurriculumAssetKind) -> CurriculumAssetKind:
        if value not in {CurriculumAssetKind.LINK, CurriculumAssetKind.VIDEO}:
            raise ValueError("Only link or video assets use an external URL.")
        return value

    @field_validator("external_url")
    @classmethod
    def require_https(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.casefold().startswith("https://"):
            raise ValueError("External curriculum URLs must use HTTPS.")
        return normalized


class CurriculumViewAcknowledgement(ApiModel):
    curriculum_key: CurriculumVariant
    viewed_at: str


__all__ = [
    "CurriculumArchiveRequest",
    "CurriculumAsset",
    "CurriculumContentBlock",
    "CurriculumDetail",
    "CurriculumExternalAssetWrite",
    "CurriculumItem",
    "CurriculumItemWrite",
    "CurriculumReorderRequest",
    "CurriculumRestoreRequest",
    "CurriculumVariantSummary",
    "CurriculumViewAcknowledgement",
    "SubjectCurriculumCatalog",
    "SubjectCurriculumSummary",
]
