"""broaden new_candidate SLA anchor backfill to every current stage entry

Revision ID: 0033_broaden_sla_anchor_backfill
Revises: 0032_backfill_sla_anchor
Create Date: 2026-07-21

0032_backfill_sla_anchor only corrected the original candidate-creation
stage_history row, matched narrowly by its exact 'Candidate created.'
comment and transition_source='manual'. Candidates whose current
new_candidate entry came from any other path (a manual move back into the
stage, a restore, or a differently-worded historical entry) were left
anchored to that transition's timestamp instead of application_date, so
they kept showing a fresh/green SLA despite an old application date.

update_candidate_stage now unconditionally anchors any current
new_candidate stage entry to application_date regardless of how it was
(re)entered, so this backfill drops the narrow comment/transition_source
filter and corrects every candidate currently open in that stage to
match. Already-correct rows (including those 0032 already fixed) are
left untouched.
"""

from alembic import op


revision = "0033_broaden_sla_anchor_backfill"
down_revision = "0032_backfill_sla_anchor"
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
                   'reason', 'Broadened backfill: SLA clock starts from application_date regardless of how the current stage entry was created'
               ),
               now()
        FROM corrected;
        """
    )


def downgrade() -> None:
    # The prior entered_at values are not recoverable from data alone, and
    # reintroducing a known-wrong anchor on rollback would reintroduce the bug.
    pass
