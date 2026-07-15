"""add a recoverable recruitment candidate trash bin

Revision ID: 0017_candidate_trash_bin
Revises: 0016_recruitment_settings
Create Date: 2026-07-15
"""

from alembic import op


revision = "0017_candidate_trash_bin"
down_revision = "0016_recruitment_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'on_hold', 'candidate_withdrew', 'trash_bin'
                )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE msi_v2.teacher_candidates
        SET status = 'new_candidate',
            stage_changed_at = COALESCE(stage_changed_at, updated_at, created_at),
            version = version + 1
        WHERE status = 'trash_bin';

        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'on_hold', 'candidate_withdrew'
                )
            );
        """
    )
