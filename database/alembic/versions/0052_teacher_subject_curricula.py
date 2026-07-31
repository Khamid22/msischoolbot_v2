"""teacher subject curricula and editable supplemental lessons

Revision ID: 0052_teacher_curricula
Revises: 0051_simple_live_billing
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "0052_teacher_curricula"
down_revision = "0051_simple_live_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.supplemental_curricula (
            id BIGSERIAL PRIMARY KEY,
            subject_id BIGINT NOT NULL
                REFERENCES msi_v2.subjects(id) ON DELETE RESTRICT,
            curriculum_key TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            version BIGINT NOT NULL DEFAULT 1,
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            updated_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT supplemental_curricula_key_check
                CHECK (length(btrim(curriculum_key)) > 0),
            CONSTRAINT supplemental_curricula_title_check
                CHECK (length(btrim(title)) > 0),
            CONSTRAINT supplemental_curricula_status_check
                CHECK (status IN ('active', 'archived')),
            CONSTRAINT supplemental_curricula_version_check CHECK (version > 0),
            CONSTRAINT supplemental_curricula_subject_key_unique
                UNIQUE (subject_id, curriculum_key)
        );

        CREATE INDEX IF NOT EXISTS idx_supplemental_curricula_subject_status
        ON msi_v2.supplemental_curricula (subject_id, status, curriculum_key);

        CREATE TABLE IF NOT EXISTS msi_v2.supplemental_curriculum_items (
            id BIGSERIAL PRIMARY KEY,
            curriculum_id BIGINT NOT NULL
                REFERENCES msi_v2.supplemental_curricula(id) ON DELETE RESTRICT,
            item_order INTEGER NOT NULL,
            lesson_number TEXT NOT NULL,
            item_type TEXT NOT NULL DEFAULT 'lesson',
            title TEXT NOT NULL,
            term_label TEXT NOT NULL DEFAULT '',
            week_label TEXT NOT NULL DEFAULT '',
            specification_points TEXT NOT NULL DEFAULT '',
            book_pages TEXT NOT NULL DEFAULT '',
            lesson_count TEXT NOT NULL DEFAULT '',
            duration_hours TEXT NOT NULL DEFAULT '',
            content_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            status TEXT NOT NULL DEFAULT 'active',
            version BIGINT NOT NULL DEFAULT 1,
            archived_at TIMESTAMPTZ,
            archived_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            archive_reason TEXT NOT NULL DEFAULT '',
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            updated_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT supplemental_curriculum_items_order_check CHECK (item_order > 0),
            CONSTRAINT supplemental_curriculum_items_number_check
                CHECK (length(btrim(lesson_number)) > 0),
            CONSTRAINT supplemental_curriculum_items_title_check
                CHECK (length(btrim(title)) > 0),
            CONSTRAINT supplemental_curriculum_items_type_check
                CHECK (item_type IN ('lesson', 'exam')),
            CONSTRAINT supplemental_curriculum_items_content_check
                CHECK (jsonb_typeof(content_json) = 'array'),
            CONSTRAINT supplemental_curriculum_items_status_check
                CHECK (status IN ('active', 'archived')),
            CONSTRAINT supplemental_curriculum_items_version_check CHECK (version > 0),
            CONSTRAINT supplemental_curriculum_items_archive_check
                CHECK (
                    (status = 'archived' AND archived_at IS NOT NULL)
                    OR
                    (status = 'active' AND archived_at IS NULL)
                )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_supplemental_curriculum_items_active_order
        ON msi_v2.supplemental_curriculum_items (curriculum_id, item_order)
        WHERE status = 'active';

        CREATE INDEX IF NOT EXISTS idx_supplemental_curriculum_items_curriculum_status
        ON msi_v2.supplemental_curriculum_items (
            curriculum_id, status, item_order, id
        );

        CREATE TABLE IF NOT EXISTS msi_v2.supplemental_curriculum_assets (
            id BIGSERIAL PRIMARY KEY,
            item_id BIGINT NOT NULL
                REFERENCES msi_v2.supplemental_curriculum_items(id) ON DELETE RESTRICT,
            asset_kind TEXT NOT NULL,
            title TEXT NOT NULL,
            external_url TEXT NOT NULL DEFAULT '',
            object_key TEXT NOT NULL DEFAULT '',
            original_file_name TEXT NOT NULL DEFAULT '',
            mime_type TEXT NOT NULL DEFAULT '',
            size_bytes BIGINT NOT NULL DEFAULT 0,
            display_order INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            version BIGINT NOT NULL DEFAULT 1,
            archived_at TIMESTAMPTZ,
            archived_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT supplemental_curriculum_assets_kind_check
                CHECK (asset_kind IN ('file', 'link', 'video')),
            CONSTRAINT supplemental_curriculum_assets_title_check
                CHECK (length(btrim(title)) > 0),
            CONSTRAINT supplemental_curriculum_assets_target_check
                CHECK (
                    (asset_kind = 'file' AND length(btrim(object_key)) > 0)
                    OR
                    (
                        asset_kind IN ('link', 'video')
                        AND length(btrim(external_url)) > 0
                    )
                ),
            CONSTRAINT supplemental_curriculum_assets_size_check CHECK (size_bytes >= 0),
            CONSTRAINT supplemental_curriculum_assets_order_check CHECK (display_order > 0),
            CONSTRAINT supplemental_curriculum_assets_status_check
                CHECK (status IN ('active', 'archived')),
            CONSTRAINT supplemental_curriculum_assets_version_check CHECK (version > 0),
            CONSTRAINT supplemental_curriculum_assets_archive_check
                CHECK (
                    (status = 'archived' AND archived_at IS NOT NULL)
                    OR
                    (status = 'active' AND archived_at IS NULL)
                )
        );

        CREATE INDEX IF NOT EXISTS idx_supplemental_curriculum_assets_item_status
        ON msi_v2.supplemental_curriculum_assets (
            item_id, status, display_order, id
        );

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_curriculum_views (
            teacher_id BIGINT NOT NULL
                REFERENCES msi_v2.teachers(id) ON DELETE CASCADE,
            subject_id BIGINT NOT NULL
                REFERENCES msi_v2.subjects(id) ON DELETE CASCADE,
            curriculum_key TEXT NOT NULL,
            last_viewed_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_curriculum_views_key_check
                CHECK (length(btrim(curriculum_key)) > 0),
            PRIMARY KEY (teacher_id, subject_id, curriculum_key)
        );

        INSERT INTO msi_v2.supplemental_curricula (
            subject_id,
            curriculum_key,
            title,
            status,
            version,
            created_at,
            updated_at
        )
        SELECT
            subject.id,
            'fundamentals',
            'Fundamentals',
            'active',
            1,
            now(),
            now()
        FROM msi_v2.subjects subject
        WHERE lower(subject.subject_key) = 'english-as-a-second-language'
           OR lower(subject.subject_name) = 'english as a second language'
        ON CONFLICT (subject_id, curriculum_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.teacher_curriculum_views;
        DROP TABLE IF EXISTS msi_v2.supplemental_curriculum_assets;
        DROP TABLE IF EXISTS msi_v2.supplemental_curriculum_items;
        DROP TABLE IF EXISTS msi_v2.supplemental_curricula;
        """
    )
