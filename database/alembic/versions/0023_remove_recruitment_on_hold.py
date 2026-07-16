"""remove On Hold from the active recruitment workflow

Revision ID: 0023_remove_on_hold
Revises: 0022_hr_recruitment_ops
Create Date: 2026-07-16
"""

from alembic import op


revision = "0023_remove_on_hold"
down_revision = "0022_hr_recruitment_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TEMP TABLE recruitment_on_hold_restore ON COMMIT DROP AS
        SELECT
            candidate.id AS candidate_id,
            CASE
                WHEN hold.origin_stage IN (
                    'new_candidate', 'responded', 'job_interview',
                    'test_and_demo', 'under_review'
                ) THEN hold.origin_stage
                ELSE 'responded'
            END AS restore_stage,
            COALESCE(NULLIF(hold.reason, ''), 'On Hold stage removed.') AS hold_reason,
            candidate.updated_by_account_id AS responsible_account_id
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN LATERAL (
            SELECT history.origin_stage, history.reason
            FROM msi_v2.teacher_candidate_holds history
            WHERE history.candidate_id = candidate.id
              AND history.released_at IS NULL
            ORDER BY history.placed_at DESC, history.id DESC
            LIMIT 1
        ) hold ON true
        WHERE candidate.status = 'on_hold';

        UPDATE msi_v2.teacher_candidate_stage_history history
        SET exited_at = GREATEST(now(), history.entered_at)
        FROM recruitment_on_hold_restore restoring
        WHERE history.candidate_id = restoring.candidate_id
          AND history.exited_at IS NULL;

        UPDATE msi_v2.teacher_candidates candidate
        SET status = restoring.restore_stage,
            stage_changed_at = now(),
            updated_at = now(),
            version = candidate.version + 1
        FROM recruitment_on_hold_restore restoring
        WHERE candidate.id = restoring.candidate_id;

        UPDATE msi_v2.teacher_candidate_holds history
        SET released_at = now()
        WHERE history.released_at IS NULL;

        UPDATE msi_v2.teacher_candidate_final_decisions decision
        SET voided_at = now(),
            void_reason = 'On Hold was removed from the recruitment workflow.'
        WHERE decision.decision = 'on_hold'
          AND decision.voided_at IS NULL;

        INSERT INTO msi_v2.teacher_candidate_stage_history (
            candidate_id, stage, entered_at, responsible_account_id,
            comment, transition_source, sla_target_days, sla_due_at
        )
        SELECT
            restoring.candidate_id,
            restoring.restore_stage,
            now(),
            restoring.responsible_account_id,
            'Restored automatically because the On Hold stage was removed.',
            'migration',
            rule.target_days,
            CASE
                WHEN rule.target_days IS NULL THEN NULL
                ELSE now() + make_interval(days => rule.target_days)
            END
        FROM recruitment_on_hold_restore restoring
        LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
          ON rule.stage = restoring.restore_stage AND rule.is_active = true;

        INSERT INTO msi_v2.audit_events (
            actor_account_id, event_type, entity_type, entity_id,
            detail_json, created_at
        )
        SELECT
            NULL,
            'candidate.stage_restored_after_on_hold_removal',
            'teacher_candidate',
            restoring.candidate_id,
            jsonb_build_object(
                'from', 'on_hold',
                'to', restoring.restore_stage,
                'previous_hold_reason', restoring.hold_reason,
                'transition_source', 'migration'
            ),
            now()
        FROM recruitment_on_hold_restore restoring;

        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            );
        """
    )


def downgrade() -> None:
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
        """
    )
