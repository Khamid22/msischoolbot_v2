"""head of department subject scopes

Revision ID: 0004_hod_subject_scopes
Revises: 0003_shared_accounts
Create Date: 2026-07-06
"""

from alembic import op


revision = "0004_hod_subject_scopes"
down_revision = "0003_shared_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_role_check;

        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_role_check CHECK (
            role IN (
                'system_admin',
                'ceo',
                'hr_manager',
                'customer_support',
                'student',
                'teacher',
                'parent',
                'academic_director',
                'head_of_department'
            )
        );

        CREATE TABLE IF NOT EXISTS msi_v2.staff_subject_scopes (
            id BIGSERIAL PRIMARY KEY,
            account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE CASCADE,
            staff_profile_id BIGINT REFERENCES msi_v2.staff_profiles(id) ON DELETE CASCADE,
            subject_id BIGINT NOT NULL REFERENCES msi_v2.subjects(id) ON DELETE RESTRICT,
            scope_type TEXT NOT NULL DEFAULT 'head_of_department',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT staff_subject_scopes_scope_type_check CHECK (
                scope_type IN ('head_of_department')
            ),
            CONSTRAINT staff_subject_scopes_status_check CHECK (
                status IN ('active', 'disabled', 'archived')
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_staff_subject_scopes_active
        ON msi_v2.staff_subject_scopes (account_id, subject_id, scope_type)
        WHERE status = 'active';

        CREATE INDEX IF NOT EXISTS idx_staff_subject_scopes_subject_status
        ON msi_v2.staff_subject_scopes (subject_id, status);

        CREATE INDEX IF NOT EXISTS idx_staff_subject_scopes_profile_status
        ON msi_v2.staff_subject_scopes (staff_profile_id, status);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.staff_subject_scopes;

        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_role_check;

        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_role_check CHECK (
            role IN (
                'system_admin',
                'ceo',
                'hr_manager',
                'customer_support',
                'student',
                'teacher',
                'parent',
                'academic_director'
            )
        );
        """
    )
