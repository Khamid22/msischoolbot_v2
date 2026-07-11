"""optimize gradebook access without removing academic data

Revision ID: 0011_gradebook_performance
Revises: 0010_lesson_exceptions
Create Date: 2026-07-12
"""

from alembic import op


revision = "0011_gradebook_performance"
down_revision = "0010_lesson_exceptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO msi_v2.lesson_sessions (
            group_id, program_item_id, status, source_key, source_kind,
            source_label, source_topic, source_order, source_file, source_sheet,
            created_at, updated_at
        )
        SELECT
            g.id, spi.id, 'scheduled', concat('curriculum:', g.id, ':', spi.id),
            'lesson', spi.lesson_number, spi.title, spi.item_order,
            spi.source_file, spi.sheet_name, now(), now()
        FROM msi_v2.groups g
        JOIN msi_v2.subject_program_items spi ON spi.program_id = g.program_id
        WHERE spi.item_type = 'lesson'
          AND NOT EXISTS (
              SELECT 1
              FROM msi_v2.lesson_sessions existing
              WHERE existing.group_id = g.id AND existing.program_item_id = spi.id
          )
        ON CONFLICT (source_key) WHERE source_key <> '' DO NOTHING;

        CREATE INDEX IF NOT EXISTS idx_attendance_gradebook_lookup
        ON msi_v2.attendance_records (group_id, student_id, lesson_session_id);

        CREATE INDEX IF NOT EXISTS idx_homework_gradebook_lookup
        ON msi_v2.homework_scores (group_id, student_id, lesson_session_id);

        CREATE INDEX IF NOT EXISTS idx_exam_gradebook_lookup
        ON msi_v2.exam_results (group_id, student_id, program_item_id);

        CREATE INDEX IF NOT EXISTS idx_coin_events_student_group
        ON msi_v2.coin_events (group_id, student_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_coin_events_student_group;
        DROP INDEX IF EXISTS msi_v2.idx_exam_gradebook_lookup;
        DROP INDEX IF EXISTS msi_v2.idx_homework_gradebook_lookup;
        DROP INDEX IF EXISTS msi_v2.idx_attendance_gradebook_lookup;
        """
    )
