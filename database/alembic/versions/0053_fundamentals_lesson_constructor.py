"""typed Fundamentals lesson-constructor documents

Revision ID: 0053_lesson_constructor
Revises: 0052_teacher_curricula
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "0053_lesson_constructor"
down_revision = "0052_teacher_curricula"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.supplemental_curriculum_items
        ADD COLUMN IF NOT EXISTS guidance_json JSONB NOT NULL
        DEFAULT '{
          "overview": "",
          "tags": [],
          "duration_minutes": 0,
          "before_teaching": [],
          "sections": []
        }'::jsonb;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'supplemental_curriculum_items_guidance_check'
                  AND conrelid = 'msi_v2.supplemental_curriculum_items'::regclass
            ) THEN
                ALTER TABLE msi_v2.supplemental_curriculum_items
                ADD CONSTRAINT supplemental_curriculum_items_guidance_check
                CHECK (jsonb_typeof(guidance_json) = 'object');
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.supplemental_curriculum_items
        DROP CONSTRAINT IF EXISTS supplemental_curriculum_items_guidance_check;

        ALTER TABLE msi_v2.supplemental_curriculum_items
        DROP COLUMN IF EXISTS guidance_json;
        """
    )
