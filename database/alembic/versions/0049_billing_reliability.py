"""non-destructive billing item lifecycle

Revision ID: 0049_billing_reliability
Revises: 0048_billing_enforcement
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op

revision = "0049_billing_reliability"
down_revision = "0048_billing_enforcement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.student_billing_items
            ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS cancelled_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS cancellation_reason TEXT NOT NULL DEFAULT '';

        ALTER TABLE msi_v2.student_billing_items
            DROP CONSTRAINT IF EXISTS student_billing_items_status_check,
            DROP CONSTRAINT IF EXISTS student_billing_items_cancellation_check;

        ALTER TABLE msi_v2.student_billing_items
            ADD CONSTRAINT student_billing_items_status_check
                CHECK (status IN ('active', 'cancelled')),
            ADD CONSTRAINT student_billing_items_cancellation_check
                CHECK (
                    (status = 'active' AND cancelled_at IS NULL)
                    OR
                    (status = 'cancelled' AND cancelled_at IS NOT NULL)
                ) NOT VALID;

        ALTER TABLE msi_v2.student_billing_items
            VALIDATE CONSTRAINT student_billing_items_cancellation_check;

        CREATE INDEX IF NOT EXISTS idx_student_billing_items_lifecycle
        ON msi_v2.student_billing_items (
            profile_id, status, active_from, active_until, group_id, id
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_items_lifecycle;
        ALTER TABLE msi_v2.student_billing_items
            DROP CONSTRAINT IF EXISTS student_billing_items_cancellation_check,
            DROP CONSTRAINT IF EXISTS student_billing_items_status_check,
            DROP COLUMN IF EXISTS cancellation_reason,
            DROP COLUMN IF EXISTS cancelled_by_staff_id,
            DROP COLUMN IF EXISTS cancelled_at,
            DROP COLUMN IF EXISTS status;
        """
    )
