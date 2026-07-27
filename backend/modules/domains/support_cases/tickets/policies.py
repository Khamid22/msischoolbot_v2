"""SLA and lifecycle rules for support tickets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)

DEFAULT_FIRST_RESPONSE_MINUTES = 240
DEFAULT_RESOLUTION_MINUTES = 1_440
DUE_SOON_DIVISOR = 4


@dataclass(frozen=True)
class TicketSlaTargets:
    first_response_minutes: int
    resolution_minutes: int

    def __post_init__(self) -> None:
        if self.first_response_minutes <= 0:
            raise ValueError("First-response target must be positive.")
        if self.resolution_minutes < self.first_response_minutes:
            raise ValueError("Resolution target cannot be shorter than first response.")


@dataclass(frozen=True)
class TicketSlaSnapshot:
    status: TicketStatus
    first_response_target_minutes: int
    resolution_target_minutes: int
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    first_responded_at: datetime | None
    waiting_on_requester_at: datetime | None
    resolved_at: datetime | None


def deadlines_for_priority_change(
    *,
    created_at: datetime,
    targets: TicketSlaTargets,
    accumulated_wait_seconds: int,
) -> tuple[datetime, datetime]:
    """Anchor recalculated deadlines to creation, never to the change time."""

    wait_duration = timedelta(seconds=max(0, accumulated_wait_seconds))
    return (
        created_at + timedelta(minutes=targets.first_response_minutes),
        created_at + timedelta(minutes=targets.resolution_minutes) + wait_duration,
    )


def sla_state(snapshot: TicketSlaSnapshot, *, now: datetime) -> TicketSlaState:
    """Return the most urgent active SLA state for a ticket."""

    if snapshot.status is TicketStatus.RESOLVED:
        if (
            snapshot.resolved_at is not None
            and snapshot.resolution_due_at is not None
            and snapshot.resolved_at <= snapshot.resolution_due_at
        ):
            return TicketSlaState.MET
        return TicketSlaState.BREACHED
    if (
        snapshot.waiting_on_requester_at is not None
        and snapshot.first_responded_at is not None
    ):
        return TicketSlaState.PAUSED

    active_due_at = (
        snapshot.first_response_due_at
        if snapshot.first_responded_at is None
        else snapshot.resolution_due_at
    )
    target_minutes = (
        snapshot.first_response_target_minutes
        if snapshot.first_responded_at is None
        else snapshot.resolution_target_minutes
    )
    if active_due_at is None:
        return TicketSlaState.NOT_APPLICABLE
    if now >= active_due_at:
        return TicketSlaState.BREACHED
    if active_due_at - now <= timedelta(minutes=target_minutes / DUE_SOON_DIVISOR):
        return TicketSlaState.DUE_SOON
    return TicketSlaState.ON_TRACK


DEFAULT_SLA_TARGETS = TicketSlaTargets(
    first_response_minutes=DEFAULT_FIRST_RESPONSE_MINUTES,
    resolution_minutes=DEFAULT_RESOLUTION_MINUTES,
)

PRIORITY_SORT_RANK = {
    TicketPriority.URGENT: 0,
    TicketPriority.HIGH: 1,
    TicketPriority.NORMAL: 2,
    TicketPriority.LOW: 3,
}


__all__ = [
    "DEFAULT_FIRST_RESPONSE_MINUTES",
    "DEFAULT_RESOLUTION_MINUTES",
    "DEFAULT_SLA_TARGETS",
    "DUE_SOON_DIVISOR",
    "PRIORITY_SORT_RANK",
    "TicketSlaSnapshot",
    "TicketSlaTargets",
    "deadlines_for_priority_change",
    "sla_state",
]
