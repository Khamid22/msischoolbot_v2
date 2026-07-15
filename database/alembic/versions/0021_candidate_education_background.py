"""add candidate education background

Revision ID: 0021_candidate_education
Revises: 0020_recruitment_notifications
Create Date: 2026-07-15
"""

from alembic import op


revision = "0021_candidate_education"
down_revision = "0020_recruitment_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidates
            ADD COLUMN IF NOT EXISTS education_background TEXT NOT NULL DEFAULT '';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidates
            DROP COLUMN IF EXISTS education_background;
        """
    )
