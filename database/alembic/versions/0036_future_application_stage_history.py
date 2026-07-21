"""repair future-dated recruitment stage-history anchors

Revision ID: 0036_future_stage_anchor
Revises: 0035_pipeline_stages
Create Date: 2026-07-22

Application dates remain the business anchor for SLA deadlines.  A future
application date, however, must not make the open history interval begin
after a transition that happens now.  Those rows violate the history time
constraint when HR moves, rejects, or withdraws the candidate.

This migration caps only the operational history timestamp at migration
time.  It deliberately preserves sla_due_at, which continues to use the
candidate's application date.
"""

from alembic import op


revision = "0036_future_stage_anchor"
down_revision = "0035_pipeline_stages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH corrected AS (
            UPDATE msi_v2.teacher_candidate_stage_history AS history
            SET entered_at = now()
            WHERE history.exited_at IS NULL
              AND history.entered_at > now()
            RETURNING history.candidate_id,
                      history.stage,
                      history.entered_at AS corrected_entered_at
        )
        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT 'candidate.stage_history_future_anchor_repaired',
               'teacher_candidate', corrected.candidate_id,
               jsonb_build_object(
                   'stage', corrected.stage,
                   'corrected_entered_at', corrected.corrected_entered_at,
                   'reason', 'Open stage history cannot begin after its eventual transition time'
               ),
               now()
        FROM corrected;
        """
    )


def downgrade() -> None:
    # The previous future timestamp is intentionally not restored: doing so
    # would recreate a row that cannot be closed safely before that date.
    pass
