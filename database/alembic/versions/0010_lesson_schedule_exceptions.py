"""add auditable lesson schedule exceptions

Revision ID: 0010_lesson_exceptions
Revises: 0009_academic_classes
Create Date: 2026-07-12
"""

from alembic import op


revision = "0010_lesson_exceptions"
down_revision = "0009_academic_classes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE msi_v2.lesson_schedule_exceptions (
            id BIGSERIAL PRIMARY KEY,
            group_id BIGINT NOT NULL REFERENCES msi_v2.groups(id) ON DELETE CASCADE,
            lesson_session_id BIGINT NOT NULL REFERENCES msi_v2.lesson_sessions(id) ON DELETE RESTRICT,
            schedule_rule_id BIGINT REFERENCES msi_v2.group_schedule_rules(id) ON DELETE SET NULL,
            original_session_date DATE NOT NULL,
            original_start_time TIME,
            original_end_time TIME,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'cancelled',
            cancelled_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            recovered_by_staff_id BIGINT REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            cancelled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            recovered_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT lesson_schedule_exceptions_reason_check CHECK (length(btrim(reason)) > 0),
            CONSTRAINT lesson_schedule_exceptions_status_check CHECK (status IN ('cancelled', 'recovered'))
        );

        CREATE UNIQUE INDEX lesson_schedule_exceptions_one_active_per_lesson
        ON msi_v2.lesson_schedule_exceptions (lesson_session_id)
        WHERE status = 'cancelled';

        CREATE INDEX lesson_schedule_exceptions_group_date
        ON msi_v2.lesson_schedule_exceptions (group_id, original_session_date)
        WHERE status = 'cancelled';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS msi_v2.lesson_schedule_exceptions")
