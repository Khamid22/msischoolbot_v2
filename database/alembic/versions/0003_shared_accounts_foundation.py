"""shared accounts foundation

Revision ID: 0003_shared_accounts
Revises: 0002_lesson_source_meta
Create Date: 2026-07-05
"""

from alembic import op


revision = "0003_shared_accounts"
down_revision = "0002_lesson_source_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.accounts (
            id BIGSERIAL PRIMARY KEY,
            login TEXT,
            password_hash TEXT,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            full_name TEXT NOT NULL DEFAULT '',
            phone TEXT,
            legacy_source_table TEXT NOT NULL DEFAULT '',
            legacy_source_id BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT accounts_role_check CHECK (
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
            ),
            CONSTRAINT accounts_status_check CHECK (
                status IN ('active', 'pending', 'disabled', 'archived')
            ),
            CONSTRAINT accounts_login_not_blank_check CHECK (
                login IS NULL OR btrim(login) <> ''
            ),
            CONSTRAINT accounts_legacy_source_check CHECK (
                (
                    legacy_source_table = ''
                    AND legacy_source_id IS NULL
                )
                OR (
                    btrim(legacy_source_table) <> ''
                    AND legacy_source_id IS NOT NULL
                )
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_login_ci
        ON msi_v2.accounts ((lower(btrim(login))))
        WHERE login IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_legacy_source
        ON msi_v2.accounts (legacy_source_table, legacy_source_id)
        WHERE legacy_source_table <> '' AND legacy_source_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_accounts_role_status
        ON msi_v2.accounts (role, status);

        CREATE TABLE IF NOT EXISTS msi_v2.account_telegram_links (
            id BIGSERIAL PRIMARY KEY,
            account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE CASCADE,
            telegram_user_id BIGINT NOT NULL,
            telegram_username TEXT,
            linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            status TEXT NOT NULL DEFAULT 'active',
            CONSTRAINT account_telegram_links_status_check CHECK (
                status IN ('active', 'revoked')
            ),
            CONSTRAINT account_telegram_links_user_id_check CHECK (
                telegram_user_id > 0
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_account_telegram_links_user_id
        ON msi_v2.account_telegram_links (telegram_user_id);

        CREATE INDEX IF NOT EXISTS idx_account_telegram_links_account_status
        ON msi_v2.account_telegram_links (account_id, status);

        CREATE TABLE IF NOT EXISTS msi_v2.student_profiles (
            id BIGSERIAL PRIMARY KEY,
            account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE RESTRICT,
            student_id BIGINT REFERENCES msi_v2.students(id) ON DELETE RESTRICT,
            school_id BIGINT REFERENCES msi_v2.schools(id) ON DELETE SET NULL,
            student_code TEXT NOT NULL,
            class_id BIGINT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_profiles_status_check CHECK (
                status IN ('active', 'pending', 'disabled', 'archived')
            ),
            CONSTRAINT student_profiles_code_not_blank_check CHECK (
                btrim(student_code) <> ''
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_profiles_account
        ON msi_v2.student_profiles (account_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_profiles_student_id
        ON msi_v2.student_profiles (student_id)
        WHERE student_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_profiles_code_ci
        ON msi_v2.student_profiles ((upper(btrim(student_code))));

        CREATE INDEX IF NOT EXISTS idx_student_profiles_school_status
        ON msi_v2.student_profiles (school_id, status);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_profiles (
            id BIGSERIAL PRIMARY KEY,
            account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE RESTRICT,
            teacher_id BIGINT REFERENCES msi_v2.teachers(id) ON DELETE RESTRICT,
            school_id BIGINT REFERENCES msi_v2.schools(id) ON DELETE SET NULL,
            teacher_code TEXT NOT NULL,
            legacy_login TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_profiles_status_check CHECK (
                status IN ('active', 'pending', 'disabled', 'archived')
            ),
            CONSTRAINT teacher_profiles_code_check CHECK (
                teacher_code ~ '^TCH[0-9]{4}$'
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_profiles_account
        ON msi_v2.teacher_profiles (account_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_profiles_teacher_id
        ON msi_v2.teacher_profiles (teacher_id)
        WHERE teacher_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_profiles_code_ci
        ON msi_v2.teacher_profiles ((upper(btrim(teacher_code))));

        CREATE TABLE IF NOT EXISTS msi_v2.parent_profiles (
            id BIGSERIAL PRIMARY KEY,
            account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE RESTRICT,
            parent_id BIGINT REFERENCES msi_v2.parents(id) ON DELETE RESTRICT,
            telegram_username TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT parent_profiles_status_check CHECK (
                status IN ('active', 'pending', 'disabled', 'archived')
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_parent_profiles_account
        ON msi_v2.parent_profiles (account_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_parent_profiles_parent_id
        ON msi_v2.parent_profiles (parent_id)
        WHERE parent_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS msi_v2.staff_profiles (
            id BIGSERIAL PRIMARY KEY,
            account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE RESTRICT,
            staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            job_title TEXT,
            department TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT staff_profiles_status_check CHECK (
                status IN ('active', 'pending', 'disabled', 'archived')
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_staff_profiles_account
        ON msi_v2.staff_profiles (account_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_staff_profiles_staff_id
        ON msi_v2.staff_profiles (staff_id)
        WHERE staff_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_staff_profiles_department_status
        ON msi_v2.staff_profiles (department, status);

        CREATE TABLE IF NOT EXISTS msi_v2.audit_events (
            id BIGSERIAL PRIMARY KEY,
            actor_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            actor_telegram_user_id BIGINT,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL DEFAULT '',
            entity_id BIGINT,
            detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_audit_events_entity_created
        ON msi_v2.audit_events (entity_type, entity_id, created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.staff_profiles;
        DROP TABLE IF EXISTS msi_v2.parent_profiles;
        DROP TABLE IF EXISTS msi_v2.teacher_profiles;
        DROP TABLE IF EXISTS msi_v2.student_profiles;
        DROP TABLE IF EXISTS msi_v2.account_telegram_links;
        DROP TABLE IF EXISTS msi_v2.accounts;
        """
    )
