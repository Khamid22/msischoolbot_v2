"""synchronize canonical subjects into Teacher Academy

Revision ID: 0030_academy_subject_handoff
Revises: 0029_hr_recruitment_core
Create Date: 2026-07-21
"""

from alembic import op


revision = "0030_academy_subject_handoff"
down_revision = "0029_hr_recruitment_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH synchronized AS (
            UPDATE msi_v2.academy_teachers academy
            SET subject_id = COALESCE(academy.subject_id, candidate.subject_id),
                subject_program_id = COALESCE(
                    academy.subject_program_id,
                    (
                        SELECT program.id
                        FROM msi_v2.subject_programs program
                        WHERE program.subject_id = COALESCE(
                            academy.subject_id,
                            candidate.subject_id
                        )
                          AND program.status = 'active'
                        ORDER BY program.updated_at DESC, program.id DESC
                        LIMIT 1
                    )
                ),
                updated_at = now()
            FROM msi_v2.teacher_candidates candidate
            WHERE academy.recruitment_candidate_id = candidate.id
              AND candidate.subject_id IS NOT NULL
              AND (
                  academy.subject_id IS NULL
                  OR (
                      academy.subject_id = candidate.subject_id
                      AND academy.subject_program_id IS NULL
                  )
              )
            RETURNING candidate.id AS candidate_id, academy.subject_id,
                      academy.subject_program_id
        )
        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT 'candidate.academy_subject_synchronized',
               'teacher_candidate', synchronized.candidate_id,
               jsonb_build_object(
                   'subject_id', synchronized.subject_id,
                   'subject_program_id', synchronized.subject_program_id,
                   'source', 'candidate_profile',
                   'reason', 'Backfilled missing Teacher Academy subject and curriculum'
               ),
               now()
        FROM synchronized;
        """
    )


def downgrade() -> None:
    # The synchronized subject is canonical application data and should not be
    # erased during a code rollback.
    pass
