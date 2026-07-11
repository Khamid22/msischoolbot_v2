"""remove Teacher as an LMS portal role

Revision ID: 0008_remove_teacher_portal
Revises: 0007_lms_integrity
Create Date: 2026-07-10
"""

from alembic import op


revision = "0008_remove_teacher_portal"
down_revision = "0007_lms_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE msi_v2.accounts
        SET status = 'disabled',
            session_version = session_version + 1,
            updated_at = now()
        WHERE role = 'teacher'
          AND status <> 'disabled';
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "Teacher portal access was intentionally removed. Re-enabling accounts "
        "requires an explicit product and security decision."
    )
