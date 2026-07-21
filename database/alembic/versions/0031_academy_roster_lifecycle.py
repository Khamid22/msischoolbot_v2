"""synchronize Teacher Academy lifecycle visibility

Revision ID: 0031_academy_roster_lifecycle
Revises: 0030_academy_subject_handoff
Create Date: 2026-07-21
"""

from alembic import op


revision = "0031_academy_roster_lifecycle"
down_revision = "0030_academy_subject_handoff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH synchronized AS (
            UPDATE msi_v2.academy_teachers academy
            SET academy_status = CASE
                    WHEN candidate.status = 'trash_bin' THEN 'trash_bin'
                    ELSE 'rejected'
                END,
                updated_at = now()
            FROM msi_v2.teacher_candidates candidate
            WHERE academy.recruitment_candidate_id = candidate.id
              AND academy.promoted_teacher_id IS NULL
              AND candidate.status IN (
                  'rejected', 'candidate_withdrew', 'trash_bin'
              )
              AND COALESCE(academy.academy_status, '')
                  NOT IN ('rejected', 'removed', 'trash_bin')
            RETURNING candidate.id AS candidate_id,
                      academy.id AS academy_teacher_id,
                      academy.academy_status
        )
        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT 'candidate.academy_lifecycle_synchronized',
               'teacher_candidate', synchronized.candidate_id,
               jsonb_build_object(
                   'academy_teacher_id', synchronized.academy_teacher_id,
                   'academy_status', synchronized.academy_status,
                   'reason', 'Closed candidates cannot remain in the Academy roster'
               ),
               now()
        FROM synchronized;
        """
    )


def downgrade() -> None:
    # Closed Academy records must not be made visible during a code rollback.
    pass
