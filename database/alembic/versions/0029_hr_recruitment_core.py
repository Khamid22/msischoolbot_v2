"""canonical HR recruitment workflow and reporting dates

Revision ID: 0029_hr_recruitment_core
Revises: 0028_remove_system_admin
Create Date: 2026-07-20
"""

from alembic import op


revision = "0029_hr_recruitment_core"
down_revision = "0028_remove_system_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teachers
            ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ;

        UPDATE msi_v2.teachers teacher
        SET activated_at = COALESCE(
            teacher.activated_at,
            (
                SELECT MIN(history.entered_at)
                FROM msi_v2.teacher_candidate_stage_history history
                WHERE history.candidate_id = teacher.recruitment_candidate_id
                  AND history.stage = 'active_teacher'
            ),
            (
                SELECT MIN(decision.created_at)
                FROM msi_v2.teacher_candidate_final_decisions decision
                WHERE decision.candidate_id = teacher.recruitment_candidate_id
                  AND decision.decision = 'active_teacher'
                  AND decision.voided_at IS NULL
            ),
            teacher.created_at
        )
        WHERE teacher.status = 'active';

        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_time_check;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ALTER COLUMN ends_at DROP NOT NULL;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD CONSTRAINT teacher_candidate_appointments_time_check CHECK (
                ends_at IS NULL OR ends_at > starts_at
            );

        UPDATE msi_v2.teacher_candidate_interviews
        SET interview_at = created_at
        WHERE interview_at IS NULL;
        UPDATE msi_v2.teacher_candidate_demo_lessons
        SET demo_at = created_at
        WHERE demo_at IS NULL;
        UPDATE msi_v2.teacher_candidate_subject_tests
        SET test_at = created_at
        WHERE test_at IS NULL;

        CREATE TEMP TABLE _hr_recruitment_legacy_active_repair
        ON COMMIT DROP AS
            SELECT candidate.id
            FROM msi_v2.teacher_candidates candidate
            WHERE candidate.status = 'active_teacher'
              AND NOT EXISTS (
                  SELECT 1
                  FROM msi_v2.teachers teacher
                  WHERE teacher.recruitment_candidate_id = candidate.id
                    AND teacher.status = 'active'
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM msi_v2.academy_teachers academy
                  WHERE academy.recruitment_candidate_id = candidate.id
                    AND academy.promoted_teacher_id IS NULL
                    AND COALESCE(academy.academy_status, '') NOT IN (
                        'rejected', 'removed', 'trash_bin'
                    )
              );

        UPDATE msi_v2.teacher_candidate_stage_history history
        SET exited_at = now()
        FROM _hr_recruitment_legacy_active_repair unsupported
        WHERE history.candidate_id = unsupported.id
          AND history.exited_at IS NULL;

        UPDATE msi_v2.teacher_candidates candidate
        SET status = 'under_review',
            stage_changed_at = now(),
            version = version + 1,
            updated_at = now()
        FROM _hr_recruitment_legacy_active_repair unsupported
        WHERE candidate.id = unsupported.id;

        INSERT INTO msi_v2.teacher_candidate_stage_history (
            candidate_id, stage, entered_at, comment, transition_source,
            sla_target_days, sla_due_at
        )
        SELECT candidate.id, 'under_review', candidate.stage_changed_at,
               'Unsupported legacy active-teacher state reconciled to Final Decision.',
               'migration', rule.target_days,
               candidate.stage_changed_at + make_interval(days => rule.target_days)
        FROM msi_v2.teacher_candidates candidate
        JOIN _hr_recruitment_legacy_active_repair repaired
          ON repaired.id = candidate.id
        LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
          ON rule.stage = 'under_review' AND rule.is_active
        WHERE NOT EXISTS (
              SELECT 1
              FROM msi_v2.teacher_candidate_stage_history history
              WHERE history.candidate_id = candidate.id
                AND history.stage = 'under_review'
                AND history.entered_at = candidate.stage_changed_at
          );

        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT 'candidate.legacy_active_teacher_reconciled',
               'teacher_candidate', candidate.id,
               jsonb_build_object(
                   'from', 'active_teacher',
                   'to', 'under_review',
                   'reason', 'No canonical active or Academy teacher record'
               ),
               candidate.stage_changed_at
        FROM msi_v2.teacher_candidates candidate
        JOIN _hr_recruitment_legacy_active_repair repaired
          ON repaired.id = candidate.id
        WHERE NOT EXISTS (
              SELECT 1
              FROM msi_v2.audit_events audit
              WHERE audit.entity_type = 'teacher_candidate'
                AND audit.entity_id = candidate.id
                AND audit.event_type = 'candidate.legacy_active_teacher_reconciled'
          );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidate_appointments
            DROP CONSTRAINT IF EXISTS teacher_candidate_appointments_time_check;
        UPDATE msi_v2.teacher_candidate_appointments
        SET ends_at = starts_at + interval '1 minute'
        WHERE ends_at IS NULL;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ALTER COLUMN ends_at SET NOT NULL;
        ALTER TABLE msi_v2.teacher_candidate_appointments
            ADD CONSTRAINT teacher_candidate_appointments_time_check CHECK (
                ends_at > starts_at
            );

        ALTER TABLE msi_v2.teachers
            DROP COLUMN IF EXISTS activated_at;
        """
    )
