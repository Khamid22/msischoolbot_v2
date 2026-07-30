"""auditable student billing cycles and manual invoice allocations

Revision ID: 0050_billing_cycles
Revises: 0049_billing_reliability
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op

revision = "0050_billing_cycles"
down_revision = "0049_billing_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.student_billing_cycles (
            id BIGSERIAL PRIMARY KEY,
            profile_id BIGINT NOT NULL
                REFERENCES msi_v2.student_billing_profiles(id) ON DELETE RESTRICT,
            student_id BIGINT NOT NULL
                REFERENCES msi_v2.students(id) ON DELETE RESTRICT,
            school_id BIGINT NOT NULL
                REFERENCES msi_v2.schools(id) ON DELETE RESTRICT,
            billing_period DATE NOT NULL,
            due_at TIMESTAMPTZ NOT NULL,
            currency TEXT NOT NULL DEFAULT 'UZS',
            expected_minor BIGINT NOT NULL,
            allocated_minor BIGINT NOT NULL DEFAULT 0,
            state TEXT NOT NULL DEFAULT 'scheduled',
            version BIGINT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_billing_cycles_period_check
                CHECK (billing_period = date_trunc('month', billing_period)::date),
            CONSTRAINT student_billing_cycles_currency_check CHECK (currency = 'UZS'),
            CONSTRAINT student_billing_cycles_amount_check
                CHECK (
                    expected_minor > 0
                    AND allocated_minor >= 0
                    AND allocated_minor <= expected_minor
                ),
            CONSTRAINT student_billing_cycles_state_check
                CHECK (
                    state IN (
                        'scheduled',
                        'review_required',
                        'invoiced',
                        'satisfied',
                        'cancelled'
                    )
                ),
            CONSTRAINT student_billing_cycles_version_check CHECK (version > 0),
            CONSTRAINT student_billing_cycles_profile_period_unique
                UNIQUE (profile_id, billing_period)
        );

        CREATE INDEX IF NOT EXISTS idx_student_billing_cycles_due
        ON msi_v2.student_billing_cycles (state, due_at, id);

        CREATE INDEX IF NOT EXISTS idx_student_billing_cycles_student_period
        ON msi_v2.student_billing_cycles (student_id, billing_period DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_student_billing_cycles_school_due
        ON msi_v2.student_billing_cycles (school_id, state, due_at, id);

        CREATE TABLE IF NOT EXISTS msi_v2.student_billing_cycle_items (
            id BIGSERIAL PRIMARY KEY,
            cycle_id BIGINT NOT NULL
                REFERENCES msi_v2.student_billing_cycles(id) ON DELETE RESTRICT,
            billing_item_id BIGINT
                REFERENCES msi_v2.student_billing_items(id) ON DELETE SET NULL,
            group_id BIGINT
                REFERENCES msi_v2.groups(id) ON DELETE SET NULL,
            subject_id BIGINT
                REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            description TEXT NOT NULL,
            amount_minor BIGINT NOT NULL,
            item_order SMALLINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_billing_cycle_items_description_check
                CHECK (length(btrim(description)) > 0),
            CONSTRAINT student_billing_cycle_items_amount_check CHECK (amount_minor > 0),
            CONSTRAINT student_billing_cycle_items_order_check CHECK (item_order >= 0),
            CONSTRAINT student_billing_cycle_items_order_unique
                UNIQUE (cycle_id, item_order)
        );

        CREATE INDEX IF NOT EXISTS idx_student_billing_cycle_items_cycle
        ON msi_v2.student_billing_cycle_items (cycle_id, item_order, id);

        CREATE TABLE IF NOT EXISTS msi_v2.billing_cycle_invoice_reviews (
            id BIGSERIAL PRIMARY KEY,
            cycle_id BIGINT NOT NULL
                REFERENCES msi_v2.student_billing_cycles(id) ON DELETE RESTRICT,
            invoice_id BIGINT NOT NULL
                REFERENCES msi_v2.invoices(id) ON DELETE RESTRICT,
            decision TEXT NOT NULL,
            allocated_minor BIGINT NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            reason TEXT NOT NULL,
            reviewed_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            reversed_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            reversed_at TIMESTAMPTZ,
            reversal_reason TEXT NOT NULL DEFAULT '',
            version BIGINT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT billing_cycle_invoice_reviews_decision_check
                CHECK (decision IN ('apply', 'exclude')),
            CONSTRAINT billing_cycle_invoice_reviews_status_check
                CHECK (status IN ('active', 'reversed')),
            CONSTRAINT billing_cycle_invoice_reviews_amount_check
                CHECK (
                    (decision = 'apply' AND allocated_minor > 0)
                    OR
                    (decision = 'exclude' AND allocated_minor = 0)
                ),
            CONSTRAINT billing_cycle_invoice_reviews_reason_check
                CHECK (length(btrim(reason)) >= 2),
            CONSTRAINT billing_cycle_invoice_reviews_reversal_check
                CHECK (
                    (status = 'active' AND reversed_at IS NULL)
                    OR
                    (
                        status = 'reversed'
                        AND reversed_at IS NOT NULL
                        AND length(btrim(reversal_reason)) >= 2
                    )
                ),
            CONSTRAINT billing_cycle_invoice_reviews_version_check CHECK (version > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_cycle_invoice_review_active
        ON msi_v2.billing_cycle_invoice_reviews (cycle_id, invoice_id)
        WHERE status = 'active';

        CREATE INDEX IF NOT EXISTS idx_billing_cycle_invoice_review_invoice
        ON msi_v2.billing_cycle_invoice_reviews (invoice_id, status, id);

        ALTER TABLE msi_v2.invoices
            ADD COLUMN IF NOT EXISTS billing_cycle_id BIGINT
                REFERENCES msi_v2.student_billing_cycles(id) ON DELETE RESTRICT;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_billing_cycle
        ON msi_v2.invoices (billing_cycle_id)
        WHERE billing_cycle_id IS NOT NULL AND status <> 'voided';

        INSERT INTO msi_v2.student_billing_cycles (
            profile_id,
            student_id,
            school_id,
            billing_period,
            due_at,
            currency,
            expected_minor,
            allocated_minor,
            state,
            created_at,
            updated_at
        )
        SELECT
            profile.id,
            invoice.student_id,
            profile.school_id,
            invoice.billing_period,
            (
                invoice.billing_period
                + (profile.billing_day - 1) * INTERVAL '1 day'
                + INTERVAL '5 minutes'
            ) AT TIME ZONE 'Asia/Tashkent',
            invoice.currency,
            invoice.total_minor,
            0,
            CASE
                WHEN invoice.status = 'paid' THEN 'satisfied'
                WHEN invoice.status = 'voided' THEN 'cancelled'
                ELSE 'invoiced'
            END,
            invoice.created_at,
            invoice.updated_at
        FROM msi_v2.invoices invoice
        JOIN msi_v2.student_billing_profiles profile
          ON profile.student_id = invoice.student_id
        WHERE invoice.origin = 'student_billing'
          AND invoice.invoice_kind = 'monthly'
        ON CONFLICT (profile_id, billing_period) DO NOTHING;

        INSERT INTO msi_v2.student_billing_cycle_items (
            cycle_id,
            group_id,
            subject_id,
            description,
            amount_minor,
            item_order,
            created_at
        )
        SELECT
            cycle.id,
            line.group_id,
            line.subject_id,
            line.description,
            line.amount_minor,
            row_number() OVER (
                PARTITION BY cycle.id ORDER BY line.id
            ) - 1,
            line.created_at
        FROM msi_v2.student_billing_cycles cycle
        JOIN msi_v2.invoices invoice
          ON invoice.student_id = cycle.student_id
         AND invoice.billing_period = cycle.billing_period
         AND invoice.origin = 'student_billing'
         AND invoice.invoice_kind = 'monthly'
        JOIN msi_v2.invoice_lines line ON line.invoice_id = invoice.id
        WHERE NOT EXISTS (
            SELECT 1
            FROM msi_v2.student_billing_cycle_items existing
            WHERE existing.cycle_id = cycle.id
        );

        UPDATE msi_v2.invoices invoice
        SET billing_cycle_id = cycle.id,
            updated_at = now()
        FROM msi_v2.student_billing_cycles cycle
        WHERE invoice.student_id = cycle.student_id
          AND invoice.billing_period = cycle.billing_period
          AND invoice.origin = 'student_billing'
          AND invoice.invoice_kind = 'monthly'
          AND invoice.billing_cycle_id IS NULL;

        WITH active_profiles AS (
            SELECT
                profile.*,
                CASE
                    WHEN now() < (
                        date_trunc('month', now() AT TIME ZONE 'Asia/Tashkent')
                        + (profile.billing_day - 1) * INTERVAL '1 day'
                        + INTERVAL '5 minutes'
                    ) AT TIME ZONE 'Asia/Tashkent'
                    THEN date_trunc(
                        'month',
                        now() AT TIME ZONE 'Asia/Tashkent'
                    )::date
                    ELSE (
                        date_trunc(
                            'month',
                            now() AT TIME ZONE 'Asia/Tashkent'
                        ) + INTERVAL '1 month'
                    )::date
                END AS next_period
            FROM msi_v2.student_billing_profiles profile
            JOIN msi_v2.students student ON student.id = profile.student_id
            WHERE profile.status = 'active'
              AND student.status = 'active'
        ),
        cycle_amounts AS (
            SELECT
                profile.id AS profile_id,
                profile.student_id,
                profile.school_id,
                profile.billing_day,
                profile.currency,
                profile.next_period,
                sum(item.amount_minor)::bigint AS expected_minor
            FROM active_profiles profile
            JOIN msi_v2.student_billing_items item
              ON item.profile_id = profile.id
             AND item.status = 'active'
             AND item.active_from <= (
                 profile.next_period
                 + (profile.billing_day - 1) * INTERVAL '1 day'
             )::date
             AND (
                 item.active_until IS NULL
                 OR item.active_until >= (
                     profile.next_period
                     + (profile.billing_day - 1) * INTERVAL '1 day'
                 )::date
             )
            JOIN msi_v2.group_students enrollment
              ON enrollment.student_id = profile.student_id
             AND enrollment.group_id = item.group_id
             AND enrollment.enrollment_status = 'active'
            WHERE profile.starts_on <= (
                    profile.next_period
                    + (profile.billing_day - 1) * INTERVAL '1 day'
                  )::date
              AND (
                  profile.ends_on IS NULL
                  OR profile.ends_on >= (
                      profile.next_period
                      + (profile.billing_day - 1) * INTERVAL '1 day'
                  )::date
              )
            GROUP BY
                profile.id,
                profile.student_id,
                profile.school_id,
                profile.billing_day,
                profile.currency,
                profile.next_period
        )
        INSERT INTO msi_v2.student_billing_cycles (
            profile_id,
            student_id,
            school_id,
            billing_period,
            due_at,
            currency,
            expected_minor,
            allocated_minor,
            state,
            version,
            created_at,
            updated_at
        )
        SELECT
            amount.profile_id,
            amount.student_id,
            amount.school_id,
            amount.next_period,
            (
                amount.next_period
                + (amount.billing_day - 1) * INTERVAL '1 day'
                + INTERVAL '5 minutes'
            ) AT TIME ZONE 'Asia/Tashkent',
            amount.currency,
            amount.expected_minor,
            0,
            'scheduled',
            1,
            now(),
            now()
        FROM cycle_amounts amount
        WHERE amount.expected_minor > 0
        ON CONFLICT (profile_id, billing_period) DO NOTHING;

        INSERT INTO msi_v2.student_billing_cycle_items (
            cycle_id,
            billing_item_id,
            group_id,
            subject_id,
            description,
            amount_minor,
            item_order,
            created_at
        )
        SELECT
            cycle.id,
            item.id,
            item.group_id,
            item.subject_id,
            item.description,
            item.amount_minor,
            row_number() OVER (
                PARTITION BY cycle.id ORDER BY item.id
            ) - 1,
            now()
        FROM msi_v2.student_billing_cycles cycle
        JOIN msi_v2.student_billing_items item
          ON item.profile_id = cycle.profile_id
         AND item.status = 'active'
         AND item.active_from <= (cycle.due_at AT TIME ZONE 'Asia/Tashkent')::date
         AND (
             item.active_until IS NULL
             OR item.active_until >= (cycle.due_at AT TIME ZONE 'Asia/Tashkent')::date
         )
        JOIN msi_v2.group_students enrollment
          ON enrollment.student_id = cycle.student_id
         AND enrollment.group_id = item.group_id
         AND enrollment.enrollment_status = 'active'
        WHERE NOT EXISTS (
            SELECT 1
            FROM msi_v2.student_billing_cycle_items existing
            WHERE existing.cycle_id = cycle.id
        );

        UPDATE msi_v2.student_billing_cycles cycle
        SET state = 'review_required',
            version = cycle.version + 1,
            updated_at = now()
        WHERE cycle.state = 'scheduled'
          AND EXISTS (
              SELECT 1
              FROM msi_v2.invoices invoice
              WHERE invoice.student_id = cycle.student_id
                AND invoice.billing_period = cycle.billing_period
                AND invoice.billing_cycle_id IS NULL
                AND (
                    invoice.invoice_kind = 'manual'
                    OR invoice.origin = 'legacy_migration'
                )
                AND invoice.status <> 'voided'
                AND invoice.paid_minor > 0
          );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_invoices_billing_cycle;
        ALTER TABLE msi_v2.invoices DROP COLUMN IF EXISTS billing_cycle_id;
        DROP INDEX IF EXISTS msi_v2.idx_billing_cycle_invoice_review_invoice;
        DROP INDEX IF EXISTS msi_v2.idx_billing_cycle_invoice_review_active;
        DROP TABLE IF EXISTS msi_v2.billing_cycle_invoice_reviews;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycle_items_cycle;
        DROP TABLE IF EXISTS msi_v2.student_billing_cycle_items;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycles_school_due;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycles_student_period;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_cycles_due;
        DROP TABLE IF EXISTS msi_v2.student_billing_cycles;
        """
    )
