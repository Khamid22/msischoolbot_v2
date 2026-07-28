"""unified billing for current and admitted students

Revision ID: 0047_unified_billing
Revises: 0046_admissions_payme
Create Date: 2026-07-28
"""

from alembic import op

revision = "0047_unified_billing"
down_revision = "0046_admissions_payme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS msi_v2.student_invoice_number_seq
            AS bigint START WITH 200000 INCREMENT BY 1 NO CYCLE;

        ALTER TABLE msi_v2.invoices
            ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'admission',
            ADD COLUMN IF NOT EXISTS legacy_payment_id BIGINT
                REFERENCES msi_v2.payments(id) ON DELETE RESTRICT;

        ALTER TABLE msi_v2.invoices
            DROP CONSTRAINT IF EXISTS invoices_origin_check;
        ALTER TABLE msi_v2.invoices
            ADD CONSTRAINT invoices_origin_check
            CHECK (origin IN ('admission', 'student_billing', 'legacy_migration'));

        ALTER TABLE msi_v2.invoices
            DROP CONSTRAINT IF EXISTS invoices_owner_check;
        ALTER TABLE msi_v2.invoices
            ADD CONSTRAINT invoices_owner_check
            CHECK (admission_id IS NOT NULL OR student_id IS NOT NULL) NOT VALID;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_legacy_payment
        ON msi_v2.invoices (legacy_payment_id)
        WHERE legacy_payment_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_student_monthly_period
        ON msi_v2.invoices (student_id, billing_period, invoice_kind)
        WHERE student_id IS NOT NULL
          AND invoice_kind = 'monthly'
          AND status <> 'voided';

        CREATE INDEX IF NOT EXISTS idx_invoices_school_queue
        ON msi_v2.invoices (status, due_date, student_id, admission_id, id);

        CREATE TABLE IF NOT EXISTS msi_v2.student_billing_profiles (
            id BIGSERIAL PRIMARY KEY,
            student_id BIGINT NOT NULL
                REFERENCES msi_v2.students(id) ON DELETE RESTRICT,
            school_id BIGINT NOT NULL
                REFERENCES msi_v2.schools(id) ON DELETE RESTRICT,
            billing_parent_id BIGINT
                REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
            billing_day SMALLINT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'UZS',
            starts_on DATE NOT NULL,
            ends_on DATE,
            status TEXT NOT NULL DEFAULT 'active',
            version BIGINT NOT NULL DEFAULT 1,
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            updated_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_billing_profiles_day_check
                CHECK (billing_day BETWEEN 1 AND 28),
            CONSTRAINT student_billing_profiles_currency_check
                CHECK (currency = 'UZS'),
            CONSTRAINT student_billing_profiles_status_check
                CHECK (status IN ('active', 'paused', 'ended')),
            CONSTRAINT student_billing_profiles_dates_check
                CHECK (ends_on IS NULL OR ends_on >= starts_on),
            CONSTRAINT student_billing_profiles_version_check CHECK (version > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_billing_profile_student
        ON msi_v2.student_billing_profiles (student_id);

        CREATE INDEX IF NOT EXISTS idx_student_billing_profiles_due
        ON msi_v2.student_billing_profiles (status, billing_day, starts_on, ends_on, id);

        CREATE TABLE IF NOT EXISTS msi_v2.student_billing_items (
            id BIGSERIAL PRIMARY KEY,
            profile_id BIGINT NOT NULL
                REFERENCES msi_v2.student_billing_profiles(id) ON DELETE RESTRICT,
            group_id BIGINT NOT NULL
                REFERENCES msi_v2.groups(id) ON DELETE RESTRICT,
            subject_id BIGINT NOT NULL
                REFERENCES msi_v2.subjects(id) ON DELETE RESTRICT,
            description TEXT NOT NULL,
            amount_minor BIGINT NOT NULL,
            active_from DATE NOT NULL,
            active_until DATE,
            version BIGINT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT student_billing_items_description_check
                CHECK (length(btrim(description)) > 0),
            CONSTRAINT student_billing_items_amount_check CHECK (amount_minor > 0),
            CONSTRAINT student_billing_items_dates_check
                CHECK (active_until IS NULL OR active_until >= active_from),
            CONSTRAINT student_billing_items_version_check CHECK (version > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_billing_item_version
        ON msi_v2.student_billing_items (profile_id, group_id, active_from);

        CREATE INDEX IF NOT EXISTS idx_student_billing_items_active
        ON msi_v2.student_billing_items (profile_id, active_from, active_until, id);

        UPDATE msi_v2.outbox_jobs
        SET topic = 'finance.generate_invoices',
            updated_at = now()
        WHERE topic = 'admissions.generate_invoices'
          AND status IN ('pending', 'retry');

        INSERT INTO msi_v2.outbox_jobs (
            topic, payload, idempotency_key, status, attempts,
            max_attempts, available_at, created_at, updated_at
        )
        VALUES (
            'finance.generate_invoices', '{}'::jsonb,
            'finance-generate-invoices:bootstrap',
            'pending', 0, 10, now(), now(), now()
        )
        ON CONFLICT (idempotency_key) DO NOTHING;

        INSERT INTO msi_v2.invoices (
            invoice_number, admission_id, student_id, parent_id,
            invoice_kind, billing_period, currency, total_minor, paid_minor,
            status, due_date, issued_at, paid_at, voided_at, void_reason,
            version, created_by_staff_id, created_at, updated_at,
            origin, legacy_payment_id
        )
        SELECT
            'LEG-' || lpad(payment.id::text, 10, '0'),
            NULL,
            payment.student_id,
            COALESCE(
                payment.parent_id,
                (
                    SELECT min(link.parent_id)
                    FROM msi_v2.parent_student_links link
                    WHERE link.student_id = payment.student_id
                      AND link.status = 'active'
                )
            ),
            'manual',
            date_trunc(
                'month',
                COALESCE(
                    payment.due_date,
                    payment.paid_at::date,
                    payment.created_at::date
                )
            )::date,
            upper(btrim(payment.currency)),
            round(payment.amount * 100)::bigint,
            CASE
                WHEN payment.voided_at IS NULL
                 AND (payment.paid_at IS NOT NULL OR payment.status = 'paid')
                THEN round(payment.amount * 100)::bigint
                ELSE 0
            END,
            CASE
                WHEN payment.voided_at IS NOT NULL OR payment.status = 'voided'
                    THEN 'voided'
                WHEN payment.paid_at IS NOT NULL OR payment.status = 'paid'
                    THEN 'paid'
                WHEN payment.due_date < CURRENT_DATE
                    THEN 'overdue'
                ELSE 'issued'
            END,
            COALESCE(payment.due_date, payment.created_at::date),
            payment.created_at,
            CASE
                WHEN payment.voided_at IS NULL
                 AND (payment.paid_at IS NOT NULL OR payment.status = 'paid')
                THEN COALESCE(payment.paid_at, payment.updated_at, payment.created_at)
                ELSE NULL
            END,
            payment.voided_at,
            payment.void_reason,
            GREATEST(payment.version, 1),
            payment.created_by_staff_id,
            payment.created_at,
            payment.updated_at,
            'legacy_migration',
            payment.id
        FROM msi_v2.payments payment
        WHERE payment.student_id IS NOT NULL
          AND payment.amount > 0
          AND upper(btrim(payment.currency)) = 'UZS'
        ON CONFLICT (legacy_payment_id)
            WHERE legacy_payment_id IS NOT NULL
        DO NOTHING;

        INSERT INTO msi_v2.invoice_lines (
            invoice_id, group_id, subject_id, description, amount_minor, created_at
        )
        SELECT
            invoice.id,
            payment.group_id,
            program.subject_id,
            COALESCE(
                NULLIF(btrim(payment.month_label), ''),
                NULLIF(btrim(subject.subject_name), ''),
                'School services'
            ),
            invoice.total_minor,
            payment.created_at
        FROM msi_v2.invoices invoice
        JOIN msi_v2.payments payment ON payment.id = invoice.legacy_payment_id
        LEFT JOIN msi_v2.groups group_row ON group_row.id = payment.group_id
        LEFT JOIN msi_v2.subject_programs program ON program.id = group_row.program_id
        LEFT JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE invoice.origin = 'legacy_migration'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.invoice_lines line WHERE line.invoice_id = invoice.id
          );

        INSERT INTO msi_v2.invoice_payments (
            invoice_id, source, method, amount_minor, currency, status,
            provider_transaction_id, reference, reason, paid_at,
            recorded_by_staff_id, created_at
        )
        SELECT
            invoice.id,
            'manual',
            'other',
            invoice.total_minor,
            invoice.currency,
            'completed',
            NULL,
            'legacy-payment:' || payment.id::text,
            'Non-destructive legacy payment migration',
            COALESCE(payment.paid_at, payment.updated_at, payment.created_at),
            payment.created_by_staff_id,
            payment.created_at
        FROM msi_v2.invoices invoice
        JOIN msi_v2.payments payment ON payment.id = invoice.legacy_payment_id
        WHERE invoice.origin = 'legacy_migration'
          AND invoice.status = 'paid'
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.invoice_payments settlement
              WHERE settlement.invoice_id = invoice.id
                AND settlement.reference = 'legacy-payment:' || payment.id::text
          );

        ALTER TABLE msi_v2.invoices VALIDATE CONSTRAINT invoices_owner_check;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_items_active;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_item_version;
        DROP TABLE IF EXISTS msi_v2.student_billing_items;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_profiles_due;
        DROP INDEX IF EXISTS msi_v2.idx_student_billing_profile_student;
        DROP TABLE IF EXISTS msi_v2.student_billing_profiles;

        DROP INDEX IF EXISTS msi_v2.idx_invoices_school_queue;
        DROP INDEX IF EXISTS msi_v2.idx_invoices_student_monthly_period;
        DROP INDEX IF EXISTS msi_v2.idx_invoices_legacy_payment;
        ALTER TABLE msi_v2.invoices
            DROP CONSTRAINT IF EXISTS invoices_owner_check,
            DROP CONSTRAINT IF EXISTS invoices_origin_check,
            DROP COLUMN IF EXISTS legacy_payment_id,
            DROP COLUMN IF EXISTS origin;
        DROP SEQUENCE IF EXISTS msi_v2.student_invoice_number_seq;
        """
    )
