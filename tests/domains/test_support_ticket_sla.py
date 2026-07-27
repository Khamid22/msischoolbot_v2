"""Support ticket SLA policy and lifecycle calculations."""

from datetime import UTC, datetime, timedelta

from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)
from backend.modules.domains.support_cases.tickets.policies import (
    TicketSlaSnapshot,
    TicketSlaTargets,
    deadlines_for_priority_change,
    sla_state,
)


def _snapshot(now: datetime, **overrides) -> TicketSlaSnapshot:
    values = {
        "status": TicketStatus.IN_PROGRESS,
        "first_response_target_minutes": 120,
        "resolution_target_minutes": 720,
        "first_response_due_at": now - timedelta(hours=1),
        "resolution_due_at": now + timedelta(hours=4),
        "first_responded_at": now - timedelta(hours=2),
        "waiting_on_requester_at": None,
        "resolved_at": None,
    }
    values.update(overrides)
    return TicketSlaSnapshot(**values)


def test_priority_change_reanchors_deadlines_to_creation_and_preserves_wait_time():
    created_at = datetime(2026, 7, 27, 8, tzinfo=UTC)
    response_due_at, resolution_due_at = deadlines_for_priority_change(
        created_at=created_at,
        targets=TicketSlaTargets(
            first_response_minutes=30,
            resolution_minutes=240,
        ),
        accumulated_wait_seconds=45 * 60,
    )

    assert response_due_at == created_at + timedelta(minutes=30)
    assert resolution_due_at == created_at + timedelta(minutes=285)


def test_sla_state_distinguishes_breached_due_soon_paused_and_met():
    now = datetime(2026, 7, 27, 12, tzinfo=UTC)

    assert sla_state(
        _snapshot(now, resolution_due_at=now - timedelta(seconds=1)),
        now=now,
    ) is TicketSlaState.BREACHED
    assert sla_state(
        _snapshot(now, resolution_due_at=now + timedelta(minutes=100)),
        now=now,
    ) is TicketSlaState.DUE_SOON
    assert sla_state(
        _snapshot(now, waiting_on_requester_at=now - timedelta(hours=1)),
        now=now,
    ) is TicketSlaState.PAUSED
    assert sla_state(
        _snapshot(
            now,
            status=TicketStatus.RESOLVED,
            resolved_at=now - timedelta(minutes=1),
            resolution_due_at=now,
        ),
        now=now,
    ) is TicketSlaState.MET


def test_waiting_does_not_hide_an_unanswered_first_response_breach():
    now = datetime(2026, 7, 27, 12, tzinfo=UTC)
    state = sla_state(
        _snapshot(
            now,
            status=TicketStatus.NEW,
            first_responded_at=None,
            first_response_due_at=now - timedelta(minutes=1),
            waiting_on_requester_at=now - timedelta(hours=1),
        ),
        now=now,
    )

    assert state is TicketSlaState.BREACHED
    assert TicketPriority.URGENT.value == "urgent"
