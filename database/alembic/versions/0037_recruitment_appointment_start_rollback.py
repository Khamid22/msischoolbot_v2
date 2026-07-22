"""preserve recruitment appointment schedule before a session starts

Revision ID: 0038_appt_start_rollback
Revises: 0037_browser_reminders
Create Date: 2026-07-22
"""

from alembic import op


revision = "0038_appt_start_rollback"
down_revision = "0037_browser_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD COLUMN IF NOT EXISTS pre_start_starts_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS pre_start_ends_at TIMESTAMPTZ;

        -- Sessions started before this migration already have the original
        -- scheduled time in their immutable start audit event. Restore that
        -- recovery point so an accidental production start can also be undone.
        WITH start_events AS (
            SELECT DISTINCT ON (appointment.id)
                   appointment.id AS appointment_id,
                   NULLIF(audit.detail_json->>'scheduled_starts_at', '')::timestamptz
                       AS scheduled_starts_at
            FROM msi_v2.teacher_candidate_appointments appointment
            JOIN msi_v2.audit_events audit
              ON audit.entity_type = 'teacher_candidate'
             AND audit.entity_id = appointment.candidate_id
             AND audit.event_type IN (
                 'candidate.interview_started',
                 'candidate.demo_lesson_started'
             )
             AND audit.detail_json->>'appointment_id' = appointment.id::text
            WHERE appointment.status = 'in_progress'
              AND NULLIF(audit.detail_json->>'scheduled_starts_at', '') IS NOT NULL
            ORDER BY appointment.id, audit.created_at DESC, audit.id DESC
        )
        UPDATE msi_v2.teacher_candidate_appointments appointment
        SET pre_start_starts_at = start_event.scheduled_starts_at
        FROM start_events start_event
        WHERE appointment.id = start_event.appointment_id
          AND appointment.status = 'in_progress'
          AND appointment.pre_start_starts_at IS NULL
          AND start_event.scheduled_starts_at IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP COLUMN IF EXISTS pre_start_ends_at,
            DROP COLUMN IF EXISTS pre_start_starts_at;
        """
    )
