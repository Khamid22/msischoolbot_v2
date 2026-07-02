"""lesson session source metadata

Revision ID: 0002_lesson_source_meta
Revises: 0001_msi_v2_baseline
Create Date: 2026-07-02
"""

from alembic import op


revision = "0002_lesson_source_meta"
down_revision = "0001_msi_v2_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.lesson_sessions
            ADD COLUMN IF NOT EXISTS source_key TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS source_kind TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS source_label TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS source_topic TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS source_order INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS source_file TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS source_sheet TEXT NOT NULL DEFAULT '';

        CREATE UNIQUE INDEX IF NOT EXISTS idx_lesson_sessions_source_key
        ON msi_v2.lesson_sessions (source_key)
        WHERE source_key <> '';

        CREATE INDEX IF NOT EXISTS idx_lesson_sessions_group_source_order
        ON msi_v2.lesson_sessions (group_id, source_order)
        WHERE source_order > 0;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_lesson_sessions_group_source_order;
        DROP INDEX IF EXISTS msi_v2.idx_lesson_sessions_source_key;
        ALTER TABLE msi_v2.lesson_sessions
            DROP COLUMN IF EXISTS source_sheet,
            DROP COLUMN IF EXISTS source_file,
            DROP COLUMN IF EXISTS source_order,
            DROP COLUMN IF EXISTS source_topic,
            DROP COLUMN IF EXISTS source_label,
            DROP COLUMN IF EXISTS source_kind,
            DROP COLUMN IF EXISTS source_key;
        """
    )
