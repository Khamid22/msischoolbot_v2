"""unify recruitment and Teacher Academy lifecycle profiles

Revision ID: 0027_unified_profiles
Revises: 0026_recruitment_positions
Create Date: 2026-07-17
"""

from alembic import op


revision = "0027_unified_profiles"
down_revision = "0026_recruitment_positions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidates
            ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS linked_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS is_application_received BOOLEAN
                NOT NULL DEFAULT true,
            ADD COLUMN IF NOT EXISTS profile_origin TEXT
                NOT NULL DEFAULT 'application';

        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_profile_origin_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_profile_origin_check CHECK (
                (profile_origin = 'application' AND is_application_received)
                OR
                (profile_origin = 'academy_direct' AND NOT is_application_received)
            );

        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_application_pipeline
            ON msi_v2.teacher_candidates (status, updated_at DESC, id DESC)
            WHERE is_application_received;
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_profile_origin
            ON msi_v2.teacher_candidates (profile_origin, id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_exact_phone
            ON msi_v2.teacher_candidates (
                regexp_replace(phone, '[^0-9]+', '', 'g')
            )
            WHERE phone <> '';
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_exact_email
            ON msi_v2.teacher_candidates (lower(email))
            WHERE email <> '';
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidates_linked_account
            ON msi_v2.teacher_candidates (linked_account_id)
            WHERE linked_account_id IS NOT NULL;

        COMMENT ON COLUMN msi_v2.teacher_candidates.is_application_received IS
            'True only when the lifecycle profile originated from a real recruitment application.';
        COMMENT ON COLUMN msi_v2.teacher_candidates.profile_origin IS
            'Lifecycle profile origin: application or academy_direct.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_linked_account;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_exact_email;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_exact_phone;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_profile_origin;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_application_pipeline;
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_profile_origin_check;
        ALTER TABLE msi_v2.teacher_candidates
            DROP COLUMN IF EXISTS profile_origin,
            DROP COLUMN IF EXISTS is_application_received,
            DROP COLUMN IF EXISTS linked_account_id,
            DROP COLUMN IF EXISTS email;
        """
    )
