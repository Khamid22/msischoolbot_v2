"""customer support records workspace

Revision ID: 0034_customer_support
Revises: 0033_broaden_sla_anchor_backfill
Create Date: 2026-07-21
"""

from alembic import op


revision = "0034_customer_support"
down_revision = "0033_broaden_sla_anchor_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.students
            ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

        ALTER TABLE msi_v2.parents
            ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

        ALTER TABLE msi_v2.payments
            ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS voided_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS void_reason TEXT NOT NULL DEFAULT '';

        ALTER TABLE msi_v2.students
            DROP CONSTRAINT IF EXISTS students_version_positive_check;
        ALTER TABLE msi_v2.students
            ADD CONSTRAINT students_version_positive_check CHECK (version > 0);

        ALTER TABLE msi_v2.parents
            DROP CONSTRAINT IF EXISTS parents_version_positive_check;
        ALTER TABLE msi_v2.parents
            ADD CONSTRAINT parents_version_positive_check CHECK (version > 0);

        ALTER TABLE msi_v2.payments
            DROP CONSTRAINT IF EXISTS payments_version_positive_check;
        ALTER TABLE msi_v2.payments
            ADD CONSTRAINT payments_version_positive_check CHECK (version > 0);

        CREATE INDEX IF NOT EXISTS idx_payments_student_active_due
        ON msi_v2.payments (student_id, due_date, id)
        WHERE voided_at IS NULL;

        CREATE INDEX IF NOT EXISTS idx_students_school_status_name
        ON msi_v2.students (school_id, status, lower(full_name), id);

        CREATE INDEX IF NOT EXISTS idx_parent_student_links_student_status
        ON msi_v2.parent_student_links (student_id, status, parent_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_parent_student_links_student_status;
        DROP INDEX IF EXISTS msi_v2.idx_students_school_status_name;
        DROP INDEX IF EXISTS msi_v2.idx_payments_student_active_due;

        ALTER TABLE msi_v2.payments
            DROP CONSTRAINT IF EXISTS payments_version_positive_check,
            DROP COLUMN IF EXISTS void_reason,
            DROP COLUMN IF EXISTS voided_by_account_id,
            DROP COLUMN IF EXISTS voided_at,
            DROP COLUMN IF EXISTS version;

        ALTER TABLE msi_v2.parents
            DROP CONSTRAINT IF EXISTS parents_version_positive_check,
            DROP COLUMN IF EXISTS version;

        ALTER TABLE msi_v2.students
            DROP CONSTRAINT IF EXISTS students_version_positive_check,
            DROP COLUMN IF EXISTS version;
        """
    )
