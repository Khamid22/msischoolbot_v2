"""add recruitment interview and demo appointments

Revision ID: 0018_recruitment_appointments
Revises: 0017_candidate_trash_bin
Create Date: 2026-07-15
"""

from alembic import op


revision = "0018_recruitment_appointments"
down_revision = "0017_candidate_trash_bin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_appointments (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            appointment_type TEXT NOT NULL,
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ NOT NULL,
            responsible_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            appointment_format TEXT NOT NULL DEFAULT '',
            location_or_link TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'scheduled',
            version INTEGER NOT NULL DEFAULT 1,
            cancellation_reason TEXT NOT NULL DEFAULT '',
            completed_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            no_show_at TIMESTAMPTZ,
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_appointments_type_check CHECK (
                appointment_type IN ('job_interview', 'demo_lesson')
            ),
            CONSTRAINT teacher_candidate_appointments_status_check CHECK (
                status IN ('scheduled', 'completed', 'cancelled', 'no_show')
            ),
            CONSTRAINT teacher_candidate_appointments_time_check CHECK (ends_at > starts_at),
            CONSTRAINT teacher_candidate_appointments_version_check CHECK (version > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_appointments_candidate_start
        ON msi_v2.teacher_candidate_appointments (candidate_id, starts_at DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_appointments_schedule
        ON msi_v2.teacher_candidate_appointments (status, starts_at ASC, id ASC);

        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_appointments_responsible
        ON msi_v2.teacher_candidate_appointments (
            responsible_account_id, status, starts_at ASC, ends_at ASC
        );

        ALTER TABLE msi_v2.teacher_candidate_interviews
            ADD COLUMN IF NOT EXISTS appointment_id BIGINT
                REFERENCES msi_v2.teacher_candidate_appointments(id) ON DELETE SET NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_interviews_appointment
        ON msi_v2.teacher_candidate_interviews (appointment_id)
        WHERE appointment_id IS NOT NULL;

        ALTER TABLE msi_v2.teacher_candidate_demo_lessons
            ADD COLUMN IF NOT EXISTS appointment_id BIGINT
                REFERENCES msi_v2.teacher_candidate_appointments(id) ON DELETE SET NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_demo_lessons_appointment
        ON msi_v2.teacher_candidate_demo_lessons (appointment_id)
        WHERE appointment_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_demo_lessons_appointment;
        ALTER TABLE msi_v2.teacher_candidate_demo_lessons DROP COLUMN IF EXISTS appointment_id;

        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_interviews_appointment;
        ALTER TABLE msi_v2.teacher_candidate_interviews DROP COLUMN IF EXISTS appointment_id;

        DROP TABLE IF EXISTS msi_v2.teacher_candidate_appointments;
        """
    )
