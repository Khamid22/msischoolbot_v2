"""Draft read-model construction and structured media placement mapping."""

from __future__ import annotations

from datetime import datetime

from backend.modules.domains.academics.subject_curriculum import revision_repository
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumContentBlockType,
    CurriculumRevisionState,
)
from backend.modules.domains.academics.subject_curriculum.exceptions import (
    CurriculumValidationError,
)
from backend.modules.domains.academics.subject_curriculum.read_models import (
    assets_from_rows,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumContentBlock,
    CurriculumLessonDraft,
    LessonGuidanceDocument,
    LessonGuidanceSection,
)

DIRECTOR_ASSET_PREFIX = (
    "/api/v1/academic-director/academic/subject-curricula/assets"
)
MEDIA_BLOCK_TYPES = {
    CurriculumContentBlockType.IMAGE,
    CurriculumContentBlockType.VIDEO,
    CurriculumContentBlockType.AUDIO,
    CurriculumContentBlockType.DOCUMENT,
    CurriculumContentBlockType.PRESENTATION,
    CurriculumContentBlockType.EMBED,
    CurriculumContentBlockType.LINK,
}


def _as_iso(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "")


def _keyed_blocks(
    blocks: list[CurriculumContentBlock],
    *,
    prefix: str,
) -> list[CurriculumContentBlock]:
    return [
        block
        if block.block_key
        else block.model_copy(update={"block_key": f"{prefix}-{index + 1}"})
        for index, block in enumerate(blocks)
    ]


def normalize_guidance_keys(
    guidance: LessonGuidanceDocument,
) -> LessonGuidanceDocument:
    sections = [
        section.model_copy(
            update={
                "planning_blocks": _keyed_blocks(
                    section.planning_blocks,
                    prefix=f"{section.section_key}-planning",
                ),
                "teaching_blocks": _keyed_blocks(
                    section.teaching_blocks,
                    prefix=f"{section.section_key}-teaching",
                ),
            }
        )
        for section in guidance.sections
    ]
    return guidance.model_copy(
        update={
            "before_teaching": _keyed_blocks(
                guidance.before_teaching,
                prefix="before-teaching",
            ),
            "sections": sections,
        }
    )


def _with_staged_materials(
    guidance: LessonGuidanceDocument,
    assets,
) -> LessonGuidanceDocument:
    normalized = normalize_guidance_keys(guidance)
    blocks = [
        *normalized.before_teaching,
        *[
            block
            for section in normalized.sections
            for block in [*section.planning_blocks, *section.teaching_blocks]
        ],
    ]
    referenced = {
        int(block.asset_id) for block in blocks if block.asset_id is not None
    }
    missing = [asset for asset in assets if asset.asset_id not in referenced]
    if not missing:
        return normalized
    material_blocks = [
        CurriculumContentBlock(
            block_key=f"material-{asset.asset_id}",
            block_type=CurriculumContentBlockType(asset.render_kind.value),
            asset_id=asset.asset_id,
            text=asset.title,
        )
        for asset in missing
    ]
    material_section = next(
        (
            section
            for section in normalized.sections
            if section.section_key == "legacy-materials"
        ),
        None,
    )
    if material_section:
        sections = [
            section.model_copy(
                update={
                    "planning_blocks": [
                        *section.planning_blocks,
                        *material_blocks,
                    ],
                }
            )
            if section.section_key == "legacy-materials"
            else section
            for section in normalized.sections
        ]
    else:
        sections = [
            *normalized.sections,
            LessonGuidanceSection(
                section_key="legacy-materials",
                title="Materials",
                planning_blocks=material_blocks,
                teaching_blocks=[],
            ),
        ]
    return normalized.model_copy(update={"sections": sections})


def build_draft_model(conn, row) -> CurriculumLessonDraft:
    revision_id = int(row["id"])
    asset_rows = revision_repository.list_revision_asset_rows(conn, revision_id)
    asset_ids = [int(asset_row["asset_id"]) for asset_row in asset_rows]
    rendition_rows = revision_repository.list_rendition_rows(conn, asset_ids)
    assets = assets_from_rows(
        asset_rows,
        rendition_rows,
        url_prefix=DIRECTOR_ASSET_PREFIX,
    )
    guidance = LessonGuidanceDocument.model_validate(row["guidance_json"])
    return CurriculumLessonDraft(
        draft_id=revision_id,
        item_id=int(row["item_id"]),
        subject_id=int(row["subject_id"]),
        state=CurriculumRevisionState(str(row["state"])),
        title=str(row["title"] or ""),
        guidance=_with_staged_materials(guidance, assets),
        assets=assets,
        base_item_version=int(row["base_item_version"]),
        revision_version=int(row["version"]),
        is_new=str(row["item_status"]) == "draft",
        updated_at=_as_iso(row["updated_at"]),
    )


def media_placements(
    guidance: LessonGuidanceDocument,
) -> list[dict[str, object]]:
    placements: list[dict[str, object]] = []
    seen_block_keys: set[str] = set()
    seen_asset_ids: set[int] = set()

    def visit(
        blocks: list[CurriculumContentBlock],
        *,
        section_key: str,
        content_area: str,
    ) -> None:
        for block in blocks:
            if not block.block_key:
                raise CurriculumValidationError(
                    "Every lesson block requires a stable blockKey."
                )
            if block.block_key in seen_block_keys:
                raise CurriculumValidationError("Lesson block keys must be unique.")
            seen_block_keys.add(block.block_key)
            if block.block_type not in MEDIA_BLOCK_TYPES:
                continue
            asset_id = int(block.asset_id or 0)
            if asset_id in seen_asset_ids:
                raise CurriculumValidationError(
                    "A material can appear only once in a lesson revision."
                )
            seen_asset_ids.add(asset_id)
            placements.append(
                {
                    "asset_id": asset_id,
                    "block_key": block.block_key,
                    "section_key": section_key,
                    "content_area": content_area,
                }
            )

    visit(
        guidance.before_teaching,
        section_key="",
        content_area="before_teaching",
    )
    for section in guidance.sections:
        visit(
            section.planning_blocks,
            section_key=section.section_key,
            content_area="planning",
        )
        visit(
            section.teaching_blocks,
            section_key=section.section_key,
            content_area="teaching",
        )
    return placements


__all__ = ["build_draft_model", "media_placements", "normalize_guidance_keys"]
