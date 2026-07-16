"""standardize recruitment option dimensions

Revision ID: 0024_recruitment_options
Revises: 0023_remove_on_hold
Create Date: 2026-07-16
"""

from alembic import op


revision = "0024_recruitment_options"
down_revision = "0023_remove_on_hold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD COLUMN IF NOT EXISTS parent_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS is_legacy BOOLEAN NOT NULL DEFAULT false;

        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP CONSTRAINT IF EXISTS teacher_recruitment_settings_category_check;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP CONSTRAINT IF EXISTS teacher_recruitment_settings_category_value_unique;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD CONSTRAINT teacher_recruitment_settings_category_check CHECK (
                category IN (
                    'source', 'subsource', 'rejection_reason', 'english_level',
                    'schedule', 'availability', 'expected_salary',
                    'teaching_experience'
                )
            );

        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_settings_label_ci;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_root_label_ci
        ON msi_v2.teacher_recruitment_settings (
            category, lower(btrim(label))
        ) WHERE parent_id IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_child_label_ci
        ON msi_v2.teacher_recruitment_settings (
            category, parent_id, lower(btrim(label))
        ) WHERE parent_id IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_root_value
        ON msi_v2.teacher_recruitment_settings (category, value)
        WHERE parent_id IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_child_value
        ON msi_v2.teacher_recruitment_settings (category, parent_id, value)
        WHERE parent_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_parent_order
        ON msi_v2.teacher_recruitment_settings (
            parent_id, is_active, sort_order, lower(btrim(label)), id
        );

        CREATE OR REPLACE FUNCTION msi_v2.validate_recruitment_setting()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            parent_category TEXT;
        BEGIN
            IF TG_OP = 'UPDATE' AND (
                NEW.category IS DISTINCT FROM OLD.category OR
                NEW.value IS DISTINCT FROM OLD.value OR
                NEW.label IS DISTINCT FROM OLD.label OR
                NEW.parent_id IS DISTINCT FROM OLD.parent_id OR
                NEW.is_legacy IS DISTINCT FROM OLD.is_legacy
            ) THEN
                RAISE EXCEPTION 'Recruitment option identity is immutable; create a replacement option instead.';
            END IF;

            IF NEW.category = 'subsource' THEN
                IF NEW.parent_id IS NULL THEN
                    RAISE EXCEPTION 'A subsource requires a source parent.';
                END IF;
                SELECT setting.category INTO parent_category
                FROM msi_v2.teacher_recruitment_settings setting
                WHERE setting.id = NEW.parent_id;
                IF parent_category IS DISTINCT FROM 'source' THEN
                    RAISE EXCEPTION 'A subsource parent must be a source.';
                END IF;
            ELSIF NEW.parent_id IS NOT NULL THEN
                RAISE EXCEPTION 'Only subsource options may have a parent.';
            END IF;
            RETURN NEW;
        END;
        $$;

        DROP TRIGGER IF EXISTS trg_validate_recruitment_setting
            ON msi_v2.teacher_recruitment_settings;
        CREATE TRIGGER trg_validate_recruitment_setting
        BEFORE INSERT OR UPDATE ON msi_v2.teacher_recruitment_settings
        FOR EACH ROW EXECUTE FUNCTION msi_v2.validate_recruitment_setting();

        ALTER TABLE msi_v2.teacher_candidates
            ADD COLUMN IF NOT EXISTS source_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS subsource_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS english_level_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS schedule_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS availability_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS expected_salary_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS teaching_experience_option_id BIGINT
                REFERENCES msi_v2.teacher_recruitment_settings(id) ON DELETE RESTRICT;

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

        DROP TRIGGER IF EXISTS trg_validate_candidate_recruitment_options
            ON msi_v2.teacher_candidates;
        CREATE TRIGGER trg_validate_candidate_recruitment_options
        BEFORE INSERT OR UPDATE OF
            source_option_id, subsource_option_id, english_level_option_id,
            schedule_option_id, availability_option_id,
            expected_salary_option_id, teaching_experience_option_id
        ON msi_v2.teacher_candidates
        FOR EACH ROW EXECUTE FUNCTION msi_v2.validate_candidate_recruitment_options();

        UPDATE msi_v2.teacher_candidates candidate
        SET source_option_id = setting.id
        FROM msi_v2.teacher_recruitment_settings setting
        WHERE candidate.source_option_id IS NULL
          AND setting.category = 'source'
          AND lower(btrim(setting.label)) = lower(btrim(candidate.source))
          AND btrim(candidate.source) <> '';

        WITH legacy_values AS (
            SELECT DISTINCT lower(btrim(candidate.source)) AS normalized,
                   min(btrim(candidate.source)) AS label
            FROM msi_v2.teacher_candidates candidate
            WHERE btrim(candidate.source) <> '' AND candidate.source_option_id IS NULL
            GROUP BY lower(btrim(candidate.source))
        )
        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, is_active, is_legacy, sort_order
        )
        SELECT 'source', 'legacy_' || md5(legacy.normalized), legacy.label,
               false, true, 100000
        FROM legacy_values legacy
        ON CONFLICT DO NOTHING;

        UPDATE msi_v2.teacher_candidates candidate
        SET source_option_id = setting.id
        FROM msi_v2.teacher_recruitment_settings setting
        WHERE candidate.source_option_id IS NULL
          AND setting.category = 'source'
          AND setting.value = 'legacy_' || md5(lower(btrim(candidate.source)))
          AND btrim(candidate.source) <> '';

        CREATE OR REPLACE FUNCTION msi_v2.backfill_candidate_text_option(
            source_column TEXT,
            option_category TEXT,
            target_column TEXT
        ) RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
            EXECUTE format(
                $query$UPDATE msi_v2.teacher_candidates candidate
                 SET %1$I = setting.id
                 FROM msi_v2.teacher_recruitment_settings setting
                 WHERE candidate.%1$I IS NULL
                   AND setting.category = $1
                   AND lower(btrim(setting.label)) = lower(btrim(candidate.%2$I::text))
                   AND btrim(candidate.%2$I::text) <> ''$query$,
                target_column, source_column
            ) USING option_category;

            EXECUTE format(
                $query$WITH legacy_values AS (
                    SELECT DISTINCT lower(btrim(candidate.%1$I::text)) AS normalized,
                           min(btrim(candidate.%1$I::text)) AS label
                    FROM msi_v2.teacher_candidates candidate
                    WHERE candidate.%2$I IS NULL
                      AND btrim(candidate.%1$I::text) <> ''
                    GROUP BY lower(btrim(candidate.%1$I::text))
                 )
                 INSERT INTO msi_v2.teacher_recruitment_settings
                    (category, value, label, is_active, is_legacy, sort_order)
                 SELECT $1, 'legacy_' || md5(legacy.normalized), legacy.label,
                        false, true, 100000
                 FROM legacy_values legacy
                 ON CONFLICT DO NOTHING$query$,
                source_column, target_column
            ) USING option_category;

            EXECUTE format(
                $query$UPDATE msi_v2.teacher_candidates candidate
                 SET %1$I = setting.id
                 FROM msi_v2.teacher_recruitment_settings setting
                 WHERE candidate.%1$I IS NULL
                   AND setting.category = $1
                   AND setting.value = 'legacy_' || md5(lower(btrim(candidate.%2$I::text)))
                   AND btrim(candidate.%2$I::text) <> ''$query$,
                target_column, source_column
            ) USING option_category;
        END;
        $$;

        SELECT msi_v2.backfill_candidate_text_option(
            'english_level', 'english_level', 'english_level_option_id'
        );
        SELECT msi_v2.backfill_candidate_text_option(
            'preferred_schedule', 'schedule', 'schedule_option_id'
        );
        SELECT msi_v2.backfill_candidate_text_option(
            'employment_availability', 'availability', 'availability_option_id'
        );
        SELECT msi_v2.backfill_candidate_text_option(
            'expected_salary_uzs', 'expected_salary', 'expected_salary_option_id'
        );
        SELECT msi_v2.backfill_candidate_text_option(
            'teaching_experience', 'teaching_experience',
            'teaching_experience_option_id'
        );
        DROP FUNCTION msi_v2.backfill_candidate_text_option(TEXT, TEXT, TEXT);

        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_source_option
            ON msi_v2.teacher_candidates (source_option_id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_subsource_option
            ON msi_v2.teacher_candidates (subsource_option_id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_english_option
            ON msi_v2.teacher_candidates (english_level_option_id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_schedule_option
            ON msi_v2.teacher_candidates (schedule_option_id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_availability_option
            ON msi_v2.teacher_candidates (availability_option_id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_salary_option
            ON msi_v2.teacher_candidates (expected_salary_option_id);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_teaching_experience_option
            ON msi_v2.teacher_candidates (teaching_experience_option_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_validate_candidate_recruitment_options
            ON msi_v2.teacher_candidates;
        DROP FUNCTION IF EXISTS msi_v2.validate_candidate_recruitment_options();

        ALTER TABLE msi_v2.teacher_candidates
            DROP COLUMN IF EXISTS teaching_experience_option_id,
            DROP COLUMN IF EXISTS expected_salary_option_id,
            DROP COLUMN IF EXISTS availability_option_id,
            DROP COLUMN IF EXISTS schedule_option_id,
            DROP COLUMN IF EXISTS english_level_option_id,
            DROP COLUMN IF EXISTS subsource_option_id,
            DROP COLUMN IF EXISTS source_option_id;

        DROP TRIGGER IF EXISTS trg_validate_recruitment_setting
            ON msi_v2.teacher_recruitment_settings;
        DROP FUNCTION IF EXISTS msi_v2.validate_recruitment_setting();
        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_settings_child_label_ci;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_settings_root_label_ci;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_settings_child_value;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_settings_root_value;
        DROP INDEX IF EXISTS msi_v2.idx_teacher_recruitment_settings_parent_order;
        DELETE FROM msi_v2.teacher_recruitment_settings
        WHERE category NOT IN ('source', 'rejection_reason');
        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP COLUMN IF EXISTS is_legacy,
            DROP COLUMN IF EXISTS parent_id;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            DROP CONSTRAINT IF EXISTS teacher_recruitment_settings_category_check;
        ALTER TABLE msi_v2.teacher_recruitment_settings
            ADD CONSTRAINT teacher_recruitment_settings_category_check CHECK (
                category IN ('source', 'rejection_reason')
            ),
            ADD CONSTRAINT teacher_recruitment_settings_category_value_unique
                UNIQUE (category, value);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_label_ci
        ON msi_v2.teacher_recruitment_settings (category, lower(label));
        """
    )
