"""customer support ticket SLA and dashboard indexes

Revision ID: 0045_customer_support_ticket_sla
Revises: 0044_student_identifier_sequence
Create Date: 2026-07-27
"""

from alembic import op

revision = "0045_customer_support_ticket_sla"
down_revision = "0044_student_identifier_sequence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.support_ticket_sla_policies (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT REFERENCES msi_v2.schools(id) ON DELETE CASCADE,
            priority TEXT NOT NULL,
            first_response_minutes INTEGER NOT NULL,
            resolution_minutes INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            updated_by_staff_id BIGINT
                REFERENCES msi_v2.msi_staff(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT support_ticket_sla_priority_check
                CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            CONSTRAINT support_ticket_sla_response_minutes_check
                CHECK (first_response_minutes > 0),
            CONSTRAINT support_ticket_sla_resolution_minutes_check
                CHECK (
                    resolution_minutes > 0
                    AND resolution_minutes >= first_response_minutes
                )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_support_ticket_sla_policy_scope_priority
        ON msi_v2.support_ticket_sla_policies (
            COALESCE(school_id, 0),
            priority
        );

        INSERT INTO msi_v2.support_ticket_sla_policies (
            school_id,
            priority,
            first_response_minutes,
            resolution_minutes
        )
        VALUES
            (NULL, 'urgent', 30, 240),
            (NULL, 'high', 120, 720),
            (NULL, 'normal', 240, 1440),
            (NULL, 'low', 480, 2880)
        ON CONFLICT (
            (COALESCE(school_id, 0)),
            priority
        ) DO NOTHING;

        ALTER TABLE msi_v2.support_tickets
            ADD COLUMN IF NOT EXISTS priority TEXT NOT NULL DEFAULT 'normal',
            ADD COLUMN IF NOT EXISTS first_response_target_minutes INTEGER
                NOT NULL DEFAULT 240,
            ADD COLUMN IF NOT EXISTS resolution_target_minutes INTEGER
                NOT NULL DEFAULT 1440,
            ADD COLUMN IF NOT EXISTS first_response_due_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS resolution_due_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS first_responded_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS waiting_on_requester_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS requester_wait_seconds BIGINT NOT NULL DEFAULT 0;

        ALTER TABLE msi_v2.support_tickets
            DROP CONSTRAINT IF EXISTS support_tickets_priority_check;
        ALTER TABLE msi_v2.support_tickets
            ADD CONSTRAINT support_tickets_priority_check
                CHECK (priority IN ('low', 'normal', 'high', 'urgent'));

        ALTER TABLE msi_v2.support_tickets
            DROP CONSTRAINT IF EXISTS support_tickets_response_target_check;
        ALTER TABLE msi_v2.support_tickets
            ADD CONSTRAINT support_tickets_response_target_check
                CHECK (first_response_target_minutes > 0);

        ALTER TABLE msi_v2.support_tickets
            DROP CONSTRAINT IF EXISTS support_tickets_resolution_target_check;
        ALTER TABLE msi_v2.support_tickets
            ADD CONSTRAINT support_tickets_resolution_target_check
                CHECK (
                    resolution_target_minutes > 0
                    AND resolution_target_minutes >= first_response_target_minutes
                );

        ALTER TABLE msi_v2.support_tickets
            DROP CONSTRAINT IF EXISTS support_tickets_requester_wait_check;
        ALTER TABLE msi_v2.support_tickets
            ADD CONSTRAINT support_tickets_requester_wait_check
                CHECK (requester_wait_seconds >= 0);

        UPDATE msi_v2.support_tickets ticket
        SET
            priority = COALESCE(NULLIF(ticket.priority, ''), 'normal'),
            first_response_target_minutes = 240,
            resolution_target_minutes = 1440,
            first_response_due_at = COALESCE(
                ticket.first_response_due_at,
                ticket.created_at + INTERVAL '240 minutes'
            ),
            resolution_due_at = COALESCE(
                ticket.resolution_due_at,
                ticket.created_at + INTERVAL '1440 minutes'
            ),
            first_responded_at = COALESCE(
                ticket.first_responded_at,
                (
                    SELECT MIN(message.created_at)
                    FROM msi_v2.ticket_messages message
                    WHERE message.ticket_id = ticket.id
                      AND message.author_staff_id IS NOT NULL
                )
            )
        WHERE
            ticket.first_response_due_at IS NULL
            OR ticket.resolution_due_at IS NULL
            OR ticket.first_responded_at IS NULL;

        CREATE INDEX IF NOT EXISTS idx_support_tickets_student_status_created
        ON msi_v2.support_tickets (student_id, status, created_at, id);

        CREATE INDEX IF NOT EXISTS idx_support_tickets_assignment_status_updated
        ON msi_v2.support_tickets (
            assigned_to_staff_id,
            status,
            updated_at DESC,
            id DESC
        );

        CREATE INDEX IF NOT EXISTS idx_support_tickets_open_response_deadline
        ON msi_v2.support_tickets (first_response_due_at, priority, created_at, id)
        WHERE status <> 'resolved' AND first_responded_at IS NULL;

        CREATE INDEX IF NOT EXISTS idx_support_tickets_open_resolution_deadline
        ON msi_v2.support_tickets (resolution_due_at, priority, created_at, id)
        WHERE status <> 'resolved';

        CREATE INDEX IF NOT EXISTS idx_support_tickets_waiting_requester
        ON msi_v2.support_tickets (waiting_on_requester_at, created_at, id)
        WHERE status <> 'resolved' AND waiting_on_requester_at IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_payments_school_exception_due
        ON msi_v2.payments (due_date, student_id, currency, id)
        WHERE voided_at IS NULL AND status NOT IN ('paid', 'voided');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_payments_school_exception_due;
        DROP INDEX IF EXISTS msi_v2.idx_support_tickets_waiting_requester;
        DROP INDEX IF EXISTS msi_v2.idx_support_tickets_open_resolution_deadline;
        DROP INDEX IF EXISTS msi_v2.idx_support_tickets_open_response_deadline;
        DROP INDEX IF EXISTS msi_v2.idx_support_tickets_assignment_status_updated;
        DROP INDEX IF EXISTS msi_v2.idx_support_tickets_student_status_created;

        ALTER TABLE msi_v2.support_tickets
            DROP CONSTRAINT IF EXISTS support_tickets_requester_wait_check,
            DROP CONSTRAINT IF EXISTS support_tickets_resolution_target_check,
            DROP CONSTRAINT IF EXISTS support_tickets_response_target_check,
            DROP CONSTRAINT IF EXISTS support_tickets_priority_check,
            DROP COLUMN IF EXISTS requester_wait_seconds,
            DROP COLUMN IF EXISTS waiting_on_requester_at,
            DROP COLUMN IF EXISTS first_responded_at,
            DROP COLUMN IF EXISTS resolution_due_at,
            DROP COLUMN IF EXISTS first_response_due_at,
            DROP COLUMN IF EXISTS resolution_target_minutes,
            DROP COLUMN IF EXISTS first_response_target_minutes,
            DROP COLUMN IF EXISTS priority;

        DROP TABLE IF EXISTS msi_v2.support_ticket_sla_policies;
        """
    )
