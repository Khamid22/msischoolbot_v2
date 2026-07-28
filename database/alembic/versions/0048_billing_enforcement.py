"""48-hour household billing enforcement

Revision ID: 0048_billing_enforcement
Revises: 0047_unified_billing
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "0048_billing_enforcement"
down_revision = "0047_unified_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.invoice_enforcement_schedules (
            id BIGSERIAL PRIMARY KEY,
            invoice_id BIGINT NOT NULL
                REFERENCES msi_v2.invoices(id) ON DELETE RESTRICT,
            student_id BIGINT NOT NULL
                REFERENCES msi_v2.students(id) ON DELETE RESTRICT,
            state TEXT NOT NULL DEFAULT 'scheduled',
            countdown_started_at TIMESTAMPTZ NOT NULL,
            deadline_at TIMESTAMPTZ NOT NULL,
            policy_hours SMALLINT NOT NULL DEFAULT 48,
            policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
            held_at TIMESTAMPTZ,
            cleared_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            version BIGINT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT invoice_enforcement_schedule_invoice_unique UNIQUE (invoice_id),
            CONSTRAINT invoice_enforcement_schedule_state_check
                CHECK (state IN ('scheduled', 'countdown', 'held', 'cleared', 'cancelled')),
            CONSTRAINT invoice_enforcement_schedule_hours_check
                CHECK (policy_hours = 48),
            CONSTRAINT invoice_enforcement_schedule_deadline_check
                CHECK (deadline_at > countdown_started_at),
            CONSTRAINT invoice_enforcement_schedule_version_check
                CHECK (version > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_invoice_enforcement_due
        ON msi_v2.invoice_enforcement_schedules (state, deadline_at, id);

        CREATE INDEX IF NOT EXISTS idx_invoice_enforcement_student
        ON msi_v2.invoice_enforcement_schedules (student_id, state, deadline_at, id);

        CREATE TABLE IF NOT EXISTS msi_v2.billing_access_holds (
            id BIGSERIAL PRIMARY KEY,
            schedule_id BIGINT NOT NULL
                REFERENCES msi_v2.invoice_enforcement_schedules(id) ON DELETE RESTRICT,
            account_id BIGINT NOT NULL
                REFERENCES msi_v2.accounts(id) ON DELETE RESTRICT,
            target_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            released_at TIMESTAMPTZ,
            release_reason TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT billing_access_hold_target_check
                CHECK (
                    target_type IN (
                        'debtor_student',
                        'linked_parent',
                        'household_student'
                    )
                ),
            CONSTRAINT billing_access_hold_status_check
                CHECK (status IN ('active', 'released')),
            CONSTRAINT billing_access_hold_release_check
                CHECK (
                    (status = 'active' AND released_at IS NULL)
                    OR
                    (status = 'released' AND released_at IS NOT NULL)
                )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_access_hold_schedule_account
        ON msi_v2.billing_access_holds (schedule_id, account_id);

        CREATE INDEX IF NOT EXISTS idx_billing_access_hold_active_account
        ON msi_v2.billing_access_holds (account_id, schedule_id)
        WHERE status = 'active';

        CREATE TABLE IF NOT EXISTS msi_v2.billing_notification_deliveries (
            id BIGSERIAL PRIMARY KEY,
            schedule_id BIGINT NOT NULL
                REFERENCES msi_v2.invoice_enforcement_schedules(id) ON DELETE RESTRICT,
            stage TEXT NOT NULL,
            recipient_key TEXT NOT NULL,
            account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            telegram_user_id BIGINT,
            language TEXT NOT NULL DEFAULT 'uz',
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            sent_at TIMESTAMPTZ,
            last_error TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT billing_notification_stage_check
                CHECK (
                    stage IN (
                        'initial',
                        'twenty_four_hours',
                        'six_hours',
                        'held',
                        'restored'
                    )
                ),
            CONSTRAINT billing_notification_language_check
                CHECK (language IN ('uz', 'ru')),
            CONSTRAINT billing_notification_status_check
                CHECK (status IN ('pending', 'sent', 'skipped', 'failed')),
            CONSTRAINT billing_notification_attempts_check CHECK (attempts >= 0),
            CONSTRAINT billing_notification_telegram_check
                CHECK (telegram_user_id IS NULL OR telegram_user_id > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_notification_recipient_stage
        ON msi_v2.billing_notification_deliveries (
            schedule_id, stage, recipient_key
        );

        CREATE INDEX IF NOT EXISTS idx_billing_notification_status
        ON msi_v2.billing_notification_deliveries (status, updated_at, id);

        ALTER TABLE msi_v2.support_tickets
            ADD COLUMN IF NOT EXISTS requester_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL;

        ALTER TABLE msi_v2.ticket_messages
            ADD COLUMN IF NOT EXISTS author_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL;

        UPDATE msi_v2.support_tickets ticket
        SET requester_account_id = profile.account_id
        FROM msi_v2.parent_profiles profile
        WHERE ticket.parent_id = profile.parent_id
          AND ticket.requester_account_id IS NULL;

        UPDATE msi_v2.ticket_messages message
        SET author_account_id = profile.account_id
        FROM msi_v2.parent_profiles profile
        WHERE message.author_parent_id = profile.parent_id
          AND message.author_account_id IS NULL;

        CREATE INDEX IF NOT EXISTS idx_support_tickets_requester_account
        ON msi_v2.support_tickets (requester_account_id, status, updated_at DESC, id);

        CREATE INDEX IF NOT EXISTS idx_ticket_messages_author_account
        ON msi_v2.ticket_messages (author_account_id, ticket_id, created_at, id);

        INSERT INTO msi_v2.outbox_jobs (
            topic, payload, idempotency_key, status, attempts,
            max_attempts, available_at, created_at, updated_at
        )
        VALUES (
            'finance.bootstrap_billing_enforcement',
            '{}'::jsonb,
            'finance-bootstrap-billing-enforcement:v1',
            'pending',
            0,
            10,
            now(),
            now(),
            now()
        )
        ON CONFLICT (idempotency_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_ticket_messages_author_account;
        DROP INDEX IF EXISTS msi_v2.idx_support_tickets_requester_account;
        ALTER TABLE msi_v2.ticket_messages
            DROP COLUMN IF EXISTS author_account_id;
        ALTER TABLE msi_v2.support_tickets
            DROP COLUMN IF EXISTS requester_account_id;

        DROP INDEX IF EXISTS msi_v2.idx_billing_notification_status;
        DROP INDEX IF EXISTS msi_v2.idx_billing_notification_recipient_stage;
        DROP TABLE IF EXISTS msi_v2.billing_notification_deliveries;

        DROP INDEX IF EXISTS msi_v2.idx_billing_access_hold_active_account;
        DROP INDEX IF EXISTS msi_v2.idx_billing_access_hold_schedule_account;
        DROP TABLE IF EXISTS msi_v2.billing_access_holds;

        DROP INDEX IF EXISTS msi_v2.idx_invoice_enforcement_student;
        DROP INDEX IF EXISTS msi_v2.idx_invoice_enforcement_due;
        DROP TABLE IF EXISTS msi_v2.invoice_enforcement_schedules;
        """
    )
