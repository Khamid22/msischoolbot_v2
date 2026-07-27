"""add durable PostgreSQL outbox jobs

Revision ID: 0043_outbox_jobs
Revises: 0042_teacher_employment_events
Create Date: 2026-07-26
"""

from alembic import op


revision = "0043_outbox_jobs"
down_revision = "0042_teacher_employment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.outbox_jobs (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            topic text NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            idempotency_key text NOT NULL,
            status text NOT NULL DEFAULT 'pending',
            attempts integer NOT NULL DEFAULT 0,
            max_attempts integer NOT NULL DEFAULT 5,
            available_at timestamptz NOT NULL DEFAULT now(),
            lease_owner text,
            lease_expires_at timestamptz,
            started_at timestamptz,
            completed_at timestamptz,
            last_error text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT outbox_jobs_topic_not_blank CHECK (btrim(topic) <> ''),
            CONSTRAINT outbox_jobs_idempotency_key_not_blank
                CHECK (btrim(idempotency_key) <> ''),
            CONSTRAINT outbox_jobs_status_check
                CHECK (status IN ('pending', 'running', 'retry', 'completed', 'dead')),
            CONSTRAINT outbox_jobs_attempts_check
                CHECK (attempts >= 0 AND max_attempts > 0)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_jobs_idempotency
            ON msi_v2.outbox_jobs (idempotency_key);

        CREATE INDEX IF NOT EXISTS idx_outbox_jobs_claim
            ON msi_v2.outbox_jobs (available_at, id)
            WHERE status IN ('pending', 'retry');

        CREATE INDEX IF NOT EXISTS idx_outbox_jobs_expired_lease
            ON msi_v2.outbox_jobs (lease_expires_at, id)
            WHERE status = 'running';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS msi_v2.outbox_jobs")
