"""Subject curriculum contracts, permissions, and migration safety."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from backend.application.modules import build_job_handler_registry
from backend.modules.domains.academics.subject_curriculum import repository
from backend.modules.domains.academics.subject_curriculum.contracts import (
    _catalog_from_rows,
)
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumAssetRenderKind,
    CurriculumVariant,
)
from backend.modules.domains.academics.subject_curriculum.exceptions import (
    CurriculumValidationError,
)
from backend.modules.domains.academics.subject_curriculum.job_handlers import (
    CONVERT_PRESENTATION_HANDLER,
)
from backend.modules.domains.academics.subject_curriculum.media import (
    CONVERT_PRESENTATION_TOPIC,
    normalize_external_url,
)
from backend.modules.domains.academics.subject_curriculum.presentation_conversion import (
    MAX_PRESENTATION_SLIDES,
    _page_count,
)
from backend.modules.domains.academics.subject_curriculum.read_models import (
    items_from_rows,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumContentBlock,
    CurriculumExternalAssetWrite,
    FundamentalsLessonWrite,
    LessonGuidanceDocument,
    LessonGuidanceSection,
)
from backend.platform.storage.r2 import _curriculum_file_signature_matches


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _Connection:
    def __init__(self):
        self.sql = ""
        self.params = ()

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params or ()
        return _Cursor([])


def _variant_row(key: str, *, program_id=None, curriculum_id=None):
    updated_at = datetime(2026, 7, 31, tzinfo=UTC)
    return {
        "subject_id": 9,
        "subject_key": "english-as-a-second-language",
        "subject_name": "English as a Second Language",
        "subject_short": "Eng",
        "curriculum_key": key,
        "program_id": program_id,
        "curriculum_id": curriculum_id,
        "title": "Fundamentals" if key == "fundamentals" else "Primary Curriculum",
        "item_count": 0,
        "lesson_count": 0,
        "exam_count": 0,
        "version": 1,
        "updated_at": updated_at,
        "last_viewed_at": None,
    }


def test_esl_catalog_exposes_fundamentals_before_primary_with_camel_case():
    catalog = _catalog_from_rows(
        [
            _variant_row("fundamentals", curriculum_id=12),
            _variant_row("primary", program_id=4),
        ],
        is_director=False,
    )

    assert [variant.curriculum_key for variant in catalog.subjects[0].variants] == [
        CurriculumVariant.FUNDAMENTALS,
        CurriculumVariant.PRIMARY,
    ]
    payload = catalog.model_dump(mode="json", by_alias=True)
    assert payload["subjects"][0]["subjectId"] == 9
    assert payload["subjects"][0]["variants"][0]["curriculumKey"] == "fundamentals"
    assert payload["subjects"][0]["variants"][0]["hasUpdates"] is True


def test_lesson_write_models_normalize_content_and_reject_insecure_assets():
    lesson = FundamentalsLessonWrite(
        title="  Study skills  ",
        guidance=LessonGuidanceDocument(
            overview="  Prepare students to read with purpose.  ",
            tags=[" Study skills ", "Study skills"],
            before_teaching=[
                CurriculumContentBlock(block_type="paragraph", text="  Open the text.  ")
            ],
            sections=[
                LessonGuidanceSection(
                    section_key="guided-reading",
                    title="  Guided reading  ",
                    planning_blocks=[
                        CurriculumContentBlock(
                            block_type="bullets",
                            text="  Read actively.  ",
                        )
                    ],
                )
            ],
        ),
    )
    assert lesson.title == "Study skills"
    assert lesson.guidance.overview == "Prepare students to read with purpose."
    assert lesson.guidance.tags == ["Study skills"]
    assert lesson.guidance.sections[0].title == "Guided reading"
    assert lesson.guidance.sections[0].planning_blocks[0].text == "Read actively."
    payload = lesson.model_dump(mode="json", by_alias=True)
    assert payload["guidance"]["durationMinutes"] == 0
    assert payload["guidance"]["sections"][0]["sectionKey"] == "guided-reading"

    with pytest.raises(ValidationError):
        CurriculumExternalAssetWrite(
            asset_kind=CurriculumAssetKind.LINK,
            title="Unsafe link",
            external_url="http://example.com/material",
        )


def test_media_blocks_require_assets_and_keep_stable_camel_case_keys():
    with pytest.raises(ValidationError):
        CurriculumContentBlock(
            block_type="presentation",
            block_key="lesson-slides",
            text="Deck",
        )

    block = CurriculumContentBlock(
        block_type="presentation",
        block_key="lesson-slides",
        text="Model dialogue",
        asset_id=17,
    )

    assert block.model_dump(mode="json", by_alias=True) == {
        "blockType": "presentation",
        "blockKey": "lesson-slides",
        "text": "Model dialogue",
        "assetId": 17,
    }


@pytest.mark.parametrize(
    ("source_url", "render_kind", "expected"),
    [
        (
            "https://youtu.be/abc123",
            CurriculumAssetRenderKind.EMBED,
            "https://www.youtube-nocookie.com/embed/abc123",
        ),
        (
            "https://docs.google.com/presentation/d/deck123/edit",
            CurriculumAssetRenderKind.EMBED,
            "https://docs.google.com/presentation/d/deck123/embed"
            "?start=false&loop=false&delayms=3000",
        ),
        (
            "https://example.com/resource#section",
            CurriculumAssetRenderKind.LINK,
            "https://example.com/resource",
        ),
    ],
)
def test_external_materials_are_normalized_for_safe_rendering(
    source_url,
    render_kind,
    expected,
):
    assert normalize_external_url(source_url, render_kind=render_kind) == expected

    with pytest.raises(CurriculumValidationError, match="Embeds support"):
        normalize_external_url(
            "https://example.com/iframe",
            render_kind=CurriculumAssetRenderKind.EMBED,
        )


def test_presentation_worker_topic_is_registered_and_limits_slide_count(monkeypatch, tmp_path):
    assert CONVERT_PRESENTATION_HANDLER.topic == CONVERT_PRESENTATION_TOPIC
    assert CONVERT_PRESENTATION_TOPIC == "academics.convert_curriculum_presentation"
    assert (
        build_job_handler_registry().handler_for(CONVERT_PRESENTATION_TOPIC)
        is not None
    )

    monkeypatch.setattr(
        "backend.modules.domains.academics.subject_curriculum."
        "presentation_conversion._run",
        lambda _command: f"Pages: {MAX_PRESENTATION_SLIDES + 1}\n",
    )
    monkeypatch.setattr(
        "backend.modules.domains.academics.subject_curriculum."
        "presentation_conversion._binary",
        lambda name: name,
    )
    with pytest.raises(RuntimeError, match="at most 200 slides"):
        _page_count(tmp_path / "deck.pdf")


def test_curriculum_upload_signature_validation_rejects_renamed_payloads(tmp_path):
    valid_pdf = tmp_path / "lesson.pdf"
    valid_pdf.write_bytes(b"%PDF-1.7\n")
    renamed_html = tmp_path / "unsafe.pdf"
    renamed_html.write_bytes(b"<html><script>alert(1)</script></html>")
    valid_deck = tmp_path / "lesson.pptx"
    with ZipFile(valid_deck, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("ppt/presentation.xml", "<presentation />")

    assert _curriculum_file_signature_matches(valid_pdf, ".pdf") is True
    assert _curriculum_file_signature_matches(renamed_html, ".pdf") is False
    assert _curriculum_file_signature_matches(valid_deck, ".pptx") is True


def test_legacy_fundamentals_blocks_map_into_the_constructor_without_data_loss():
    row = {
        "item_id": 8,
        "item_order": 1,
        "lesson_number": "F-01",
        "item_type": "lesson",
        "title": "Legacy lesson",
        "term_label": "",
        "week_label": "",
        "specification_points": "Legacy overview",
        "book_pages": "",
        "lesson_count": "",
        "duration_hours": "",
        "content_json": [
            {"block_type": "heading", "text": "Starter"},
            {"block_type": "paragraph", "text": "Welcome the class."},
        ],
        "guidance_json": {
            "overview": "",
            "tags": [],
            "duration_minutes": 0,
            "before_teaching": [],
            "sections": [],
        },
        "status": "active",
        "version": 1,
        "updated_at": datetime(2026, 7, 31, tzinfo=UTC),
    }

    item = items_from_rows([row], [], url_prefix="/assets")[0]

    assert item.guidance.overview == "Legacy overview"
    assert item.guidance.sections[0].title == "Starter"
    assert item.guidance.sections[0].planning_blocks[0].text == "Welcome the class."


def test_legacy_write_payload_is_upgraded_without_exposing_row_fields():
    lesson = FundamentalsLessonWrite.model_validate(
        {
            "lessonNumber": "F-01",
            "itemType": "lesson",
            "title": "Legacy editor",
            "specificationPoints": "Legacy overview",
            "bookPages": "Not used",
            "contentBlocks": [
                {"blockType": "heading", "text": "Practice"},
                {"blockType": "paragraph", "text": "Model the activity."},
            ],
        }
    )

    assert lesson.guidance.overview == "Legacy overview"
    assert lesson.guidance.sections[0].title == "Practice"
    assert lesson.guidance.sections[0].planning_blocks[0].text == "Model the activity."
    assert "bookPages" not in lesson.model_dump(mode="json", by_alias=True)


def test_teacher_curriculum_query_requires_active_teacher_and_subject_assignment():
    connection = _Connection()

    repository.list_teacher_curriculum_variant_rows(connection, 77)

    assert "teacher.status = 'active'" in connection.sql
    assert "teacher_subject.status = 'active'" in connection.sql
    assert "subject.status = 'active'" in connection.sql
    assert connection.params == (77, 77, 77)


def test_curriculum_migration_is_additive_and_seeds_only_supplemental_data():
    source = Path(
        "database/alembic/versions/0052_teacher_subject_curricula.py"
    ).read_text(encoding="utf-8")
    upgrade = source.split("def downgrade", 1)[0].upper()

    assert 'revision = "0052_teacher_curricula"' in source
    assert 'down_revision = "0051_simple_live_billing"' in source
    assert "CREATE TABLE IF NOT EXISTS MSI_V2.SUPPLEMENTAL_CURRICULA" in upgrade
    assert "CREATE TABLE IF NOT EXISTS MSI_V2.TEACHER_CURRICULUM_VIEWS" in upgrade
    assert "'fundamentals'" in source
    assert "DELETE FROM" not in upgrade
    assert "TRUNCATE " not in upgrade
    assert "DROP TABLE" not in upgrade

    constructor_source = Path(
        "database/alembic/versions/0053_fundamentals_lesson_constructor.py"
    ).read_text(encoding="utf-8")
    constructor_upgrade = constructor_source.split("def downgrade", 1)[0].upper()
    assert 'revision = "0053_lesson_constructor"' in constructor_source
    assert 'down_revision = "0052_teacher_curricula"' in constructor_source
    assert "ADD COLUMN IF NOT EXISTS GUIDANCE_JSON JSONB" in constructor_upgrade
    assert "DELETE FROM" not in constructor_upgrade
    assert "TRUNCATE " not in constructor_upgrade

    revision_source = Path(
        "database/alembic/versions/0054_rich_fundamentals_constructor.py"
    ).read_text(encoding="utf-8")
    revision_upgrade = revision_source.split("def downgrade", 1)[0].upper()
    assert 'revision = "0054_rich_fundamentals"' in revision_source
    assert 'down_revision = "0053_lesson_constructor"' in revision_source
    assert "SUPPLEMENTAL_CURRICULUM_ITEM_REVISIONS" in revision_upgrade
    assert "SUPPLEMENTAL_CURRICULUM_REVISION_ASSETS" in revision_upgrade
    assert "SUPPLEMENTAL_CURRICULUM_ASSET_RENDITIONS" in revision_upgrade
    assert "PUBLISHED_REVISION_ID" in revision_upgrade
    assert "BETWEEN 1 AND 200" in revision_upgrade
    assert "DELETE FROM" not in revision_upgrade
    assert "TRUNCATE " not in revision_upgrade
    assert "DROP TABLE" not in revision_upgrade


def test_primary_curriculum_has_no_mutation_repository():
    public_names = set(repository.__all__)
    mutation_names = {
        name for name in public_names if name.startswith(("insert_", "update_", "archive_"))
    }

    assert all("primary" not in name for name in mutation_names)


def test_reorder_preserves_positive_database_order_values():
    connection = _Connection()

    repository.reorder_active_items(connection, 4, [])

    assert "item_order = -" not in connection.sql
    assert "item_order = item_order + boundary.offset" in connection.sql
