"""standalone HR access and Academic Director decision queue

Revision ID: 0014_hr_decision_queue
Revises: 0013_teacher_recruitment
Create Date: 2026-07-15
"""

from alembic import op


revision = "0014_hr_decision_queue"
down_revision = "0013_teacher_recruitment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_hire_approvals_actionable
        ON msi_v2.teacher_candidate_hire_approvals (candidate_id, created_at DESC, id DESC)
        WHERE status IN ('requested', 'approved');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_hire_approvals_actionable;
        """
    )
