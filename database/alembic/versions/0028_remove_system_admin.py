"""remove the system admin runtime role

Revision ID: 0028_remove_system_admin
Revises: 0027_unified_profiles
Create Date: 2026-07-20
"""

from alembic import op


revision = "0028_remove_system_admin"
down_revision = "0027_unified_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_role_check;
        """
    )

    op.execute(
        """
        UPDATE msi_v2.account_telegram_links
        SET status = 'revoked'
        WHERE account_id IN (
            SELECT id
            FROM msi_v2.accounts
            WHERE role = 'system_admin'
        );

        INSERT INTO msi_v2.audit_events (
            actor_account_id,
            event_type,
            entity_type,
            entity_id,
            detail_json,
            created_at
        )
        SELECT
            NULL,
            'identity.system_admin_retired',
            'account',
            account.id,
            jsonb_build_object(
                'previous_role', account.role,
                'previous_login', account.login,
                'reason', 'System Admin workspace removed'
            ),
            now()
        FROM msi_v2.accounts account
        WHERE account.role = 'system_admin';

        UPDATE msi_v2.staff_profiles profile
        SET status = 'archived',
            job_title = 'Retired internal operator',
            department = 'Retired',
            updated_at = now()
        WHERE profile.account_id IN (
            SELECT id
            FROM msi_v2.accounts
            WHERE role = 'system_admin'
        );

        UPDATE msi_v2.msi_staff
        SET login = 'retired_internal_' || id::text,
            password_hash = '!retired-system-admin!',
            role = 'retired',
            status = 'archived',
            telegram_user_id = NULL,
            updated_at = now()
        WHERE lower(btrim(role)) IN ('admin', 'owner', 'system_admin');

        UPDATE msi_v2.accounts
        SET login = 'retired_internal_' || id::text,
            password_hash = NULL,
            role = 'retired',
            status = 'archived',
            must_change_password = false,
            session_version = session_version + 1,
            updated_at = now()
        WHERE role = 'system_admin';

        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_role_check CHECK (
            role IN (
                'retired',
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
        """
    )

def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_role_check;

        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_role_check CHECK (
            role IN (
                'retired',
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
        """
    )
