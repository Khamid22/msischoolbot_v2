"""add durable recruitment interview sessions

Revision ID: 0025_interview_sessions
Revises: 0024_recruitment_options
Create Date: 2026-07-16
"""

from alembic import op


revision = "0025_interview_sessions"
down_revision = "0024_recruitment_options"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS started_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL;

        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_status_check;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD CONSTRAINT teacher_candidate_appointments_status_check CHECK (
                status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'no_show')
            );
        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_session_start_check,
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_session_time_check;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD CONSTRAINT teacher_candidate_appointments_session_start_check CHECK (
                status <> 'in_progress' OR started_at IS NOT NULL
            ),
            ADD CONSTRAINT teacher_candidate_appointments_session_time_check CHECK (
                started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at
            );

        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_appointments_active_type;
        CREATE UNIQUE INDEX idx_teacher_candidate_appointments_active_type
        ON msi_v2.teacher_candidate_appointments (candidate_id, appointment_type)
        WHERE status IN ('scheduled', 'in_progress');
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_appointments_in_progress
        ON msi_v2.teacher_candidate_appointments (
            candidate_id, appointment_type, started_at DESC, id DESC
        ) WHERE status = 'in_progress';
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_interview_schedule
        ON msi_v2.teacher_candidate_appointments (starts_at, id)
        WHERE status = 'scheduled' AND appointment_type = 'job_interview';

        WITH ranked AS (
            SELECT approval.id,
                   row_number() OVER (
                       PARTITION BY approval.candidate_id
                       ORDER BY approval.created_at DESC, approval.id DESC
                   ) AS actionable_rank
            FROM msi_v2.teacher_candidate_hire_approvals approval
            WHERE approval.status IN ('requested', 'approved')
        )
        UPDATE msi_v2.teacher_candidate_hire_approvals approval
        SET status = 'revoked', updated_at = now()
        FROM ranked
        WHERE approval.id = ranked.id AND ranked.actionable_rank > 1;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_hire_approvals_one_actionable
        ON msi_v2.teacher_candidate_hire_approvals (candidate_id)
        WHERE status IN ('requested', 'approved');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_hire_approvals_one_actionable;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_interview_schedule;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_appointments_in_progress;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_appointments_active_type;
        CREATE UNIQUE INDEX idx_teacher_candidate_appointments_active_type
        ON msi_v2.teacher_candidate_appointments (candidate_id, appointment_type)
        WHERE status = 'scheduled';

        UPDATE msi_v2.teacher_candidate_appointments
        SET status = 'scheduled', started_at = NULL, started_by_account_id = NULL
        WHERE status = 'in_progress';
        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_session_time_check,
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_session_start_check,
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_status_check;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD CONSTRAINT teacher_candidate_appointments_status_check CHECK (
                status IN ('scheduled', 'completed', 'cancelled', 'no_show')
            );
        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP COLUMN IF EXISTS started_by_account_id,
            DROP COLUMN IF EXISTS started_at;
        """
    )
