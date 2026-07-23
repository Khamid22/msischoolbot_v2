"""track recruited teacher activation and deactivation events

Revision ID: 0042_teacher_employment_events
Revises: 0041_consolidate_reasons
Create Date: 2026-07-23
"""

from alembic import op


revision = "0042_teacher_employment_events"
down_revision = "0041_consolidate_reasons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_employment_events (
            id BIGSERIAL PRIMARY KEY,
            teacher_id BIGINT NOT NULL
                REFERENCES msi_v2.teachers(id) ON DELETE CASCADE,
            recruitment_candidate_id BIGINT
                REFERENCES msi_v2.teacher_candidates(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            occurred_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_employment_events_type_check CHECK (
                event_type IN ('activated', 'deactivated')
            ),
            CONSTRAINT teacher_employment_events_source_check CHECK (
                length(btrim(source)) > 0
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_employment_events_unique
        ON msi_v2.teacher_employment_events (
            teacher_id, event_type, occurred_at
        );

        CREATE INDEX IF NOT EXISTS idx_teacher_employment_events_occurred
        ON msi_v2.teacher_employment_events (occurred_at, event_type);

        CREATE INDEX IF NOT EXISTS idx_teacher_employment_events_candidate
        ON msi_v2.teacher_employment_events (
            recruitment_candidate_id, occurred_at
        )
        WHERE recruitment_candidate_id IS NOT NULL;

        -- Every recruited teacher must have entered active employment at least
        -- once. Legacy rows without an explicit activation date fall back to
        -- their creation time.
        INSERT INTO msi_v2.teacher_employment_events (
            teacher_id, recruitment_candidate_id, event_type,
            occurred_at, source, created_at
        )
        SELECT
            teacher.id,
            teacher.recruitment_candidate_id,
            'activated',
            COALESCE(teacher.activated_at, teacher.created_at),
            'historical_backfill',
            now()
        FROM msi_v2.teachers teacher
        WHERE teacher.recruitment_candidate_id IS NOT NULL
        ON CONFLICT DO NOTHING;

        -- Inactive recruited teachers do not currently have a dedicated
        -- departure timestamp. Their latest update is the best historical
        -- approximation and is never allowed to precede activation.
        INSERT INTO msi_v2.teacher_employment_events (
            teacher_id, recruitment_candidate_id, event_type,
            occurred_at, source, created_at
        )
        SELECT
            teacher.id,
            teacher.recruitment_candidate_id,
            'deactivated',
            GREATEST(
                teacher.updated_at,
                COALESCE(teacher.activated_at, teacher.created_at)
            ),
            'historical_backfill',
            now()
        FROM msi_v2.teachers teacher
        WHERE teacher.recruitment_candidate_id IS NOT NULL
          AND teacher.status <> 'active'
        ON CONFLICT DO NOTHING;

        CREATE OR REPLACE FUNCTION msi_v2.capture_teacher_employment_event()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            event_at TIMESTAMPTZ;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.recruitment_candidate_id IS NOT NULL
                   AND NEW.status = 'active' THEN
                    event_at := COALESCE(
                        NEW.activated_at, NEW.created_at, NEW.updated_at, now()
                    );
                    INSERT INTO msi_v2.teacher_employment_events (
                        teacher_id, recruitment_candidate_id, event_type,
                        occurred_at, source, created_at
                    ) VALUES (
                        NEW.id, NEW.recruitment_candidate_id, 'activated',
                        event_at, 'status_transition', now()
                    )
                    ON CONFLICT DO NOTHING;
                END IF;
                RETURN NEW;
            END IF;

            IF NEW.recruitment_candidate_id IS NOT NULL
               AND NEW.status = 'active'
               AND (
                   OLD.status IS DISTINCT FROM 'active'
                   OR OLD.recruitment_candidate_id IS NULL
               ) THEN
                event_at := CASE
                    WHEN NEW.activated_at IS DISTINCT FROM OLD.activated_at
                        THEN COALESCE(NEW.activated_at, NEW.updated_at, now())
                    WHEN NEW.updated_at IS DISTINCT FROM OLD.updated_at
                        THEN COALESCE(NEW.updated_at, now())
                    ELSE now()
                END;
                INSERT INTO msi_v2.teacher_employment_events (
                    teacher_id, recruitment_candidate_id, event_type,
                    occurred_at, source, created_at
                ) VALUES (
                    NEW.id, NEW.recruitment_candidate_id, 'activated',
                    event_at, 'status_transition', now()
                )
                ON CONFLICT DO NOTHING;
            END IF;

            IF OLD.status = 'active'
               AND NEW.status IS DISTINCT FROM 'active'
               AND COALESCE(
                   NEW.recruitment_candidate_id,
                   OLD.recruitment_candidate_id
               ) IS NOT NULL THEN
                event_at := CASE
                    WHEN NEW.updated_at IS DISTINCT FROM OLD.updated_at
                        THEN COALESCE(NEW.updated_at, now())
                    ELSE now()
                END;
                INSERT INTO msi_v2.teacher_employment_events (
                    teacher_id, recruitment_candidate_id, event_type,
                    occurred_at, source, created_at
                ) VALUES (
                    NEW.id,
                    COALESCE(
                        NEW.recruitment_candidate_id,
                        OLD.recruitment_candidate_id
                    ),
                    'deactivated',
                    event_at,
                    'status_transition',
                    now()
                )
                ON CONFLICT DO NOTHING;
            END IF;

            RETURN NEW;
        END
        $$;

        DROP TRIGGER IF EXISTS trg_capture_teacher_employment_event
            ON msi_v2.teachers;
        CREATE TRIGGER trg_capture_teacher_employment_event
        AFTER INSERT OR UPDATE OF status, recruitment_candidate_id
        ON msi_v2.teachers
        FOR EACH ROW EXECUTE FUNCTION msi_v2.capture_teacher_employment_event();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_capture_teacher_employment_event
            ON msi_v2.teachers;
        DROP FUNCTION IF EXISTS msi_v2.capture_teacher_employment_event();
        DROP TABLE IF EXISTS msi_v2.teacher_employment_events;
        """
    )
