"""replace MAX+1 student legacy identifiers with a PostgreSQL sequence

Revision ID: 0044_student_identifier_sequence
Revises: 0043_outbox_jobs
Create Date: 2026-07-26
"""

from alembic import op


revision = "0044_student_identifier_sequence"
down_revision = "0043_outbox_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS msi_v2.legacy_student_row_id_seq
            AS bigint
            START WITH 9000000000
            INCREMENT BY 1
            NO CYCLE;

        SELECT setval(
            'msi_v2.legacy_student_row_id_seq',
            GREATEST(
                COALESCE(MAX(legacy_student_row_id), 0) + 1,
                9000000000
            ),
            false
        )
        FROM msi_v2.students;
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP SEQUENCE IF EXISTS msi_v2.legacy_student_row_id_seq"
    )
