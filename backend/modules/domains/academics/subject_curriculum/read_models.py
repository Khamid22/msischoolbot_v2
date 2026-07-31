"""Persistence-row mapping for subject-curriculum read models."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumItemType,
    CurriculumRecordStatus,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumAsset,
    CurriculumContentBlock,
    CurriculumItem,
    LessonGuidanceDocument,
    LessonGuidanceSection,
)


def _as_iso(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _content_blocks(raw_value: object) -> list[CurriculumContentBlock]:
    if not isinstance(raw_value, list):
        return []
    blocks: list[CurriculumContentBlock] = []
    for value in raw_value:
        try:
            blocks.append(CurriculumContentBlock.model_validate(value))
        except (TypeError, ValueError):
            continue
    return blocks


def _legacy_guidance_document(row) -> LessonGuidanceDocument:
    blocks = _content_blocks(row["content_json"])
    before_teaching: list[CurriculumContentBlock] = []
    sections: list[LessonGuidanceSection] = []
    current_title = ""
    current_blocks: list[CurriculumContentBlock] = []
    for block in blocks:
        if block.block_type.value == "heading":
            if current_title:
                sections.append(
                    LessonGuidanceSection(
                        section_key=f"legacy-section-{len(sections) + 1}",
                        title=current_title,
                        planning_blocks=current_blocks,
                    )
                )
            current_title = block.text
            current_blocks = []
        elif current_title:
            current_blocks.append(block)
        else:
            before_teaching.append(block)
    if current_title:
        sections.append(
            LessonGuidanceSection(
                section_key=f"legacy-section-{len(sections) + 1}",
                title=current_title,
                planning_blocks=current_blocks,
            )
        )
    elif before_teaching:
        sections.append(
            LessonGuidanceSection(
                section_key="legacy-section-1",
                title="Lesson guidance",
                planning_blocks=before_teaching,
            )
        )
        before_teaching = []
    return LessonGuidanceDocument(
        overview=str(row["specification_points"] or ""),
        before_teaching=before_teaching,
        sections=sections,
    )


def _guidance_document(row) -> LessonGuidanceDocument:
    raw_value = row["guidance_json"]
    if isinstance(raw_value, dict) and raw_value:
        try:
            document = LessonGuidanceDocument.model_validate(raw_value)
            if (
                document.overview
                or document.tags
                or document.duration_minutes
                or document.before_teaching
                or document.sections
            ):
                return document
        except (TypeError, ValueError):
            pass
    return _legacy_guidance_document(row)


def _assets_by_item(rows, url_prefix: str) -> dict[int, list[CurriculumAsset]]:
    grouped: dict[int, list[CurriculumAsset]] = defaultdict(list)
    for row in rows:
        asset_id = int(row["asset_id"])
        is_file = str(row["asset_kind"]) == CurriculumAssetKind.FILE
        grouped[int(row["item_id"])].append(
            CurriculumAsset(
                asset_id=asset_id,
                asset_kind=CurriculumAssetKind(str(row["asset_kind"])),
                title=str(row["title"] or ""),
                external_url=str(row["external_url"] or ""),
                download_url=f"{url_prefix}/{asset_id}/open" if is_file else "",
                original_file_name=str(row["original_file_name"] or ""),
                mime_type=str(row["mime_type"] or ""),
                size_bytes=int(row["size_bytes"] or 0),
                display_order=int(row["display_order"] or 1),
                status=CurriculumRecordStatus(str(row["status"])),
                version=int(row["version"] or 1),
            )
        )
    return grouped


def items_from_rows(rows, asset_rows, *, url_prefix: str) -> list[CurriculumItem]:
    assets = _assets_by_item(asset_rows, url_prefix)
    return [
        CurriculumItem(
            item_id=int(row["item_id"]),
            item_order=int(row["item_order"]),
            lesson_number=str(row["lesson_number"] or ""),
            item_type=CurriculumItemType(str(row["item_type"])),
            title=str(row["title"] or ""),
            term_label=str(row["term_label"] or ""),
            week_label=str(row["week_label"] or ""),
            specification_points=str(row["specification_points"] or ""),
            book_pages=str(row["book_pages"] or ""),
            lesson_count=str(row["lesson_count"] or ""),
            duration_hours=str(row["duration_hours"] or ""),
            content_blocks=_content_blocks(row["content_json"]),
            guidance=_guidance_document(row),
            assets=assets.get(int(row["item_id"]), []),
            status=CurriculumRecordStatus(str(row["status"])),
            version=int(row["version"] or 1),
            updated_at=_as_iso(row["updated_at"]),
        )
        for row in rows
    ]


__all__ = ["items_from_rows"]
