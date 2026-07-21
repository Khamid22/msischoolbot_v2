"""add configurable recruitment pipeline stages

Revision ID: 0035_pipeline_stages
Revises: 0034_customer_support
Create Date: 2026-07-21
"""

from alembic import op


revision = "0035_pipeline_stages"
down_revision = "0034_customer_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_pipeline_stages (
            id BIGSERIAL PRIMARY KEY,
            stage_key TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            stage_kind TEXT NOT NULL,
            color_token TEXT NOT NULL DEFAULT 'neutral',
            sort_order INTEGER NOT NULL,
            is_pipeline BOOLEAN NOT NULL DEFAULT true,
            is_active BOOLEAN NOT NULL DEFAULT true,
            replacement_stage_key TEXT,
            sla_target_days SMALLINT,
            version BIGINT NOT NULL DEFAULT 1,
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            archived_at TIMESTAMPTZ,
            archived_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            CONSTRAINT teacher_recruitment_pipeline_stages_kind_check CHECK (
                stage_kind IN ('system', 'custom', 'terminal')
            ),
            CONSTRAINT teacher_recruitment_pipeline_stages_color_check CHECK (
                color_token IN ('neutral', 'blue', 'cyan', 'violet', 'green', 'amber', 'orange', 'rose')
            ),
            CONSTRAINT teacher_recruitment_pipeline_stages_sla_check CHECK (
                sla_target_days IS NULL OR sla_target_days BETWEEN 1 AND 90
            ),
            CONSTRAINT teacher_recruitment_pipeline_stages_version_check CHECK (version > 0),
            CONSTRAINT teacher_recruitment_pipeline_stages_archive_check CHECK (
                (is_active = true AND archived_at IS NULL)
                OR (is_active = false AND archived_at IS NOT NULL)
            ),
            CONSTRAINT teacher_recruitment_pipeline_stages_replacement_fk
                FOREIGN KEY (replacement_stage_key)
                REFERENCES msi_v2.teacher_recruitment_pipeline_stages(stage_key)
                ON DELETE RESTRICT
        );

        INSERT INTO msi_v2.teacher_recruitment_pipeline_stages (
            stage_key, label, stage_kind, color_token, sort_order,
            is_pipeline, is_active, sla_target_days
        ) VALUES
            ('new_candidate', 'Application Received', 'system', 'neutral', 10, true, true, 1),
            ('responded', 'Interview Schedule', 'system', 'blue', 20, true, true, 3),
            ('job_interview', 'Job Interview', 'system', 'green', 30, true, true, 5),
            ('test_and_demo', 'Test & Demo', 'system', 'amber', 40, true, true, 7),
            ('under_review', 'Final Decision', 'system', 'violet', 50, true, true, 2),
            ('teacher_academy', 'Teacher Academy', 'terminal', 'amber', 60, false, true, NULL),
            ('active_teacher', 'Active Teacher', 'terminal', 'blue', 70, false, true, NULL),
            ('rejected', 'Rejected', 'terminal', 'rose', 80, false, true, NULL),
            ('candidate_withdrew', 'Candidate Withdrew', 'terminal', 'neutral', 90, false, true, NULL),
            ('trash_bin', 'Trash Bin', 'terminal', 'neutral', 100, false, true, NULL)
        ON CONFLICT (stage_key) DO NOTHING;

        -- The retired on-hold stage can still exist in immutable history and
        -- decision-origin records. Keep it resolvable without exposing it as
        -- an active movement target or changing any historical row.
        INSERT INTO msi_v2.teacher_recruitment_pipeline_stages (
            stage_key, label, stage_kind, color_token, sort_order,
            is_pipeline, is_active, replacement_stage_key, archived_at
        ) VALUES (
            'on_hold', 'On Hold (legacy)', 'terminal', 'neutral', 110,
            false, false, 'responded', now()
        )
        ON CONFLICT (stage_key) DO NOTHING;

        UPDATE msi_v2.teacher_recruitment_pipeline_stages stage
        SET sla_target_days = rule.target_days,
            updated_at = GREATEST(stage.updated_at, rule.updated_at)
        FROM msi_v2.teacher_recruitment_sla_rules rule
        WHERE rule.stage = stage.stage_key;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_recruitment_pipeline_stage_label
        ON msi_v2.teacher_recruitment_pipeline_stages (lower(btrim(label)));

        CREATE INDEX IF NOT EXISTS idx_recruitment_pipeline_stage_order
        ON msi_v2.teacher_recruitment_pipeline_stages (is_pipeline, is_active, sort_order, id);

        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check,
            DROP CONSTRAINT IF EXISTS teacher_candidates_status_stage_fk;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_status_stage_fk
            FOREIGN KEY (status)
            REFERENCES msi_v2.teacher_recruitment_pipeline_stages(stage_key)
            ON UPDATE CASCADE ON DELETE RESTRICT;

        ALTER TABLE msi_v2.teacher_candidate_stage_history
            DROP CONSTRAINT IF EXISTS teacher_candidate_stage_history_stage_check,
            DROP CONSTRAINT IF EXISTS teacher_candidate_stage_history_stage_fk;
        ALTER TABLE msi_v2.teacher_candidate_stage_history
            ADD CONSTRAINT teacher_candidate_stage_history_stage_fk
            FOREIGN KEY (stage)
            REFERENCES msi_v2.teacher_recruitment_pipeline_stages(stage_key)
            ON UPDATE CASCADE ON DELETE RESTRICT;

        ALTER TABLE msi_v2.teacher_recruitment_sla_rules
            DROP CONSTRAINT IF EXISTS teacher_recruitment_sla_rules_stage_check,
            DROP CONSTRAINT IF EXISTS teacher_recruitment_sla_rules_stage_fk;
        ALTER TABLE msi_v2.teacher_recruitment_sla_rules
            ADD CONSTRAINT teacher_recruitment_sla_rules_stage_fk
            FOREIGN KEY (stage)
            REFERENCES msi_v2.teacher_recruitment_pipeline_stages(stage_key)
            ON UPDATE CASCADE ON DELETE RESTRICT;

        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            DROP CONSTRAINT IF EXISTS teacher_candidate_final_decisions_origin_stage_check;
        ALTER TABLE msi_v2.teacher_candidate_holds
            DROP CONSTRAINT IF EXISTS teacher_candidate_holds_origin_stage_check;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE msi_v2.teacher_candidate_final_decisions decision
        SET origin_stage = COALESCE(stage.replacement_stage_key, 'new_candidate')
        FROM msi_v2.teacher_recruitment_pipeline_stages stage
        WHERE decision.origin_stage = stage.stage_key AND stage.stage_kind = 'custom';

        UPDATE msi_v2.teacher_candidate_stage_history history
        SET stage = COALESCE(stage.replacement_stage_key, 'new_candidate')
        FROM msi_v2.teacher_recruitment_pipeline_stages stage
        WHERE history.stage = stage.stage_key AND stage.stage_kind = 'custom';

        UPDATE msi_v2.teacher_candidates candidate
        SET status = COALESCE(stage.replacement_stage_key, 'new_candidate')
        FROM msi_v2.teacher_recruitment_pipeline_stages stage
        WHERE candidate.status = stage.stage_key AND stage.stage_kind = 'custom';

        DELETE FROM msi_v2.teacher_recruitment_sla_rules rule
        USING msi_v2.teacher_recruitment_pipeline_stages stage
        WHERE rule.stage = stage.stage_key AND stage.stage_kind = 'custom';

        ALTER TABLE msi_v2.teacher_recruitment_sla_rules
            DROP CONSTRAINT IF EXISTS teacher_recruitment_sla_rules_stage_fk;
        ALTER TABLE msi_v2.teacher_candidate_stage_history
            DROP CONSTRAINT IF EXISTS teacher_candidate_stage_history_stage_fk;
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_status_stage_fk;

        DROP TABLE IF EXISTS msi_v2.teacher_recruitment_pipeline_stages;

        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            );
        ALTER TABLE msi_v2.teacher_candidate_stage_history
            ADD CONSTRAINT teacher_candidate_stage_history_stage_check CHECK (
                stage IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            );
        ALTER TABLE msi_v2.teacher_recruitment_sla_rules
            ADD CONSTRAINT teacher_recruitment_sla_rules_stage_check CHECK (
                stage IN ('new_candidate', 'responded', 'job_interview', 'test_and_demo', 'under_review')
            );
        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            ADD CONSTRAINT teacher_candidate_final_decisions_origin_stage_check CHECK (
                origin_stage = '' OR origin_stage IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher'
                )
            );
        """
    )
