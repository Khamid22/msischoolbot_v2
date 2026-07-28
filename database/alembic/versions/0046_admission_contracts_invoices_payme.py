"""admission contracts, invoices, and Payme transactions

Revision ID: 0046_admissions_payme
Revises: 0045_customer_support_ticket_sla
Create Date: 2026-07-28
"""

from alembic import op

revision = "0046_admissions_payme"
down_revision = "0045_customer_support_ticket_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS msi_v2.admission_invoice_number_seq
            AS bigint START WITH 100000 INCREMENT BY 1 NO CYCLE;
        CREATE SEQUENCE IF NOT EXISTS msi_v2.legacy_enrollment_id_seq
            AS bigint START WITH 9000000000 INCREMENT BY 1 NO CYCLE;
        CREATE SEQUENCE IF NOT EXISTS msi_v2.legacy_dashboard_id_seq
            AS bigint START WITH 9000000000 INCREMENT BY 1 NO CYCLE;

        SELECT setval(
            'msi_v2.legacy_enrollment_id_seq',
            GREATEST(
                COALESCE(MAX(legacy_enrollment_id), 0) + 1,
                9000000000
            ),
            false
        )
        FROM msi_v2.group_students;

        SELECT setval(
            'msi_v2.legacy_dashboard_id_seq',
            GREATEST(
                COALESCE(MAX(legacy_public_dashboard_id), 0) + 1,
                9000000000
            ),
            false
        )
        FROM msi_v2.group_students;

        CREATE TABLE IF NOT EXISTS msi_v2.admissions (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL
                REFERENCES msi_v2.schools(id) ON DELETE RESTRICT,
            student_full_name TEXT NOT NULL,
            student_phone TEXT NOT NULL DEFAULT '',
            parent_full_name TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            parent_telegram_username TEXT NOT NULL DEFAULT '',
            preferred_language TEXT NOT NULL DEFAULT 'uz',
            service_start_date DATE,
            first_due_date DATE NOT NULL,
            billing_day SMALLINT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'UZS',
            status TEXT NOT NULL DEFAULT 'draft',
            version BIGINT NOT NULL DEFAULT 1,
            activated_student_id BIGINT
                REFERENCES msi_v2.students(id) ON DELETE SET NULL,
            activated_parent_id BIGINT
                REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            activated_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            cancellation_reason TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT admissions_student_name_check
                CHECK (length(btrim(student_full_name)) >= 2),
            CONSTRAINT admissions_parent_name_check
                CHECK (length(btrim(parent_full_name)) >= 2),
            CONSTRAINT admissions_parent_phone_check
                CHECK (length(btrim(parent_phone)) >= 5),
            CONSTRAINT admissions_language_check
                CHECK (preferred_language IN ('uz', 'ru')),
            CONSTRAINT admissions_billing_day_check
                CHECK (billing_day BETWEEN 1 AND 28),
            CONSTRAINT admissions_currency_check
                CHECK (currency = 'UZS'),
            CONSTRAINT admissions_status_check
                CHECK (
                    status IN (
                        'draft', 'contract_sent', 'contract_submitted',
                        'awaiting_payment', 'active', 'cancelled',
                        'expired', 'payment_review'
                    )
                ),
            CONSTRAINT admissions_version_check CHECK (version > 0)
        );

        CREATE TABLE IF NOT EXISTS msi_v2.admission_group_selections (
            admission_id BIGINT NOT NULL
                REFERENCES msi_v2.admissions(id) ON DELETE CASCADE,
            group_id BIGINT NOT NULL
                REFERENCES msi_v2.groups(id) ON DELETE RESTRICT,
            subject_id BIGINT NOT NULL
                REFERENCES msi_v2.subjects(id) ON DELETE RESTRICT,
            monthly_amount_minor BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (admission_id, group_id),
            CONSTRAINT admission_group_amount_check
                CHECK (monthly_amount_minor > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_group_one_subject
        ON msi_v2.admission_group_selections (admission_id, subject_id);

        CREATE TABLE IF NOT EXISTS msi_v2.admission_access_tokens (
            id BIGSERIAL PRIMARY KEY,
            admission_id BIGINT NOT NULL
                REFERENCES msi_v2.admissions(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ,
            last_accessed_at TIMESTAMPTZ,
            rate_window_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            rate_window_requests INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT admission_token_hash_check
                CHECK (length(token_hash) = 64),
            CONSTRAINT admission_token_rate_count_check
                CHECK (rate_window_requests >= 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_access_token_hash
        ON msi_v2.admission_access_tokens (token_hash);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_access_one_active
        ON msi_v2.admission_access_tokens (admission_id)
        WHERE revoked_at IS NULL;

        CREATE TABLE IF NOT EXISTS msi_v2.admission_contracts (
            id BIGSERIAL PRIMARY KEY,
            admission_id BIGINT NOT NULL
                REFERENCES msi_v2.admissions(id) ON DELETE CASCADE,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft',
            original_object_key TEXT NOT NULL,
            original_file_name TEXT NOT NULL,
            original_mime_type TEXT NOT NULL,
            original_size_bytes BIGINT NOT NULL,
            signed_object_key TEXT NOT NULL DEFAULT '',
            signed_file_name TEXT NOT NULL DEFAULT '',
            signed_mime_type TEXT NOT NULL DEFAULT '',
            signed_size_bytes BIGINT,
            submitted_at TIMESTAMPTZ,
            reviewed_at TIMESTAMPTZ,
            reviewed_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            rejection_reason TEXT NOT NULL DEFAULT '',
            superseded_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT admission_contract_status_check
                CHECK (
                    status IN (
                        'draft', 'sent', 'submitted',
                        'accepted', 'rejected', 'superseded'
                    )
                ),
            CONSTRAINT admission_contract_version_check CHECK (version > 0),
            CONSTRAINT admission_contract_original_size_check
                CHECK (original_size_bytes > 0),
            CONSTRAINT admission_contract_signed_size_check
                CHECK (signed_size_bytes IS NULL OR signed_size_bytes > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_contract_version
        ON msi_v2.admission_contracts (admission_id, version);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_contract_current
        ON msi_v2.admission_contracts (admission_id)
        WHERE superseded_at IS NULL;

        CREATE TABLE IF NOT EXISTS msi_v2.invoices (
            id BIGSERIAL PRIMARY KEY,
            invoice_number TEXT NOT NULL,
            admission_id BIGINT
                REFERENCES msi_v2.admissions(id) ON DELETE RESTRICT,
            student_id BIGINT
                REFERENCES msi_v2.students(id) ON DELETE SET NULL,
            parent_id BIGINT
                REFERENCES msi_v2.parents(id) ON DELETE SET NULL,
            invoice_kind TEXT NOT NULL DEFAULT 'first',
            billing_period DATE NOT NULL,
            currency TEXT NOT NULL DEFAULT 'UZS',
            total_minor BIGINT NOT NULL,
            paid_minor BIGINT NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            due_date DATE NOT NULL,
            issued_at TIMESTAMPTZ,
            paid_at TIMESTAMPTZ,
            voided_at TIMESTAMPTZ,
            void_reason TEXT NOT NULL DEFAULT '',
            version BIGINT NOT NULL DEFAULT 1,
            created_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT invoices_number_check
                CHECK (length(btrim(invoice_number)) > 0),
            CONSTRAINT invoices_kind_check
                CHECK (invoice_kind IN ('first', 'monthly', 'manual')),
            CONSTRAINT invoices_currency_check CHECK (currency = 'UZS'),
            CONSTRAINT invoices_total_check CHECK (total_minor > 0),
            CONSTRAINT invoices_paid_check
                CHECK (paid_minor >= 0 AND paid_minor <= total_minor),
            CONSTRAINT invoices_status_check
                CHECK (
                    status IN (
                        'draft', 'issued', 'partially_paid',
                        'paid', 'overdue', 'voided'
                    )
                ),
            CONSTRAINT invoices_version_check CHECK (version > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_number
        ON msi_v2.invoices (invoice_number);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_admission_period_kind
        ON msi_v2.invoices (admission_id, billing_period, invoice_kind)
        WHERE admission_id IS NOT NULL AND status <> 'voided';

        CREATE INDEX IF NOT EXISTS idx_invoices_admission_status_due
        ON msi_v2.invoices (admission_id, status, due_date, id);

        CREATE INDEX IF NOT EXISTS idx_invoices_student_status_due
        ON msi_v2.invoices (student_id, status, due_date, id)
        WHERE student_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS msi_v2.invoice_lines (
            id BIGSERIAL PRIMARY KEY,
            invoice_id BIGINT NOT NULL
                REFERENCES msi_v2.invoices(id) ON DELETE CASCADE,
            group_id BIGINT
                REFERENCES msi_v2.groups(id) ON DELETE SET NULL,
            subject_id BIGINT
                REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            description TEXT NOT NULL,
            amount_minor BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT invoice_lines_description_check
                CHECK (length(btrim(description)) > 0),
            CONSTRAINT invoice_lines_amount_check CHECK (amount_minor > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice
        ON msi_v2.invoice_lines (invoice_id, id);

        CREATE TABLE IF NOT EXISTS msi_v2.invoice_payments (
            id BIGSERIAL PRIMARY KEY,
            invoice_id BIGINT NOT NULL
                REFERENCES msi_v2.invoices(id) ON DELETE RESTRICT,
            source TEXT NOT NULL,
            method TEXT NOT NULL,
            amount_minor BIGINT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'UZS',
            status TEXT NOT NULL DEFAULT 'completed',
            provider_transaction_id TEXT,
            reference TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            paid_at TIMESTAMPTZ NOT NULL,
            recorded_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            reversed_at TIMESTAMPTZ,
            reversed_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            reversal_reason TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT invoice_payments_source_check
                CHECK (source IN ('payme', 'manual')),
            CONSTRAINT invoice_payments_method_check
                CHECK (
                    method IN (
                        'payme', 'cash', 'bank_transfer',
                        'card_terminal', 'other'
                    )
                ),
            CONSTRAINT invoice_payments_amount_check CHECK (amount_minor > 0),
            CONSTRAINT invoice_payments_currency_check CHECK (currency = 'UZS'),
            CONSTRAINT invoice_payments_status_check
                CHECK (
                    status IN (
                        'pending', 'completed', 'cancelled',
                        'refunded', 'failed', 'reversed'
                    )
                )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_payment_provider_transaction
        ON msi_v2.invoice_payments (source, provider_transaction_id)
        WHERE provider_transaction_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_invoice_payments_invoice_status
        ON msi_v2.invoice_payments (invoice_id, status, paid_at, id);

        CREATE TABLE IF NOT EXISTS msi_v2.payme_transactions (
            id BIGSERIAL PRIMARY KEY,
            provider_transaction_id TEXT NOT NULL,
            invoice_id BIGINT NOT NULL
                REFERENCES msi_v2.invoices(id) ON DELETE RESTRICT,
            provider_created_at_ms BIGINT NOT NULL,
            amount_minor BIGINT NOT NULL,
            state SMALLINT NOT NULL,
            reason SMALLINT,
            create_time_ms BIGINT NOT NULL,
            perform_time_ms BIGINT NOT NULL DEFAULT 0,
            cancel_time_ms BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT payme_transaction_id_check
                CHECK (length(btrim(provider_transaction_id)) > 0),
            CONSTRAINT payme_transaction_amount_check CHECK (amount_minor > 0),
            CONSTRAINT payme_transaction_state_check
                CHECK (state IN (-2, -1, 1, 2)),
            CONSTRAINT payme_transaction_times_check
                CHECK (
                    provider_created_at_ms > 0
                    AND create_time_ms > 0
                    AND perform_time_ms >= 0
                    AND cancel_time_ms >= 0
                )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_payme_transaction_provider_id
        ON msi_v2.payme_transactions (provider_transaction_id);

        CREATE INDEX IF NOT EXISTS idx_payme_transaction_invoice_state
        ON msi_v2.payme_transactions (invoice_id, state, id);

        CREATE INDEX IF NOT EXISTS idx_payme_transaction_statement
        ON msi_v2.payme_transactions (provider_created_at_ms, id);

        CREATE INDEX IF NOT EXISTS idx_admissions_school_status_updated
        ON msi_v2.admissions (school_id, status, updated_at DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_admissions_billing_due
        ON msi_v2.admissions (first_due_date, id)
        WHERE status IN ('contract_submitted', 'awaiting_payment', 'active');

        INSERT INTO msi_v2.outbox_jobs (
            topic, payload, idempotency_key, status, attempts,
            max_attempts, available_at, created_at, updated_at
        )
        VALUES (
            'admissions.generate_invoices', '{}'::jsonb,
            'admissions-generate-invoices:bootstrap',
            'pending', 0, 10, now(), now(), now()
        )
        ON CONFLICT (idempotency_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.payme_transactions;
        DROP TABLE IF EXISTS msi_v2.invoice_payments;
        DROP TABLE IF EXISTS msi_v2.invoice_lines;
        DROP TABLE IF EXISTS msi_v2.invoices;
        DROP TABLE IF EXISTS msi_v2.admission_contracts;
        DROP TABLE IF EXISTS msi_v2.admission_access_tokens;
        DROP TABLE IF EXISTS msi_v2.admission_group_selections;
        DROP TABLE IF EXISTS msi_v2.admissions;
        DROP SEQUENCE IF EXISTS msi_v2.legacy_dashboard_id_seq;
        DROP SEQUENCE IF EXISTS msi_v2.legacy_enrollment_id_seq;
        DROP SEQUENCE IF EXISTS msi_v2.admission_invoice_number_seq;
        """
    )
