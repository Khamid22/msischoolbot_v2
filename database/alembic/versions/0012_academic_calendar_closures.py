"""add auditable school and group calendar closures

Revision ID: 0012_calendar_closures
Revises: 0011_gradebook_performance
Create Date: 2026-07-14
"""

from alembic import op


revision = "0012_calendar_closures"
down_revision = "0011_gradebook_performance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE msi_v2.academic_calendar_closures (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL REFERENCES msi_v2.schools(id) ON DELETE CASCADE,
            group_id BIGINT REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'Summer holiday',
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            unlocked_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            unlocked_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT academic_calendar_closures_title_check
                CHECK (length(btrim(title)) > 0),
            CONSTRAINT academic_calendar_closures_dates_check
                CHECK (end_date >= start_date),
            CONSTRAINT academic_calendar_closures_status_check
                CHECK (status IN ('active', 'unlocked'))
        );

        CREATE INDEX academic_calendar_closures_school_range
        ON msi_v2.academic_calendar_closures (school_id, start_date, end_date)
        WHERE status = 'active';

        CREATE INDEX academic_calendar_closures_group_range
        ON msi_v2.academic_calendar_closures (group_id, start_date, end_date)
        WHERE status = 'active' AND group_id IS NOT NULL;

        CREATE UNIQUE INDEX academic_calendar_closures_school_exact_active
        ON msi_v2.academic_calendar_closures (school_id, start_date, end_date)
        WHERE status = 'active' AND group_id IS NULL;

        CREATE UNIQUE INDEX academic_calendar_closures_group_exact_active
        ON msi_v2.academic_calendar_closures (group_id, start_date, end_date)
        WHERE status = 'active' AND group_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS msi_v2.academic_calendar_closures")
