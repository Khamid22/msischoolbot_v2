"""add browser recruitment appointment reminders

Revision ID: 0037_browser_reminders
Revises: 0036_future_stage_anchor
Create Date: 2026-07-22
"""

from alembic import op


revision = "0037_browser_reminders"
down_revision = "0036_future_stage_anchor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_reminder_config (
            id SMALLINT PRIMARY KEY DEFAULT 1,
            lead_minutes SMALLINT NOT NULL DEFAULT 15,
            version BIGINT NOT NULL DEFAULT 1,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_recruitment_reminder_config_singleton_check CHECK (id = 1),
            CONSTRAINT teacher_recruitment_reminder_config_lead_check CHECK (
                lead_minutes BETWEEN 5 AND 120
            ),
            CONSTRAINT teacher_recruitment_reminder_config_version_check CHECK (version > 0)
        );
        INSERT INTO msi_v2.teacher_recruitment_reminder_config (id, lead_minutes)
        VALUES (1, 15)
        ON CONFLICT (id) DO NOTHING;

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_browser_preferences (
            account_id BIGINT PRIMARY KEY REFERENCES msi_v2.accounts(id) ON DELETE CASCADE,
            enabled BOOLEAN NOT NULL DEFAULT false,
            version BIGINT NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_recruitment_browser_preferences_version_check CHECK (version > 0)
        );

        ALTER TABLE msi_v2.teacher_recruitment_notifications
            ADD COLUMN IF NOT EXISTS browser_delivered_at TIMESTAMPTZ;
        ALTER TABLE msi_v2.teacher_recruitment_notifications
            DROP CONSTRAINT IF EXISTS teacher_recruitment_notifications_type_check;
        ALTER TABLE msi_v2.teacher_recruitment_notifications
            ADD CONSTRAINT teacher_recruitment_notifications_type_check CHECK (
                notification_type IN (
                    'demo_assigned', 'demo_rescheduled', 'demo_cancelled',
                    'demo_no_show', 'demo_completed', 'demo_evaluated',
                    'demo_reminder_24h', 'demo_reminder_1h', 'demo_link_summary',
                    'appointment_reminder'
                )
            );

        -- Recruitment delivery is browser-only from this revision onward.
        UPDATE msi_v2.teacher_recruitment_notifications
        SET telegram_status = 'cancelled', telegram_next_attempt_at = NULL,
            telegram_locked_at = NULL, updated_at = now()
        WHERE telegram_status IN ('pending', 'waiting_link', 'sending', 'failed');

        CREATE INDEX IF NOT EXISTS idx_teacher_recruitment_notifications_browser_due
        ON msi_v2.teacher_recruitment_notifications (recipient_account_id, deliver_at, id)
        WHERE notification_type = 'appointment_reminder'
          AND browser_delivered_at IS NULL
          AND read_at IS NULL;

        -- Backfill one 15-minute reminder for every eligible future appointment.
        WITH recipients AS (
            SELECT appointment.id AS appointment_id,
                   COALESCE(appointment.created_by_account_id, appointment.responsible_account_id) AS recipient_account_id
            FROM msi_v2.teacher_candidate_appointments appointment
            WHERE appointment.status = 'scheduled'
            UNION
            SELECT appointment.id, appointment.responsible_account_id
            FROM msi_v2.teacher_candidate_appointments appointment
            WHERE appointment.status = 'scheduled'
              AND appointment.appointment_type = 'demo_lesson'
        )
        INSERT INTO msi_v2.teacher_recruitment_notifications (
            recipient_account_id, candidate_id, appointment_id,
            notification_type, title, body, action_url, deliver_at,
            telegram_status, telegram_next_attempt_at, dedupe_key,
            created_at, updated_at
        )
        SELECT recipient.id,
               candidate.id,
               appointment.id,
               'appointment_reminder',
               CASE appointment.appointment_type
                   WHEN 'job_interview' THEN 'Job interview in 15 minutes'
                   ELSE 'Demo lesson in 15 minutes'
               END,
               candidate.full_name || ' · ' ||
                   to_char(appointment.starts_at AT TIME ZONE 'Asia/Tashkent', 'Mon DD, YYYY HH12:MI AM'),
               CASE recipient.role
                   WHEN 'hr_manager' THEN '/hr-manager/candidates/' || candidate.id || '?tab=evaluations'
                   WHEN 'head_of_department' THEN '/head-of-departments/recruitment/candidates/' || candidate.id || '?tab=evaluations'
                   ELSE '/academic-director/recruitment/candidates/' || candidate.id || '?tab=evaluations'
               END,
               appointment.starts_at - interval '15 minutes',
               'cancelled',
               NULL,
               'appointment:' || appointment.id || ':appointment_reminder:' || appointment.version || ':' || recipient.id,
               now(),
               now()
        FROM recipients target
        JOIN msi_v2.teacher_candidate_appointments appointment ON appointment.id = target.appointment_id
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = appointment.candidate_id
        JOIN msi_v2.accounts recipient ON recipient.id = target.recipient_account_id
        WHERE target.recipient_account_id IS NOT NULL
          AND recipient.status = 'active'
          AND recipient.role IN ('hr_manager', 'academic_director', 'head_of_department')
          AND appointment.starts_at - interval '15 minutes' > now()
        ON CONFLICT (dedupe_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_notifications_browser_due;
        DELETE FROM msi_v2.teacher_recruitment_notifications
        WHERE notification_type = 'appointment_reminder';
        ALTER TABLE msi_v2.teacher_recruitment_notifications
            DROP CONSTRAINT IF EXISTS teacher_recruitment_notifications_type_check;
        ALTER TABLE msi_v2.teacher_recruitment_notifications
            ADD CONSTRAINT teacher_recruitment_notifications_type_check CHECK (
                notification_type IN (
                    'demo_assigned', 'demo_rescheduled', 'demo_cancelled',
                    'demo_no_show', 'demo_completed', 'demo_evaluated',
                    'demo_reminder_24h', 'demo_reminder_1h', 'demo_link_summary'
                )
            );
        ALTER TABLE msi_v2.teacher_recruitment_notifications
            DROP COLUMN IF EXISTS browser_delivered_at;
        DROP TABLE IF EXISTS msi_v2.teacher_recruitment_browser_preferences;
        DROP TABLE IF EXISTS msi_v2.teacher_recruitment_reminder_config;
        """
    )
