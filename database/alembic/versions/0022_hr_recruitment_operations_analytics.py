"""add recruitment stage history, SLA, structured assessments, and next actions

Revision ID: 0022_hr_recruitment_ops
Revises: 0021_candidate_education
Create Date: 2026-07-16
"""

from alembic import op


revision = "0022_hr_recruitment_ops"
down_revision = "0021_candidate_education"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_sla_rules (
            stage TEXT PRIMARY KEY,
            target_days SMALLINT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_recruitment_sla_rules_stage_check CHECK (
                stage IN (
                    'new_candidate', 'responded', 'job_interview',
                    'test_and_demo', 'under_review'
                )
            ),
            CONSTRAINT teacher_recruitment_sla_rules_days_check CHECK (
                target_days BETWEEN 1 AND 90
            )
        );

        INSERT INTO msi_v2.teacher_recruitment_sla_rules (stage, target_days)
        VALUES
            ('new_candidate', 1),
            ('responded', 3),
            ('job_interview', 5),
            ('test_and_demo', 7),
            ('under_review', 2)
        ON CONFLICT (stage) DO NOTHING;

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_stage_history (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL
                REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            stage TEXT NOT NULL,
            entered_at TIMESTAMPTZ NOT NULL,
            exited_at TIMESTAMPTZ,
            responsible_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            comment TEXT NOT NULL DEFAULT '',
            transition_source TEXT NOT NULL DEFAULT 'manual',
            sla_target_days SMALLINT,
            sla_due_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_stage_history_stage_check CHECK (
                stage IN (
                    'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                    'under_review', 'on_hold', 'teacher_academy', 'active_teacher',
                    'rejected', 'candidate_withdrew', 'trash_bin'
                )
            ),
            CONSTRAINT teacher_candidate_stage_history_source_check CHECK (
                transition_source IN ('manual', 'automatic', 'migration', 'restored')
            ),
            CONSTRAINT teacher_candidate_stage_history_time_check CHECK (
                exited_at IS NULL OR exited_at >= entered_at
            ),
            CONSTRAINT teacher_candidate_stage_history_sla_check CHECK (
                sla_target_days IS NULL OR sla_target_days BETWEEN 1 AND 90
            )
        );

        WITH stage_events AS (
            SELECT
                event.entity_id::bigint AS candidate_id,
                CASE
                    WHEN event.event_type = 'candidate.created'
                        THEN NULLIF(event.detail_json ->> 'stage', '')
                    WHEN event.event_type = 'candidate.final_decision_made'
                        THEN NULLIF(event.detail_json ->> 'decision', '')
                    ELSE NULLIF(event.detail_json ->> 'to', '')
                END AS stage,
                event.created_at AS entered_at,
                event.actor_account_id,
                COALESCE(
                    NULLIF(event.detail_json ->> 'reason', ''),
                    NULLIF(event.detail_json ->> 'comment', ''),
                    ''
                ) AS comment,
                event.id
            FROM msi_v2.audit_events event
            WHERE event.entity_type = 'teacher_candidate'
              AND event.event_type IN (
                  'candidate.created', 'candidate.stage_changed',
                  'candidate.moved_to_trash', 'candidate.placed_on_hold',
                  'candidate.final_decision_made'
              )
        ), ordered_events AS (
            SELECT
                event.*,
                candidate.status AS current_stage,
                candidate.stage_changed_at AS current_stage_changed_at,
                lead(event.entered_at) OVER (
                    PARTITION BY event.candidate_id
                    ORDER BY event.entered_at, event.id
                ) AS next_entered_at,
                row_number() OVER (
                    PARTITION BY event.candidate_id
                    ORDER BY event.entered_at, event.id
                ) AS event_index,
                count(*) OVER (PARTITION BY event.candidate_id) AS event_count
            FROM stage_events event
            JOIN msi_v2.teacher_candidates candidate ON candidate.id = event.candidate_id
            WHERE event.stage IN (
                'new_candidate', 'responded', 'job_interview', 'test_and_demo',
                'under_review', 'on_hold', 'teacher_academy', 'active_teacher',
                'rejected', 'candidate_withdrew', 'trash_bin'
            )
        )
        INSERT INTO msi_v2.teacher_candidate_stage_history (
            candidate_id, stage, entered_at, exited_at,
            responsible_account_id, comment, transition_source,
            sla_target_days, sla_due_at
        )
        SELECT
            event.candidate_id,
            event.stage,
            event.entered_at,
            CASE
                WHEN event.next_entered_at IS NOT NULL THEN event.next_entered_at
                ELSE GREATEST(
                    event.entered_at,
                    COALESCE(event.current_stage_changed_at, event.entered_at)
                )
            END,
            event.actor_account_id,
            event.comment,
            'migration',
            rule.target_days,
            CASE
                WHEN rule.target_days IS NULL THEN NULL
                ELSE event.entered_at + make_interval(days => rule.target_days)
            END
        FROM ordered_events event
        LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
          ON rule.stage = event.stage AND rule.is_active = true
        WHERE event.event_index < event.event_count
           OR event.stage <> event.current_stage;

        INSERT INTO msi_v2.teacher_candidate_stage_history (
            candidate_id, stage, entered_at, responsible_account_id,
            comment, transition_source, sla_target_days, sla_due_at
        )
        SELECT
            candidate.id,
            candidate.status,
            COALESCE(candidate.stage_changed_at, candidate.updated_at, candidate.created_at),
            candidate.updated_by_account_id,
            'Current stage reconstructed during migration.',
            'migration',
            rule.target_days,
            CASE
                WHEN rule.target_days IS NULL THEN NULL
                ELSE COALESCE(candidate.stage_changed_at, candidate.updated_at, candidate.created_at)
                     + make_interval(days => rule.target_days)
            END
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN msi_v2.teacher_recruitment_sla_rules rule
          ON rule.stage = candidate.status AND rule.is_active = true
        WHERE NOT EXISTS (
            SELECT 1
            FROM msi_v2.teacher_candidate_stage_history history
            WHERE history.candidate_id = candidate.id AND history.exited_at IS NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_stage_history_open
        ON msi_v2.teacher_candidate_stage_history (candidate_id)
        WHERE exited_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_stage_history_candidate_time
        ON msi_v2.teacher_candidate_stage_history (candidate_id, entered_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_stage_history_stage_time
        ON msi_v2.teacher_candidate_stage_history (stage, entered_at DESC);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_stage_history_sla_open
        ON msi_v2.teacher_candidate_stage_history (sla_due_at, stage)
        WHERE exited_at IS NULL AND sla_due_at IS NOT NULL;

        ALTER TABLE msi_v2.teacher_candidate_tasks
            ADD COLUMN IF NOT EXISTS task_key TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS task_origin TEXT NOT NULL DEFAULT 'manual',
            ADD COLUMN IF NOT EXISTS stage_history_id BIGINT
                REFERENCES msi_v2.teacher_candidate_stage_history(id) ON DELETE SET NULL;
        ALTER TABLE msi_v2.teacher_candidate_tasks
            DROP CONSTRAINT IF EXISTS teacher_candidate_tasks_origin_check;
        ALTER TABLE msi_v2.teacher_candidate_tasks
            ADD CONSTRAINT teacher_candidate_tasks_origin_check CHECK (
                task_origin IN ('manual', 'system')
            );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_tasks_system_active
        ON msi_v2.teacher_candidate_tasks (candidate_id, task_key, stage_history_id)
        WHERE task_origin = 'system' AND status = 'pending';

        ALTER TABLE msi_v2.teacher_candidates
            ADD COLUMN IF NOT EXISTS source_detail TEXT NOT NULL DEFAULT '';

        ALTER TABLE msi_v2.teacher_candidate_interviews
            ADD COLUMN IF NOT EXISTS cefr_level TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS overall_score NUMERIC(4, 2),
            ADD COLUMN IF NOT EXISTS communication_score NUMERIC(4, 2),
            ADD COLUMN IF NOT EXISTS recommendation_code TEXT NOT NULL DEFAULT '';
        ALTER TABLE msi_v2.teacher_candidate_interviews
            DROP CONSTRAINT IF EXISTS teacher_candidate_interviews_overall_score_check,
            DROP CONSTRAINT IF EXISTS teacher_candidate_interviews_communication_score_check;
        ALTER TABLE msi_v2.teacher_candidate_interviews
            ADD CONSTRAINT teacher_candidate_interviews_overall_score_check CHECK (
                overall_score IS NULL OR overall_score BETWEEN 0 AND 10
            ),
            ADD CONSTRAINT teacher_candidate_interviews_communication_score_check CHECK (
                communication_score IS NULL OR communication_score BETWEEN 0 AND 10
            );

        ALTER TABLE msi_v2.teacher_candidate_subject_tests
            ADD COLUMN IF NOT EXISTS paper TEXT NOT NULL DEFAULT '';

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_subject_test_topics (
            id BIGSERIAL PRIMARY KEY,
            subject_test_id BIGINT NOT NULL
                REFERENCES msi_v2.teacher_candidate_subject_tests(id) ON DELETE CASCADE,
            topic TEXT NOT NULL,
            score NUMERIC(10, 2) NOT NULL,
            maximum_score NUMERIC(10, 2) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_subject_test_topics_name_check CHECK (
                length(btrim(topic)) > 0
            ),
            CONSTRAINT teacher_candidate_subject_test_topics_score_check CHECK (
                score >= 0 AND maximum_score > 0 AND score <= maximum_score
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_subject_test_topics_attempt
        ON msi_v2.teacher_candidate_subject_test_topics (subject_test_id, id);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_demo_criteria (
            id BIGSERIAL PRIMARY KEY,
            demo_lesson_id BIGINT NOT NULL
                REFERENCES msi_v2.teacher_candidate_demo_lessons(id) ON DELETE CASCADE,
            criterion TEXT NOT NULL,
            score NUMERIC(4, 2) NOT NULL,
            maximum_score NUMERIC(4, 2) NOT NULL DEFAULT 10,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_demo_criteria_name_check CHECK (
                length(btrim(criterion)) > 0
            ),
            CONSTRAINT teacher_candidate_demo_criteria_score_check CHECK (
                score >= 0 AND maximum_score > 0 AND score <= maximum_score
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_demo_criteria_attempt
        ON msi_v2.teacher_candidate_demo_criteria (demo_lesson_id, id);

        ALTER TABLE msi_v2.teacher_candidate_documents
            DROP CONSTRAINT IF EXISTS teacher_candidate_documents_type_check;
        ALTER TABLE msi_v2.teacher_candidate_documents
            ADD CONSTRAINT teacher_candidate_documents_type_check CHECK (
                document_type IN (
                    'cv', 'a_level', 'igcse', 'id_passport', 'ielts', 'sat',
                    'diploma', 'certificate', 'recommendation', 'other'
                )
            );

        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_subject_application
        ON msi_v2.teacher_candidates (subject_id, application_date DESC NULLS LAST);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_subject_application;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_demo_criteria;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_subject_test_topics;

        ALTER TABLE msi_v2.teacher_candidate_subject_tests
            DROP COLUMN IF EXISTS paper;
        ALTER TABLE msi_v2.teacher_candidate_interviews
            DROP CONSTRAINT IF EXISTS teacher_candidate_interviews_communication_score_check,
            DROP CONSTRAINT IF EXISTS teacher_candidate_interviews_overall_score_check,
            DROP COLUMN IF EXISTS recommendation_code,
            DROP COLUMN IF EXISTS communication_score,
            DROP COLUMN IF EXISTS overall_score,
            DROP COLUMN IF EXISTS cefr_level;
        ALTER TABLE msi_v2.teacher_candidates
            DROP COLUMN IF EXISTS source_detail;

        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidate_tasks_system_active;
        ALTER TABLE msi_v2.teacher_candidate_tasks
            DROP CONSTRAINT IF EXISTS teacher_candidate_tasks_origin_check,
            DROP COLUMN IF EXISTS stage_history_id,
            DROP COLUMN IF EXISTS task_origin,
            DROP COLUMN IF EXISTS task_key;

        DROP TABLE IF EXISTS msi_v2.teacher_candidate_stage_history;
        DROP TABLE IF EXISTS msi_v2.teacher_recruitment_sla_rules;
        """
    )
