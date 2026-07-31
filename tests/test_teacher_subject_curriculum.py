"""Subject curriculum contracts, permissions, and migration safety."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.modules.domains.academics.subject_curriculum import repository
from backend.modules.domains.academics.subject_curriculum.contracts import (
    _catalog_from_rows,
)
from backend.modules.domains.academics.subject_curriculum.domain_types import (
    CurriculumAssetKind,
    CurriculumVariant,
)
from backend.modules.domains.academics.subject_curriculum.schemas import (
    CurriculumContentBlock,
    CurriculumExternalAssetWrite,
    CurriculumItemWrite,
)


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
    lesson = CurriculumItemWrite(
        lesson_number="  F-01  ",
        title="  Study skills  ",
        content_blocks=[
            CurriculumContentBlock(block_type="paragraph", text="  Read actively.  ")
        ],
    )
    assert lesson.lesson_number == "F-01"
    assert lesson.title == "Study skills"
    assert lesson.content_blocks[0].text == "Read actively."

    with pytest.raises(ValidationError):
        CurriculumExternalAssetWrite(
            asset_kind=CurriculumAssetKind.LINK,
            title="Unsafe link",
            external_url="http://example.com/material",
        )


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
