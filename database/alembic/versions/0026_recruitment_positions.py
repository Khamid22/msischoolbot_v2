"""standardize recruitment teacher positions

Revision ID: 0026_recruitment_positions
Revises: 0025_interview_sessions
Create Date: 2026-07-16
"""

from alembic import op


revision = "0026_recruitment_positions"
down_revision = "0025_interview_sessions"
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
                    'source', 'subsource', 'rejection_reason', 'position',
                    'english_level', 'schedule', 'availability',
                    'expected_salary', 'teaching_experience'
                )
            );

        ALTER TABLE msi_v2.teacher_candidates
            ADD COLUMN IF NOT EXISTS position_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT;

        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, is_active, is_legacy, sort_order
        ) VALUES
            ('position', 'igcse_math_teacher', 'IGCSE Math Teacher', true, false, 10),
            ('position', 'igcse_chemistry_teacher', 'IGCSE Chemistry Teacher', true, false, 20),
            ('position', 'igcse_physics_teacher', 'IGCSE Physics Teacher', true, false, 30),
            ('position', 'igcse_biology_teacher', 'IGCSE Biology Teacher', true, false, 40),
            ('position', 'igcse_esl_teacher', 'IGCSE ESL Teacher', true, false, 50)
        ON CONFLICT DO NOTHING;

        CREATE OR REPLACE FUNCTION msi_v2.validate_candidate_recruitment_options()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            option_category TEXT;
            option_parent BIGINT;
        BEGIN
            IF NEW.source_option_id IS NOT NULL THEN
                SELECT category INTO option_category
                FROM msi_v2.teacher_recruitment_settings WHERE id = NEW.source_option_id;
                IF option_category IS DISTINCT FROM 'source' THEN
                    RAISE EXCEPTION 'source_option_id must reference a source option.';
                END IF;
            END IF;
            IF NEW.subsource_option_id IS NOT NULL THEN
                SELECT category, parent_id INTO option_category, option_parent
                FROM msi_v2.teacher_recruitment_settings WHERE id = NEW.subsource_option_id;
                IF option_category IS DISTINCT FROM 'subsource'
                   OR option_parent IS DISTINCT FROM NEW.source_option_id THEN
                    RAISE EXCEPTION 'Subsource must belong to the selected source.';
                END IF;
            END IF;
            IF NEW.position_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.position_option_id AND category = 'position'
            ) THEN RAISE EXCEPTION 'Invalid position option.'; END IF;
            IF NEW.english_level_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.english_level_option_id AND category = 'english_level'
            ) THEN RAISE EXCEPTION 'Invalid English level option.'; END IF;
            IF NEW.schedule_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.schedule_option_id AND category = 'schedule'
            ) THEN RAISE EXCEPTION 'Invalid schedule option.'; END IF;
            IF NEW.availability_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.availability_option_id AND category = 'availability'
            ) THEN RAISE EXCEPTION 'Invalid availability option.'; END IF;
            IF NEW.expected_salary_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.expected_salary_option_id AND category = 'expected_salary'
            ) THEN RAISE EXCEPTION 'Invalid expected salary option.'; END IF;
            IF NEW.teaching_experience_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.teaching_experience_option_id AND category = 'teaching_experience'
            ) THEN RAISE EXCEPTION 'Invalid teaching experience option.'; END IF;
            RETURN NEW;
        END;
        $$;

        DROP TRIGGER IF EXISTS trg_validate_candidate_recruitment_options
            ON msi_v2.teacher_candidates;
        CREATE TRIGGER trg_validate_candidate_recruitment_options
        BEFORE INSERT OR UPDATE OF
            source_option_id, subsource_option_id, position_option_id,
            english_level_option_id, schedule_option_id, availability_option_id,
            expected_salary_option_id, teaching_experience_option_id
        ON msi_v2.teacher_candidates
        FOR EACH ROW EXECUTE FUNCTION msi_v2.validate_candidate_recruitment_options();

        WITH classified AS (
            SELECT candidate.id,
                   candidate.applied_position AS previous_position,
                   CASE
                       WHEN lower(concat_ws(' ', candidate.applied_position, subject.subject_name))
                            ~ '(^|[^a-z])biology([^a-z]|$)'
                           THEN 'igcse_biology_teacher'
                       WHEN lower(concat_ws(' ', candidate.applied_position, subject.subject_name))
                            ~ '(^|[^a-z])chem(istry)?([^a-z]|$)'
                           THEN 'igcse_chemistry_teacher'
                       WHEN lower(concat_ws(' ', candidate.applied_position, subject.subject_name))
                            ~ '(^|[^a-z])physics([^a-z]|$)'
                           THEN 'igcse_physics_teacher'
                       WHEN lower(concat_ws(' ', candidate.applied_position, subject.subject_name))
                            ~ '(^|[^a-z])(english|esl)([^a-z]|$)'
                           THEN 'igcse_esl_teacher'
                       WHEN lower(concat_ws(' ', candidate.applied_position, subject.subject_name))
                            ~ '(^|[^a-z])(math|mathematics)([^a-z]|$)'
                           THEN 'igcse_math_teacher'
                       ELSE NULL
                   END AS canonical_value
            FROM msi_v2.teacher_candidates candidate
            LEFT JOIN msi_v2.subjects subject ON subject.id = candidate.subject_id
        ), changed AS (
            UPDATE msi_v2.teacher_candidates candidate
            SET position_option_id = setting.id,
                applied_position = setting.label,
                updated_at = now(),
                version = candidate.version + 1
            FROM classified,
                 msi_v2.teacher_recruitment_settings setting
            WHERE candidate.id = classified.id
              AND classified.canonical_value IS NOT NULL
              AND setting.category = 'position'
              AND setting.value = classified.canonical_value
              AND (
                  candidate.position_option_id IS DISTINCT FROM setting.id
                  OR candidate.applied_position IS DISTINCT FROM setting.label
              )
            RETURNING candidate.id, candidate.applied_position AS label
        )
        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT 'candidate.position_standardized', 'teacher_candidate', changed.id,
               jsonb_build_object('position', changed.label, 'source', 'migration_0026'),
               now()
        FROM changed;

        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_position_option
            ON msi_v2.teacher_candidates (position_option_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_validate_candidate_recruitment_options
            ON msi_v2.teacher_candidates;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_candidates_position_option;
        ALTER TABLE msi_v2.teacher_candidates
            DROP COLUMN IF EXISTS position_option_id;
        DELETE FROM msi_v2.teacher_recruitment_settings
        WHERE category = 'position';

        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP CONSTRAINT IF EXISTS teacher_recruitment_settings_category_check;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD CONSTRAINT teacher_recruitment_settings_category_check CHECK (
                category IN (
                    'source', 'subsource', 'rejection_reason', 'english_level',
                    'schedule', 'availability', 'expected_salary',
                    'teaching_experience'
                )
            );

        CREATE OR REPLACE FUNCTION msi_v2.validate_candidate_recruitment_options()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            option_category TEXT;
            option_parent BIGINT;
        BEGIN
            IF NEW.source_option_id IS NOT NULL THEN
                SELECT category INTO option_category
                FROM msi_v2.teacher_recruitment_settings WHERE id = NEW.source_option_id;
                IF option_category IS DISTINCT FROM 'source' THEN
                    RAISE EXCEPTION 'source_option_id must reference a source option.';
                END IF;
            END IF;
            IF NEW.subsource_option_id IS NOT NULL THEN
                SELECT category, parent_id INTO option_category, option_parent
                FROM msi_v2.teacher_recruitment_settings WHERE id = NEW.subsource_option_id;
                IF option_category IS DISTINCT FROM 'subsource'
                   OR option_parent IS DISTINCT FROM NEW.source_option_id THEN
                    RAISE EXCEPTION 'Subsource must belong to the selected source.';
                END IF;
            END IF;
            IF NEW.english_level_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.english_level_option_id AND category = 'english_level'
            ) THEN RAISE EXCEPTION 'Invalid English level option.'; END IF;
            IF NEW.schedule_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.schedule_option_id AND category = 'schedule'
            ) THEN RAISE EXCEPTION 'Invalid schedule option.'; END IF;
            IF NEW.availability_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.availability_option_id AND category = 'availability'
            ) THEN RAISE EXCEPTION 'Invalid availability option.'; END IF;
            IF NEW.expected_salary_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.expected_salary_option_id AND category = 'expected_salary'
            ) THEN RAISE EXCEPTION 'Invalid expected salary option.'; END IF;
            IF NEW.teaching_experience_option_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM msi_v2.teacher_recruitment_settings
                WHERE id = NEW.teaching_experience_option_id AND category = 'teaching_experience'
            ) THEN RAISE EXCEPTION 'Invalid teaching experience option.'; END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_validate_candidate_recruitment_options
        BEFORE INSERT OR UPDATE OF
            source_option_id, subsource_option_id, english_level_option_id,
            schedule_option_id, availability_option_id,
            expected_salary_option_id, teaching_experience_option_id
        ON msi_v2.teacher_candidates
        FOR EACH ROW EXECUTE FUNCTION msi_v2.validate_candidate_recruitment_options();
        """
    )
