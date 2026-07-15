"""simplify the recruitment workflow and preserve correction history

Revision ID: 0019_recruitment_workflow
Revises: 0018_recruitment_appointments
Create Date: 2026-07-15
"""

from alembic import op


revision = "0019_recruitment_workflow"
down_revision = "0018_recruitment_appointments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'on_hold', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            );

        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            ADD COLUMN IF NOT EXISTS origin_stage TEXT NOT NULL DEFAULT '';
        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            DROP CONSTRAINT IF EXISTS teacher_candidate_final_decisions_origin_stage_check;
        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            ADD CONSTRAINT teacher_candidate_final_decisions_origin_stage_check CHECK (
                origin_stage = '' OR origin_stage IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'on_hold', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            );

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_holds (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL
                REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            origin_stage TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL,
            application_date DATE,
            placed_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            released_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            placed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            released_at TIMESTAMPTZ,
            CONSTRAINT teacher_candidate_holds_reason_check CHECK (length(btrim(reason)) > 0),
            CONSTRAINT teacher_candidate_holds_origin_stage_check CHECK (
                origin_stage = '' OR origin_stage IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'on_hold', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            )
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_holds_active
        ON msi_v2.teacher_candidate_holds (candidate_id)
        WHERE released_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_holds_history
        ON msi_v2.teacher_candidate_holds (candidate_id, placed_at DESC, id DESC);

        INSERT INTO msi_v2.teacher_candidate_holds (
            candidate_id, origin_stage, reason, application_date,
            placed_by_account_id, placed_at
        )
        SELECT candidate.id,
               COALESCE(NULLIF(decision.origin_stage, ''), 'new_candidate'),
               COALESCE(NULLIF(decision.reason_detail, ''), 'Migrated On Hold record'),
               candidate.application_date,
               decision.decided_by_account_id,
               COALESCE(decision.created_at, candidate.stage_changed_at, candidate.updated_at)
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN LATERAL (
            SELECT final_decision.origin_stage, final_decision.reason_detail,
                   final_decision.decided_by_account_id, final_decision.created_at
            FROM msi_v2.teacher_candidate_final_decisions final_decision
            WHERE final_decision.candidate_id = candidate.id
              AND final_decision.decision = 'on_hold'
            ORDER BY final_decision.created_at DESC, final_decision.id DESC
            LIMIT 1
        ) decision ON true
        WHERE candidate.status = 'on_hold'
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.teacher_candidate_holds existing
              WHERE existing.candidate_id = candidate.id AND existing.released_at IS NULL
          );

        ALTER TABLE msi_v2.teacher_candidate_interviews
            ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS voided_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS void_reason TEXT NOT NULL DEFAULT '';
        ALTER TABLE msi_v2.teacher_candidate_subject_tests
            ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS voided_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS void_reason TEXT NOT NULL DEFAULT '';
        ALTER TABLE msi_v2.teacher_candidate_demo_lessons
            ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS voided_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS void_reason TEXT NOT NULL DEFAULT '';

        WITH duplicate_appointments AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY candidate_id, appointment_type
                       ORDER BY updated_at DESC, id DESC
                   ) AS duplicate_rank
            FROM msi_v2.teacher_candidate_appointments
            WHERE status = 'scheduled'
        )
        UPDATE msi_v2.teacher_candidate_appointments appointment
        SET status = 'cancelled',
            cancellation_reason = 'Superseded during recruitment workflow migration.',
            cancelled_at = now(),
            updated_at = now(),
            version = version + 1
        FROM duplicate_appointments duplicate
        WHERE appointment.id = duplicate.id AND duplicate.duplicate_rank > 1;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_appointments_active_type
        ON msi_v2.teacher_candidate_appointments (candidate_id, appointment_type)
        WHERE status = 'scheduled';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_appointments_active_type;

        ALTER TABLE msi_v2.teacher_candidate_demo_lessons
            DROP COLUMN IF EXISTS void_reason,
            DROP COLUMN IF EXISTS voided_by_account_id,
            DROP COLUMN IF EXISTS voided_at;
        ALTER TABLE msi_v2.teacher_candidate_subject_tests
            DROP COLUMN IF EXISTS void_reason,
            DROP COLUMN IF EXISTS voided_by_account_id,
            DROP COLUMN IF EXISTS voided_at;
        ALTER TABLE msi_v2.teacher_candidate_interviews
            DROP COLUMN IF EXISTS void_reason,
            DROP COLUMN IF EXISTS voided_by_account_id,
            DROP COLUMN IF EXISTS voided_at;

        DROP TABLE IF EXISTS msi_v2.teacher_candidate_holds;

        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            DROP CONSTRAINT IF EXISTS teacher_candidate_final_decisions_origin_stage_check,
            DROP COLUMN IF EXISTS origin_stage;

        UPDATE msi_v2.teacher_candidates
        SET status = 'new_candidate',
            stage_changed_at = COALESCE(stage_changed_at, updated_at, created_at),
            version = version + 1
        WHERE status = 'responded';

        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'on_hold', 'candidate_withdrew', 'trash_bin'
                )
            );
        """
    )
