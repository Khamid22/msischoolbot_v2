"""versioned Fundamentals drafts and private media renditions

Revision ID: 0054_rich_fundamentals
Revises: 0053_lesson_constructor
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "0054_rich_fundamentals"
down_revision = "0053_lesson_constructor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.supplemental_curriculum_items
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_items_status_check;

        ALTER TABLE msi_v2.supplemental_curriculum_items
        ADD CONSTRAINT supplemental_curriculum_items_status_check
        CHECK (status IN ('draft', 'active', 'archived'));

        ALTER TABLE msi_v2.supplemental_curriculum_items
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_items_archive_check;

        ALTER TABLE msi_v2.supplemental_curriculum_items
        ADD CONSTRAINT supplemental_curriculum_items_archive_check
        CHECK (
            (status = 'archived' AND archived_at IS NOT NULL)
            OR (status IN ('draft', 'active') AND archived_at IS NULL)
        );

        CREATE TABLE IF NOT EXISTS msi_v2.supplemental_curriculum_item_revisions (
            id BIGSERIAL PRIMARY KEY,
            item_id BIGINT NOT NULL
                REFERENCES msi_v2.supplemental_curriculum_items(id) ON DELETE RESTRICT,
            revision_number BIGINT NOT NULL,
            state TEXT NOT NULL,
            title TEXT NOT NULL,
            guidance_json JSONB NOT NULL,
            base_item_version BIGINT NOT NULL,
            version BIGINT NOT NULL DEFAULT 1,
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            updated_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            published_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            published_at TIMESTAMPTZ,
            abandoned_at TIMESTAMPTZ,
            CONSTRAINT supplemental_curriculum_revisions_number_check
                CHECK (revision_number > 0),
            CONSTRAINT supplemental_curriculum_revisions_state_check
                CHECK (state IN ('draft', 'published', 'superseded', 'abandoned')),
            CONSTRAINT supplemental_curriculum_revisions_title_check
                CHECK (length(btrim(title)) > 0),
            CONSTRAINT supplemental_curriculum_revisions_guidance_check
                CHECK (jsonb_typeof(guidance_json) = 'object'),
            CONSTRAINT supplemental_curriculum_revisions_base_version_check
                CHECK (base_item_version > 0),
            CONSTRAINT supplemental_curriculum_revisions_version_check
                CHECK (version > 0),
            CONSTRAINT supplemental_curriculum_revisions_item_number_unique
                UNIQUE (item_id, revision_number)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_supplemental_curriculum_revisions_one_draft
        ON msi_v2.supplemental_curriculum_item_revisions (item_id)
        WHERE state = 'draft';

        CREATE INDEX IF NOT EXISTS idx_supplemental_curriculum_revisions_item_state
        ON msi_v2.supplemental_curriculum_item_revisions (
            item_id, state, revision_number DESC
        );

        ALTER TABLE msi_v2.supplemental_curriculum_items
        ADD COLUMN IF NOT EXISTS published_revision_id BIGINT
            REFERENCES msi_v2.supplemental_curriculum_item_revisions(id)
            ON DELETE RESTRICT;

        ALTER TABLE msi_v2.supplemental_curriculum_assets
        ADD COLUMN IF NOT EXISTS render_kind TEXT NOT NULL DEFAULT 'document',
        ADD COLUMN IF NOT EXISTS conversion_status TEXT NOT NULL DEFAULT 'not_required',
        ADD COLUMN IF NOT EXISTS conversion_error TEXT NOT NULL DEFAULT '',
        ADD COLUMN IF NOT EXISTS conversion_attempts INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS converted_at TIMESTAMPTZ;

        UPDATE msi_v2.supplemental_curriculum_assets
        SET render_kind = CASE
                WHEN asset_kind = 'link' THEN 'link'
                WHEN asset_kind = 'video' THEN 'link'
                WHEN mime_type LIKE 'image/%' THEN 'image'
                WHEN mime_type LIKE 'video/%' THEN 'video'
                WHEN mime_type LIKE 'audio/%' THEN 'audio'
                WHEN mime_type IN (
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                ) THEN 'presentation'
                ELSE 'document'
            END,
            conversion_status = CASE
                WHEN mime_type IN (
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                ) THEN 'failed'
                ELSE 'not_required'
            END,
            conversion_error = CASE
                WHEN mime_type IN (
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                ) THEN 'Conversion is required; open a lesson draft and retry.'
                ELSE ''
            END
        WHERE render_kind = 'document'
          AND conversion_status = 'not_required';

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'supplemental_curriculum_assets_render_kind_check'
                  AND conrelid = 'msi_v2.supplemental_curriculum_assets'::regclass
            ) THEN
                ALTER TABLE msi_v2.supplemental_curriculum_assets
                ADD CONSTRAINT supplemental_curriculum_assets_render_kind_check
                CHECK (
                    render_kind IN (
                        'image', 'video', 'audio', 'document',
                        'presentation', 'embed', 'link'
                    )
                );
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'supplemental_curriculum_assets_conversion_check'
                  AND conrelid = 'msi_v2.supplemental_curriculum_assets'::regclass
            ) THEN
                ALTER TABLE msi_v2.supplemental_curriculum_assets
                ADD CONSTRAINT supplemental_curriculum_assets_conversion_check
                CHECK (
                    conversion_status IN (
                        'not_required', 'pending', 'processing', 'ready', 'failed'
                    )
                );
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'supplemental_curriculum_assets_attempts_check'
                  AND conrelid = 'msi_v2.supplemental_curriculum_assets'::regclass
            ) THEN
                ALTER TABLE msi_v2.supplemental_curriculum_assets
                ADD CONSTRAINT supplemental_curriculum_assets_attempts_check
                CHECK (conversion_attempts >= 0);
            END IF;
        END
        $$;

        CREATE TABLE IF NOT EXISTS msi_v2.supplemental_curriculum_revision_assets (
            id BIGSERIAL PRIMARY KEY,
            revision_id BIGINT NOT NULL
                REFERENCES msi_v2.supplemental_curriculum_item_revisions(id)
                ON DELETE RESTRICT,
            asset_id BIGINT NOT NULL
                REFERENCES msi_v2.supplemental_curriculum_assets(id)
                ON DELETE RESTRICT,
            block_key TEXT NOT NULL,
            section_key TEXT NOT NULL DEFAULT '',
            content_area TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            version BIGINT NOT NULL DEFAULT 1,
            archived_at TIMESTAMPTZ,
            archived_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT supplemental_curriculum_revision_assets_block_check
                CHECK (length(btrim(block_key)) > 0),
            CONSTRAINT supplemental_curriculum_revision_assets_area_check
                CHECK (
                    content_area IN (
                        'before_teaching', 'planning', 'teaching', 'materials'
                    )
                ),
            CONSTRAINT supplemental_curriculum_revision_assets_order_check
                CHECK (display_order > 0),
            CONSTRAINT supplemental_curriculum_revision_assets_status_check
                CHECK (status IN ('active', 'archived')),
            CONSTRAINT supplemental_curriculum_revision_assets_version_check
                CHECK (version > 0),
            CONSTRAINT supplemental_curriculum_revision_assets_unique
                UNIQUE (revision_id, asset_id, block_key)
        );

        CREATE INDEX IF NOT EXISTS idx_curriculum_revision_assets_revision_status
        ON msi_v2.supplemental_curriculum_revision_assets (
            revision_id, status, content_area, display_order, id
        );

        CREATE TABLE IF NOT EXISTS msi_v2.supplemental_curriculum_asset_renditions (
            id BIGSERIAL PRIMARY KEY,
            asset_id BIGINT NOT NULL
                REFERENCES msi_v2.supplemental_curriculum_assets(id)
                ON DELETE RESTRICT,
            rendition_kind TEXT NOT NULL DEFAULT 'slide_image',
            slide_number INTEGER NOT NULL,
            object_key TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes BIGINT NOT NULL DEFAULT 0,
            width INTEGER NOT NULL DEFAULT 0,
            height INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT supplemental_curriculum_renditions_kind_check
                CHECK (rendition_kind IN ('slide_image')),
            CONSTRAINT supplemental_curriculum_renditions_slide_check
                CHECK (slide_number BETWEEN 1 AND 200),
            CONSTRAINT supplemental_curriculum_renditions_object_check
                CHECK (length(btrim(object_key)) > 0),
            CONSTRAINT supplemental_curriculum_renditions_size_check
                CHECK (size_bytes >= 0),
            CONSTRAINT supplemental_curriculum_renditions_asset_slide_unique
                UNIQUE (asset_id, rendition_kind, slide_number)
        );

        CREATE INDEX IF NOT EXISTS idx_curriculum_asset_renditions_asset_slide
        ON msi_v2.supplemental_curriculum_asset_renditions (
            asset_id, slide_number
        );

        INSERT INTO msi_v2.supplemental_curriculum_item_revisions (
            item_id, revision_number, state, title, guidance_json,
            base_item_version, version, created_by_staff_id, updated_by_staff_id,
            published_by_staff_id, created_at, updated_at, published_at
        )
        SELECT
            item.id, 1, 'published', item.title, item.guidance_json,
            item.version, 1, item.created_by_staff_id, item.updated_by_staff_id,
            item.updated_by_staff_id, item.created_at, item.updated_at, item.updated_at
        FROM msi_v2.supplemental_curriculum_items item
        ON CONFLICT (item_id, revision_number) DO NOTHING;

        UPDATE msi_v2.supplemental_curriculum_items item
        SET published_revision_id = revision.id
        FROM msi_v2.supplemental_curriculum_item_revisions revision
        WHERE revision.item_id = item.id
          AND revision.revision_number = 1
          AND item.published_revision_id IS NULL;

        INSERT INTO msi_v2.supplemental_curriculum_revision_assets (
            revision_id, asset_id, block_key, section_key,
            content_area, display_order, status, version, created_at, updated_at
        )
        SELECT
            item.published_revision_id,
            asset.id,
            'legacy-material-' || asset.id::text,
            'legacy-materials',
            'materials',
            asset.display_order,
            asset.status,
            asset.version,
            asset.created_at,
            asset.updated_at
        FROM msi_v2.supplemental_curriculum_assets asset
        JOIN msi_v2.supplemental_curriculum_items item ON item.id = asset.item_id
        WHERE item.published_revision_id IS NOT NULL
        ON CONFLICT (revision_id, asset_id, block_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.supplemental_curriculum_items
        DROP COLUMN IF EXISTS published_revision_id;

        DROP TABLE IF EXISTS msi_v2.supplemental_curriculum_asset_renditions;
        DROP TABLE IF EXISTS msi_v2.supplemental_curriculum_revision_assets;
        DROP TABLE IF EXISTS msi_v2.supplemental_curriculum_item_revisions;

        ALTER TABLE msi_v2.supplemental_curriculum_assets
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_assets_attempts_check,
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_assets_conversion_check,
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_assets_render_kind_check,
        DROP COLUMN IF EXISTS converted_at,
        DROP COLUMN IF EXISTS conversion_attempts,
        DROP COLUMN IF EXISTS conversion_error,
        DROP COLUMN IF EXISTS conversion_status,
        DROP COLUMN IF EXISTS render_kind;

        ALTER TABLE msi_v2.supplemental_curriculum_items
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_items_archive_check,
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_items_status_check;

        ALTER TABLE msi_v2.supplemental_curriculum_items
        ADD CONSTRAINT supplemental_curriculum_items_status_check
        CHECK (status IN ('active', 'archived'));

        ALTER TABLE msi_v2.supplemental_curriculum_items
        ADD CONSTRAINT supplemental_curriculum_items_archive_check
        CHECK (
            (status = 'archived' AND archived_at IS NOT NULL)
            OR (status = 'active' AND archived_at IS NULL)
        );
        """
    )
