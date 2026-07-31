"""Typed subject-curriculum API and contract models."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from backend.core.api import ApiModel
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumAssetRenderKind,
    CurriculumContentBlockType,
    CurriculumConversionStatus,
    CurriculumItemType,
    CurriculumRecordStatus,
    CurriculumRevisionState,
    CurriculumVariant,
)


class CurriculumContentBlock(ApiModel):
    block_type: CurriculumContentBlockType
    block_key: str = Field(default="", max_length=80)
    text: str = Field(default="", max_length=10_000)
    asset_id: int | None = Field(default=None, ge=1)

    @field_validator("block_key", "text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_block_content(self):
        media_types = {
            CurriculumContentBlockType.IMAGE,
            CurriculumContentBlockType.VIDEO,
            CurriculumContentBlockType.AUDIO,
            CurriculumContentBlockType.DOCUMENT,
            CurriculumContentBlockType.PRESENTATION,
            CurriculumContentBlockType.EMBED,
            CurriculumContentBlockType.LINK,
        }
        if self.block_type in media_types:
            if self.asset_id is None:
                raise ValueError("Media blocks require an attached asset.")
        elif not self.text:
            raise ValueError("Content cannot be empty.")
        if self.block_key and not self.block_key.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Block keys may contain letters, numbers, dashes, and underscores.")
        return self


class LessonGuidanceSection(ApiModel):
    section_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    activity_label: str = Field(default="", max_length=160)
    duration_minutes: int = Field(default=0, ge=0, le=480)
    planning_blocks: list[CurriculumContentBlock] = Field(
        default_factory=list,
        max_length=100,
    )
    teaching_blocks: list[CurriculumContentBlock] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator("section_key")
    @classmethod
    def normalize_section_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Section keys may contain letters, numbers, dashes, and underscores.")
        return normalized

    @field_validator("title")
    @classmethod
    def normalize_section_title(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("A section title is required.")
        return normalized

class LessonGuidanceDocument(ApiModel):
    overview: str = Field(default="", max_length=4_000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    duration_minutes: int = Field(default=0, ge=0, le=480)
    before_teaching: list[CurriculumContentBlock] = Field(
        default_factory=list,
        max_length=100,
    )
    sections: list[LessonGuidanceSection] = Field(default_factory=list, max_length=40)

    @field_validator("overview")
    @classmethod
    def normalize_overview(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            tag = " ".join(value.strip().split())
            if tag and tag not in normalized:
                normalized.append(tag)
        if any(len(tag) > 80 for tag in normalized):
            raise ValueError("Guidance tags may not exceed 80 characters.")
        return normalized

    @model_validator(mode="after")
    def validate_document_structure(self):
        section_keys = [section.section_key for section in self.sections]
        if len(section_keys) != len(set(section_keys)):
            raise ValueError("Lesson section keys must be unique.")
        return self


class CurriculumAsset(ApiModel):
    asset_id: int
    asset_kind: CurriculumAssetKind
    render_kind: CurriculumAssetRenderKind = CurriculumAssetRenderKind.DOCUMENT
    title: str
    external_url: str = ""
    preview_url: str = ""
    download_url: str = ""
    original_file_name: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    display_order: int = 1
    placement_version: int = 1
    conversion_status: CurriculumConversionStatus = CurriculumConversionStatus.NOT_REQUIRED
    conversion_error: str = ""
    conversion_attempts: int = 0
    slides: list["CurriculumAssetRendition"] = Field(default_factory=list)
    status: CurriculumRecordStatus = CurriculumRecordStatus.ACTIVE
    version: int = 1


class CurriculumAssetRendition(ApiModel):
    rendition_id: int
    slide_number: int
    preview_url: str
    mime_type: str
    size_bytes: int = 0
    width: int = 0
    height: int = 0


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
    guidance: LessonGuidanceDocument = Field(default_factory=LessonGuidanceDocument)
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


class FundamentalsLessonWrite(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    guidance: LessonGuidanceDocument = Field(default_factory=LessonGuidanceDocument)
    expected_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def adapt_legacy_curriculum_row(cls, value):
        if not isinstance(value, dict) or value.get("guidance"):
            return value
        raw_blocks = value.get("contentBlocks", value.get("content_blocks", []))
        if not isinstance(raw_blocks, list):
            raw_blocks = []
        before_teaching: list[dict[str, object]] = []
        sections: list[dict[str, object]] = []
        current_title = ""
        current_blocks: list[dict[str, object]] = []
        for raw_block in raw_blocks:
            if not isinstance(raw_block, dict):
                continue
            block_type = raw_block.get("blockType", raw_block.get("block_type"))
            if block_type == CurriculumContentBlockType.HEADING:
                if current_title:
                    sections.append(
                        {
                            "section_key": f"legacy-section-{len(sections) + 1}",
                            "title": current_title,
                            "planning_blocks": current_blocks,
                        }
                    )
                current_title = str(raw_block.get("text") or "").strip()
                current_blocks = []
            elif current_title:
                current_blocks.append(raw_block)
            else:
                before_teaching.append(raw_block)
        if current_title:
            sections.append(
                {
                    "section_key": f"legacy-section-{len(sections) + 1}",
                    "title": current_title,
                    "planning_blocks": current_blocks,
                }
            )
        elif before_teaching:
            sections.append(
                {
                    "section_key": "legacy-section-1",
                    "title": "Lesson guidance",
                    "planning_blocks": before_teaching,
                }
            )
            before_teaching = []
        normalized = dict(value)
        normalized["guidance"] = {
            "overview": value.get(
                "specificationPoints",
                value.get("specification_points", ""),
            ),
            "before_teaching": before_teaching,
            "sections": sections,
        }
        return normalized

    @field_validator("title")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("This field is required.")
        return normalized


class CurriculumLessonDraft(ApiModel):
    draft_id: int
    item_id: int
    subject_id: int
    state: CurriculumRevisionState = CurriculumRevisionState.DRAFT
    title: str
    guidance: LessonGuidanceDocument = Field(default_factory=LessonGuidanceDocument)
    assets: list[CurriculumAsset] = Field(default_factory=list)
    base_item_version: int
    revision_version: int
    is_new: bool = False
    updated_at: str = ""


class CurriculumDraftStartRequest(ApiModel):
    item_id: int | None = Field(default=None, ge=1)


class FundamentalsLessonPublish(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    guidance: LessonGuidanceDocument = Field(default_factory=LessonGuidanceDocument)
    expected_revision_version: int = Field(ge=1)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("A lesson title is required.")
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
    render_kind: CurriculumAssetRenderKind = CurriculumAssetRenderKind.LINK
    title: str = Field(min_length=1, max_length=200)
    external_url: str = Field(min_length=8, max_length=2_000)

    @field_validator("asset_kind")
    @classmethod
    def require_external_kind(cls, value: CurriculumAssetKind) -> CurriculumAssetKind:
        if value not in {CurriculumAssetKind.LINK, CurriculumAssetKind.VIDEO}:
            raise ValueError("Only link or video assets use an external URL.")
        return value

    @field_validator("render_kind")
    @classmethod
    def require_external_render_kind(
        cls,
        value: CurriculumAssetRenderKind,
    ) -> CurriculumAssetRenderKind:
        if value not in {
            CurriculumAssetRenderKind.LINK,
            CurriculumAssetRenderKind.EMBED,
            CurriculumAssetRenderKind.VIDEO,
        }:
            raise ValueError("External assets must be links, embeds, or videos.")
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
    "CurriculumAssetRendition",
    "CurriculumContentBlock",
    "CurriculumDetail",
    "CurriculumDraftStartRequest",
    "CurriculumExternalAssetWrite",
    "CurriculumItem",
    "CurriculumLessonDraft",
    "CurriculumReorderRequest",
    "CurriculumRestoreRequest",
    "CurriculumVariantSummary",
    "CurriculumViewAcknowledgement",
    "FundamentalsLessonWrite",
    "FundamentalsLessonPublish",
    "LessonGuidanceDocument",
    "LessonGuidanceSection",
    "SubjectCurriculumCatalog",
    "SubjectCurriculumSummary",
]
