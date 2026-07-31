"""Persistence-row mapping for subject-curriculum read models."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumAssetRenderKind,
    CurriculumContentBlockType,
    CurriculumConversionStatus,
    CurriculumItemType,
    CurriculumRecordStatus,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumAsset,
    CurriculumAssetRendition,
    CurriculumContentBlock,
    CurriculumItem,
    LessonGuidanceDocument,
    LessonGuidanceSection,
)


def _value(row, key: str, default=None):
    try:
        value = row[key]
    except (KeyError, TypeError):
        return default
    return default if value is None else value


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
    ungrouped_blocks: list[CurriculumContentBlock] = []
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
                        blocks=current_blocks,
                    )
                )
            current_title = block.text
            current_blocks = []
        elif current_title:
            current_blocks.append(block)
        else:
            ungrouped_blocks.append(block)
    if current_title:
        sections.append(
            LessonGuidanceSection(
                section_key=f"legacy-section-{len(sections) + 1}",
                title=current_title,
                blocks=current_blocks,
            )
        )
    if ungrouped_blocks:
        sections.insert(
            0,
            LessonGuidanceSection(
                section_key="legacy-preparation",
                title="Preparation",
                blocks=ungrouped_blocks,
            ),
        )
    return LessonGuidanceDocument(
        overview=str(row["specification_points"] or ""),
        sections=sections,
    )


def _guidance_document(row) -> LessonGuidanceDocument:
    raw_value = row["guidance_json"]
    if isinstance(raw_value, dict) and raw_value:
        try:
            document = LessonGuidanceDocument.model_validate(raw_value)
            if document.overview or document.tags or document.duration_minutes or document.sections:
                return document
        except (TypeError, ValueError):
            pass
    return _legacy_guidance_document(row)


def guidance_from_row(row) -> LessonGuidanceDocument:
    """Map stored guidance while preserving pre-constructor legacy content."""
    return _guidance_document(row)


def _renditions_by_asset(rows, url_prefix: str) -> dict[int, list[CurriculumAssetRendition]]:
    grouped: dict[int, list[CurriculumAssetRendition]] = defaultdict(list)
    for row in rows:
        asset_id = int(row["asset_id"])
        slide_number = int(row["slide_number"])
        grouped[asset_id].append(
            CurriculumAssetRendition(
                rendition_id=int(row["rendition_id"]),
                slide_number=slide_number,
                preview_url=f"{url_prefix}/{asset_id}/slides/{slide_number}/open",
                mime_type=str(row["mime_type"] or ""),
                size_bytes=int(row["size_bytes"] or 0),
                width=int(row["width"] or 0),
                height=int(row["height"] or 0),
            )
        )
    return grouped


def _assets_by_item(
    rows,
    rendition_rows,
    url_prefix: str,
) -> dict[int, list[CurriculumAsset]]:
    grouped: dict[int, list[CurriculumAsset]] = defaultdict(list)
    renditions = _renditions_by_asset(rendition_rows, url_prefix)
    for row in rows:
        asset_id = int(row["asset_id"])
        is_file = str(row["asset_kind"]) == CurriculumAssetKind.FILE
        grouped[int(row["item_id"])].append(
            CurriculumAsset(
                asset_id=asset_id,
                asset_kind=CurriculumAssetKind(str(row["asset_kind"])),
                render_kind=CurriculumAssetRenderKind(
                    str(_value(row, "render_kind", CurriculumAssetRenderKind.DOCUMENT))
                ),
                title=str(row["title"] or ""),
                external_url=str(row["external_url"] or ""),
                preview_url=f"{url_prefix}/{asset_id}/open" if is_file else "",
                download_url=(f"{url_prefix}/{asset_id}/open?download=true" if is_file else ""),
                original_file_name=str(row["original_file_name"] or ""),
                mime_type=str(row["mime_type"] or ""),
                size_bytes=int(row["size_bytes"] or 0),
                display_order=int(row["display_order"] or 1),
                placement_version=int(_value(row, "placement_version", 1)),
                conversion_status=CurriculumConversionStatus(
                    str(
                        _value(
                            row,
                            "conversion_status",
                            CurriculumConversionStatus.NOT_REQUIRED,
                        )
                    )
                ),
                conversion_error=str(_value(row, "conversion_error", "")),
                conversion_attempts=int(_value(row, "conversion_attempts", 0)),
                slides=renditions.get(asset_id, []),
                status=CurriculumRecordStatus(str(row["status"])),
                version=int(row["version"] or 1),
            )
        )
    return grouped


def assets_from_rows(rows, rendition_rows, *, url_prefix: str) -> list[CurriculumAsset]:
    grouped = _assets_by_item(rows, rendition_rows, url_prefix)
    return [asset for item_assets in grouped.values() for asset in item_assets]


def _with_legacy_materials(
    guidance: LessonGuidanceDocument,
    item_assets: list[CurriculumAsset],
) -> LessonGuidanceDocument:
    all_blocks = [block for section in guidance.sections for block in section.blocks]
    referenced_ids = {int(block.asset_id) for block in all_blocks if block.asset_id is not None}
    missing = [asset for asset in item_assets if asset.asset_id not in referenced_ids]
    if not missing:
        return guidance
    material_blocks = [
        CurriculumContentBlock(
            block_key=f"legacy-material-{asset.asset_id}",
            block_type=CurriculumContentBlockType(asset.render_kind.value),
            asset_id=asset.asset_id,
            text=asset.title,
        )
        for asset in missing
    ]
    if any(section.section_key == "legacy-materials" for section in guidance.sections):
        sections = [
            section.model_copy(
                update={
                    "blocks": [
                        *section.blocks,
                        *material_blocks,
                    ]
                }
            )
            if section.section_key == "legacy-materials"
            else section
            for section in guidance.sections
        ]
    else:
        sections = [
            *guidance.sections,
            LessonGuidanceSection(
                section_key="legacy-materials",
                title="Materials",
                blocks=material_blocks,
            ),
        ]
    return guidance.model_copy(update={"sections": sections})


def items_from_rows(
    rows,
    asset_rows,
    rendition_rows=None,
    *,
    url_prefix: str,
) -> list[CurriculumItem]:
    assets = _assets_by_item(asset_rows, rendition_rows or [], url_prefix)
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
            guidance=_with_legacy_materials(
                _guidance_document(row),
                assets.get(int(row["item_id"]), []),
            ),
            assets=assets.get(int(row["item_id"]), []),
            status=CurriculumRecordStatus(str(row["status"])),
            version=int(row["version"] or 1),
            updated_at=_as_iso(row["updated_at"]),
        )
        for row in rows
    ]


__all__ = ["assets_from_rows", "items_from_rows"]
