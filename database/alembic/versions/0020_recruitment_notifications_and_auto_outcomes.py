"""add recruitment notifications, Telegram links, and automatic outcome metadata

Revision ID: 0020_recruitment_notifications
Revises: 0019_recruitment_workflow
Create Date: 2026-07-15
"""

from alembic import op


revision = "0020_recruitment_notifications"
down_revision = "0019_recruitment_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT false;

        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, is_active, sort_order, is_system,
            created_at, updated_at
        ) VALUES
            ('rejection_reason', 'failed_job_interview', 'Failed job interview', true, -30, true, now(), now()),
            ('rejection_reason', 'failed_subject_test', 'Failed subject test', true, -20, true, now(), now()),
            ('rejection_reason', 'failed_demo_lesson', 'Failed demo lesson', true, -10, true, now(), now())
        ON CONFLICT (category, value) DO UPDATE SET
            label = excluded.label,
            is_active = true,
            is_system = true,
            updated_at = now();

        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            ADD COLUMN IF NOT EXISTS is_system_generated BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS source_evaluation_type TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS source_evaluation_id BIGINT,
            ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS voided_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS void_reason TEXT NOT NULL DEFAULT '';

        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            DROP CONSTRAINT IF EXISTS teacher_candidate_final_decisions_source_evaluation_type_check;
        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            ADD CONSTRAINT teacher_candidate_final_decisions_source_evaluation_type_check CHECK (
                source_evaluation_type IN ('', 'interview', 'subject_test', 'demo')
            );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_system_decision_evaluation
        ON msi_v2.teacher_candidate_final_decisions (
            source_evaluation_type, source_evaluation_id
        )
        WHERE is_system_generated = true
          AND source_evaluation_id IS NOT NULL
          AND voided_at IS NULL;

        ALTER TABLE msi_v2.account_telegram_links
            ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

        WITH duplicate_links AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY account_id
                       ORDER BY linked_at DESC, id DESC
                   ) AS link_rank
            FROM msi_v2.account_telegram_links
            WHERE status = 'active'
        )
        UPDATE msi_v2.account_telegram_links link
        SET status = 'revoked', revoked_at = now(), updated_at = now()
        FROM duplicate_links duplicate
        WHERE link.id = duplicate.id AND duplicate.link_rank > 1;

        DROP INDEX IF EXISTS msi_v2.idx_account_telegram_links_user_id;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_account_telegram_links_active_identity
        ON msi_v2.account_telegram_links (telegram_user_id)
        WHERE status = 'active';
        CREATE UNIQUE INDEX IF NOT EXISTS idx_account_telegram_links_active_account
        ON msi_v2.account_telegram_links (account_id)
        WHERE status = 'active';

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_notifications (
            id BIGSERIAL PRIMARY KEY,
            recipient_account_id BIGINT NOT NULL
                REFERENCES msi_v2.accounts(id) ON DELETE CASCADE,
            candidate_id BIGINT
                REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            appointment_id BIGINT
                REFERENCES msi_v2.teacher_candidate_appointments(id) ON DELETE SET NULL,
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            action_url TEXT NOT NULL DEFAULT '',
            deliver_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            read_at TIMESTAMPTZ,
            telegram_status TEXT NOT NULL DEFAULT 'pending',
            telegram_attempts INTEGER NOT NULL DEFAULT 0,
            telegram_next_attempt_at TIMESTAMPTZ,
            telegram_sent_at TIMESTAMPTZ,
            telegram_last_error TEXT NOT NULL DEFAULT '',
            telegram_locked_at TIMESTAMPTZ,
            dedupe_key TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_recruitment_notifications_type_check CHECK (
                notification_type IN (
                    'demo_assigned', 'demo_rescheduled', 'demo_cancelled',
                    'demo_no_show', 'demo_completed', 'demo_evaluated',
                    'demo_reminder_24h', 'demo_reminder_1h', 'demo_link_summary'
                )
            ),
            CONSTRAINT teacher_recruitment_notifications_telegram_status_check CHECK (
                telegram_status IN (
                    'pending', 'waiting_link', 'sending', 'sent', 'failed', 'cancelled'
                )
            ),
            CONSTRAINT teacher_recruitment_notifications_attempts_check CHECK (
                telegram_attempts >= 0
            )
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_notifications_dedupe
        ON msi_v2.teacher_recruitment_notifications (dedupe_key);
        CREATE INDEX IF NOT EXISTS idx_teacher_recruitment_notifications_recipient_unread
        ON msi_v2.teacher_recruitment_notifications (recipient_account_id, created_at DESC, id DESC)
        WHERE read_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_teacher_recruitment_notifications_delivery
        ON msi_v2.teacher_recruitment_notifications (
            COALESCE(telegram_next_attempt_at, deliver_at), id
        )
        WHERE telegram_status IN ('pending', 'failed', 'waiting_link');
        CREATE INDEX IF NOT EXISTS idx_teacher_recruitment_notifications_appointment
        ON msi_v2.teacher_recruitment_notifications (appointment_id, notification_type);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.teacher_recruitment_notifications;
        DROP INDEX IF EXISTS msi_v2.idx_account_telegram_links_active_account;
        DROP INDEX IF EXISTS msi_v2.idx_account_telegram_links_active_identity;
        DELETE FROM msi_v2.account_telegram_links older
        USING msi_v2.account_telegram_links newer
        WHERE older.telegram_user_id = newer.telegram_user_id AND older.id < newer.id;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_account_telegram_links_user_id
        ON msi_v2.account_telegram_links (telegram_user_id);
        ALTER TABLE msi_v2.account_telegram_links
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS revoked_at;

        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_system_decision_evaluation;
        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            DROP CONSTRAINT IF EXISTS teacher_candidate_final_decisions_source_evaluation_type_check,
            DROP COLUMN IF EXISTS void_reason,
            DROP COLUMN IF EXISTS voided_by_account_id,
            DROP COLUMN IF EXISTS voided_at,
            DROP COLUMN IF EXISTS source_evaluation_id,
            DROP COLUMN IF EXISTS source_evaluation_type,
            DROP COLUMN IF EXISTS is_system_generated;

        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP COLUMN IF EXISTS is_system;
        """
    )
