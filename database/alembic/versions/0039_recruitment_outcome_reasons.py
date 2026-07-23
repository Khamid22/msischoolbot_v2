"""unify recruitment outcome reason catalogs

Revision ID: 0040_outcome_reasons
Revises: 0039_test_demo_color
Create Date: 2026-07-23
"""

from alembic import op


revision = "0040_outcome_reasons"
down_revision = "0039_test_demo_color"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP CONSTRAINT IF EXISTS teacher_recruitment_settings_category_check;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD CONSTRAINT teacher_recruitment_settings_category_check CHECK (
                category IN (
                    'source', 'subsource', 'rejection_reason',
                    'withdrawal_reason', 'position', 'english_level',
                    'schedule', 'availability', 'expected_salary',
                    'teaching_experience'
                )
            );

        -- Evaluation outcomes now use the same HR-managed rejection catalog as
        -- manual rejection, so the old automatic entries are ordinary options.
        UPDATE msi_v2.teacher_recruitment_settings
        SET is_system = false,
            updated_at = now()
        WHERE category = 'rejection_reason'
          AND is_system = true;

        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            ADD COLUMN IF NOT EXISTS withdrawal_reason TEXT NOT NULL DEFAULT '';

        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, is_active, sort_order, is_system,
            created_at, updated_at
        ) VALUES
            ('withdrawal_reason', 'candidate_no_longer_interested', 'Candidate no longer interested', true, 10, false, now(), now()),
            ('withdrawal_reason', 'accepted_another_offer', 'Accepted another offer', true, 20, false, now(), now()),
            ('withdrawal_reason', 'personal_circumstances', 'Personal circumstances', true, 30, false, now(), now()),
            ('withdrawal_reason', 'schedule_incompatibility', 'Schedule incompatibility', true, 40, false, now(), now()),
            ('withdrawal_reason', 'salary_expectation_incompatibility', 'Salary expectation incompatibility', true, 50, false, now(), now()),
            ('withdrawal_reason', 'relocation_or_location', 'Relocation or location', true, 60, false, now(), now()),
            ('withdrawal_reason', 'unresponsive', 'Candidate stopped responding', true, 70, false, now(), now()),
            ('withdrawal_reason', 'other', 'Other', true, 80, false, now(), now())
        ON CONFLICT DO NOTHING;

        -- Preserve every current free-text withdrawal reason as an active
        -- option so existing operational language remains available.
        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, is_active, sort_order, is_system,
            created_at, updated_at
        )
        SELECT
            'withdrawal_reason',
            'historical_' || substr(md5(lower(btrim(decision.reason_detail))), 1, 24),
            left(btrim(decision.reason_detail), 120),
            true,
            100 + row_number() OVER (
                ORDER BY lower(left(btrim(decision.reason_detail), 120))
            ) * 10,
            false,
            now(),
            now()
        FROM (
            SELECT DISTINCT reason_detail
            FROM msi_v2.teacher_candidate_final_decisions
            WHERE decision = 'candidate_withdrew'
              AND length(btrim(reason_detail)) > 0
        ) decision
        ON CONFLICT DO NOTHING;

        UPDATE msi_v2.teacher_candidate_final_decisions decision
        SET withdrawal_reason = setting.value
        FROM msi_v2.teacher_recruitment_settings setting
        WHERE decision.decision = 'candidate_withdrew'
          AND decision.withdrawal_reason = ''
          AND length(btrim(decision.reason_detail)) > 0
          AND setting.category = 'withdrawal_reason'
          AND lower(setting.label) = lower(left(btrim(decision.reason_detail), 120));

        UPDATE msi_v2.teacher_candidate_final_decisions
        SET withdrawal_reason = 'other'
        WHERE decision = 'candidate_withdrew'
          AND withdrawal_reason = '';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidate_final_decisions
            DROP COLUMN IF EXISTS withdrawal_reason;

        DELETE FROM msi_v2.teacher_recruitment_settings
        WHERE category = 'withdrawal_reason';

        UPDATE msi_v2.teacher_recruitment_settings
        SET is_system = true,
            updated_at = now()
        WHERE category = 'rejection_reason'
          AND value IN (
              'failed_job_interview',
              'failed_subject_test',
              'failed_demo_lesson'
          );

        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP CONSTRAINT IF EXISTS teacher_recruitment_settings_category_check;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD CONSTRAINT teacher_recruitment_settings_category_check CHECK (
                category IN (
                    'source', 'subsource', 'rejection_reason', 'position',
                    'english_level', 'schedule', 'availability',
                    'expected_salary', 'teaching_experience'
                )
            );
        """
    )
