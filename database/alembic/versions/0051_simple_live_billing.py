"""simple pricing modes and revisioned live billing cycles

Revision ID: 0051_simple_live_billing
Revises: 0050_billing_cycles
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op

revision = "0051_simple_live_billing"
down_revision = "0050_billing_cycles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.student_billing_profiles
            ADD COLUMN IF NOT EXISTS pricing_mode TEXT NOT NULL DEFAULT 'per_subject',
            ADD COLUMN IF NOT EXISTS total_amount_minor BIGINT;

        ALTER TABLE msi_v2.student_billing_profiles
            DROP CONSTRAINT IF EXISTS student_billing_profiles_pricing_mode_check;
        ALTER TABLE msi_v2.student_billing_profiles
            ADD CONSTRAINT student_billing_profiles_pricing_mode_check
            CHECK (pricing_mode IN ('total', 'per_subject'));

        ALTER TABLE msi_v2.student_billing_profiles
            DROP CONSTRAINT IF EXISTS student_billing_profiles_total_amount_check;
        ALTER TABLE msi_v2.student_billing_profiles
            ADD CONSTRAINT student_billing_profiles_total_amount_check
            CHECK (
                (pricing_mode = 'total' AND total_amount_minor > 0)
                OR
                (pricing_mode = 'per_subject' AND total_amount_minor IS NULL)
            );

        CREATE TABLE IF NOT EXISTS msi_v2.student_billing_subject_prices (
            id BIGSERIAL PRIMARY KEY,
            profile_id BIGINT NOT NULL
                REFERENCES msi_v2.student_billing_profiles(id) ON DELETE RESTRICT,
            subject_id BIGINT NOT NULL
                REFERENCES msi_v2.subjects(id) ON DELETE RESTRICT,
            amount_minor BIGINT NOT NULL,
            active_from DATE NOT NULL,
            active_until DATE,
            status TEXT NOT NULL DEFAULT 'active',
            cancelled_at TIMESTAMPTZ,
            cancelled_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            cancellation_reason TEXT NOT NULL DEFAULT '',
            version BIGINT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_billing_subject_prices_amount_check
                CHECK (amount_minor > 0),
            CONSTRAINT student_billing_subject_prices_dates_check
                CHECK (active_until IS NULL OR active_until >= active_from),
            CONSTRAINT student_billing_subject_prices_status_check
                CHECK (status IN ('active', 'cancelled')),
            CONSTRAINT student_billing_subject_prices_version_check CHECK (version > 0),
            CONSTRAINT student_billing_subject_prices_version_unique
                UNIQUE (profile_id, subject_id, active_from)
        );

        CREATE INDEX IF NOT EXISTS idx_student_billing_subject_prices_active
        ON msi_v2.student_billing_subject_prices (
            profile_id, status, active_from, active_until, subject_id
        );

        INSERT INTO msi_v2.student_billing_subject_prices (
            profile_id,
            subject_id,
            amount_minor,
            active_from,
            active_until,
            status,
            cancelled_at,
            cancelled_by_staff_id,
            cancellation_reason,
            version,
            created_at,
            updated_at
        )
        SELECT
            item.profile_id,
            item.subject_id,
            sum(item.amount_minor)::bigint,
            item.active_from,
            item.active_until,
            item.status,
            max(item.cancelled_at),
            max(item.cancelled_by_staff_id),
            max(item.cancellation_reason),
            max(item.version),
            min(item.created_at),
            max(item.updated_at)
        FROM msi_v2.student_billing_items item
        GROUP BY
            item.profile_id,
            item.subject_id,
            item.active_from,
            item.active_until,
            item.status
        ON CONFLICT (profile_id, subject_id, active_from) DO NOTHING;

        ALTER TABLE msi_v2.student_billing_cycles
            ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS pricing_mode TEXT NOT NULL DEFAULT 'per_subject',
            ADD COLUMN IF NOT EXISTS superseded_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS superseded_by_cycle_id BIGINT
                REFERENCES msi_v2.student_billing_cycles(id) ON DELETE RESTRICT;

        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_state_check;
        ALTER TABLE msi_v2.student_billing_cycles
            ADD CONSTRAINT student_billing_cycles_state_check
            CHECK (
                state IN (
                    'scheduled',
                    'review_required',
                    'invoiced',
                    'satisfied',
                    'cancelled',
                    'superseded'
                )
            );

        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_pricing_mode_check;
        ALTER TABLE msi_v2.student_billing_cycles
            ADD CONSTRAINT student_billing_cycles_pricing_mode_check
            CHECK (pricing_mode IN ('total', 'per_subject'));

        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_revision_check;
        ALTER TABLE msi_v2.student_billing_cycles
            ADD CONSTRAINT student_billing_cycles_revision_check CHECK (revision > 0);

        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_superseded_check;
        ALTER TABLE msi_v2.student_billing_cycles
            ADD CONSTRAINT student_billing_cycles_superseded_check
            CHECK (
                (state = 'superseded' AND superseded_at IS NOT NULL)
                OR
                (state <> 'superseded' AND superseded_at IS NULL)
            );

        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_profile_period_unique;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_billing_cycles_revision
        ON msi_v2.student_billing_cycles (profile_id, billing_period, revision);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_billing_cycles_current
        ON msi_v2.student_billing_cycles (profile_id, billing_period)
        WHERE state <> 'superseded';

        CREATE TABLE IF NOT EXISTS msi_v2.student_billing_cycle_coverage (
            id BIGSERIAL PRIMARY KEY,
            cycle_id BIGINT NOT NULL
                REFERENCES msi_v2.student_billing_cycles(id) ON DELETE RESTRICT,
            group_id BIGINT NOT NULL
                REFERENCES msi_v2.groups(id) ON DELETE RESTRICT,
            subject_id BIGINT NOT NULL
                REFERENCES msi_v2.subjects(id) ON DELETE RESTRICT,
            group_name TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_billing_cycle_coverage_group_name_check
                CHECK (length(btrim(group_name)) > 0),
            CONSTRAINT student_billing_cycle_coverage_subject_name_check
                CHECK (length(btrim(subject_name)) > 0),
            CONSTRAINT student_billing_cycle_coverage_unique
                UNIQUE (cycle_id, group_id)
        );

        CREATE INDEX IF NOT EXISTS idx_student_billing_cycle_coverage_cycle
        ON msi_v2.student_billing_cycle_coverage (cycle_id, subject_id, group_id);

        INSERT INTO msi_v2.student_billing_cycle_coverage (
            cycle_id,
            group_id,
            subject_id,
            group_name,
            subject_name,
            created_at
        )
        SELECT DISTINCT
            item.cycle_id,
            item.group_id,
            item.subject_id,
            group_row.group_name,
            subject.subject_name,
            item.created_at
        FROM msi_v2.student_billing_cycle_items item
        JOIN msi_v2.groups group_row ON group_row.id = item.group_id
        JOIN msi_v2.subjects subject ON subject.id = item.subject_id
        WHERE item.group_id IS NOT NULL
          AND item.subject_id IS NOT NULL
        ON CONFLICT (cycle_id, group_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycle_coverage_cycle;
        DROP TABLE IF EXISTS msi_v2.student_billing_cycle_coverage;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycles_current;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycles_revision;
        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_superseded_check;
        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_revision_check;
        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_pricing_mode_check;
        ALTER TABLE msi_v2.student_billing_cycles
            DROP COLUMN IF EXISTS superseded_by_cycle_id,
            DROP COLUMN IF EXISTS superseded_at,
            DROP COLUMN IF EXISTS pricing_mode,
            DROP COLUMN IF EXISTS revision;
        ALTER TABLE msi_v2.student_billing_cycles
            ADD CONSTRAINT student_billing_cycles_profile_period_unique
            UNIQUE (profile_id, billing_period);
        ALTER TABLE msi_v2.student_billing_cycles
            DROP CONSTRAINT IF EXISTS student_billing_cycles_state_check;
        ALTER TABLE msi_v2.student_billing_cycles
            ADD CONSTRAINT student_billing_cycles_state_check
            CHECK (
                state IN (
                    'scheduled',
                    'review_required',
                    'invoiced',
                    'satisfied',
                    'cancelled'
                )
            );
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_subject_prices_active;
        DROP TABLE IF EXISTS msi_v2.student_billing_subject_prices;
        ALTER TABLE msi_v2.student_billing_profiles
            DROP CONSTRAINT IF EXISTS student_billing_profiles_total_amount_check;
        ALTER TABLE msi_v2.student_billing_profiles
            DROP CONSTRAINT IF EXISTS student_billing_profiles_pricing_mode_check;
        ALTER TABLE msi_v2.student_billing_profiles
            DROP COLUMN IF EXISTS total_amount_minor,
            DROP COLUMN IF EXISTS pricing_mode;
        """
    )
