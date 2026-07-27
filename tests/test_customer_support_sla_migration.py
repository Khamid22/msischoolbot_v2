"""Static safety checks for the additive Customer Support SLA migration."""

from pathlib import Path

MIGRATION = Path("database/alembic/versions/0045_customer_support_ticket_sla.py")


def test_customer_support_sla_migration_is_additive_and_anchors_backfill():
    source = MIGRATION.read_text(encoding="utf-8")
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]

    assert 'down_revision = "0044_student_identifier_sequence"' in source
    assert "support_ticket_sla_policies" in upgrade
    assert "first_response_due_at" in upgrade
    assert "resolution_due_at" in upgrade
    assert "waiting_on_requester_at" in upgrade
    assert "requester_wait_seconds" in upgrade
    assert "ticket.created_at + INTERVAL '240 minutes'" in upgrade
    assert "ticket.created_at + INTERVAL '1440 minutes'" in upgrade
    assert "MIN(message.created_at)" in upgrade
    assert "DELETE FROM" not in upgrade.upper()
    assert "TRUNCATE" not in upgrade.upper()


def test_customer_support_sla_migration_seeds_all_priority_targets_and_indexes():
    source = MIGRATION.read_text(encoding="utf-8")
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]

    for seed in (
        "(NULL, 'urgent', 30, 240)",
        "(NULL, 'high', 120, 720)",
        "(NULL, 'normal', 240, 1440)",
        "(NULL, 'low', 480, 2880)",
    ):
        assert seed in upgrade
    for index_name in (
        "idx_support_tickets_assignment_status_updated",
        "idx_support_tickets_open_response_deadline",
        "idx_support_tickets_open_resolution_deadline",
        "idx_payments_school_exception_due",
    ):
        assert index_name in upgrade
