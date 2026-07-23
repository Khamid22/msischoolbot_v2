"""give Test & Demo its own pipeline color

Revision ID: 0039_test_demo_color
Revises: 0038_appt_start_rollback
Create Date: 2026-07-23
"""

from alembic import op


revision = "0039_test_demo_color"
down_revision = "0038_appt_start_rollback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE msi_v2.teacher_recruitment_pipeline_stages
        SET color_token = 'orange',
            version = version + 1,
            updated_at = now()
        WHERE stage_key = 'test_and_demo'
          AND stage_kind = 'system'
          AND color_token <> 'orange';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE msi_v2.teacher_recruitment_pipeline_stages
        SET color_token = 'amber',
            version = version + 1,
            updated_at = now()
        WHERE stage_key = 'test_and_demo'
          AND stage_kind = 'system'
          AND color_token = 'orange';
        """
    )
