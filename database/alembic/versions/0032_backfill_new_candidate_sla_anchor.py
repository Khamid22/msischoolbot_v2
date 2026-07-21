"""backfill new_candidate SLA anchor to application_date

Revision ID: 0032_backfill_sla_anchor
Revises: 0031_academy_roster_lifecycle
Create Date: 2026-07-21

Candidates created before the application-date SLA fix had their initial
"Application Received" stage_history row anchored to the moment HR entered
the record instead of the candidate's actual application_date, so a
historical application date understated (or hid) an already-elapsed or
overdue SLA. This corrects only the original creation entry (matched by its
exact 'Candidate created.' comment) for candidates still open in that stage,
leaving every later transition (restores, board moves, evaluations) intact.
"""

from alembic import op


revision = "0032_backfill_sla_anchor"
down_revision = "0031_academy_roster_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH corrected AS (
            UPDATE msi_v2.teacher_candidate_stage_history AS history
            SET entered_at = anchor.new_entered_at,
                sla_due_at = CASE
                    WHEN history.sla_target_days IS NULL THEN history.sla_due_at
                    ELSE anchor.new_entered_at
                         + make_interval(days => history.sla_target_days)
                END
            FROM (
                SELECT h.id AS history_id,
                       c.id AS candidate_id,
                       h.entered_at AS old_entered_at,
                       (c.application_date::timestamp AT TIME ZONE 'Asia/Tashkent')
                           AS new_entered_at
                FROM msi_v2.teacher_candidate_stage_history h
                JOIN msi_v2.teacher_candidates c ON c.id = h.candidate_id
                WHERE h.stage = 'new_candidate'
                  AND h.exited_at IS NULL
                  AND h.transition_source = 'manual'
                  AND h.comment = 'Candidate created.'
                  AND c.status = 'new_candidate'
                  AND c.application_date IS NOT NULL
            ) AS anchor
            WHERE history.id = anchor.history_id
              AND history.entered_at <> anchor.new_entered_at
            RETURNING anchor.candidate_id, anchor.old_entered_at, anchor.new_entered_at
        )
        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT 'candidate.sla_anchor_backfilled',
               'teacher_candidate', corrected.candidate_id,
               jsonb_build_object(
                   'old_entered_at', corrected.old_entered_at,
                   'new_entered_at', corrected.new_entered_at,
                   'reason', 'SLA clock now starts from application_date'
               ),
               now()
        FROM corrected;
        """
    )


def downgrade() -> None:
    # The prior entered_at (the row-creation timestamp) is not recoverable
    # from data alone, and re-inflating an already-correct SLA anchor to a
    # known-wrong value on rollback would reintroduce the bug intentionally.
    pass
