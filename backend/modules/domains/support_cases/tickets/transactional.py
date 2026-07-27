"""Transaction-bound ticket operations shared by person modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.core.api.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    normalize_page_size,
)
from backend.core.unit_of_work import Connection
from backend.modules.domains.parent_relationships.contracts import (
    parent_can_access_student_on_connection,
)
from backend.modules.domains.support_cases.tickets import repository
from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketCategory,
    TicketPriority,
    TicketSlaState,
    TicketStatus,
    normalize_ticket_category,
    normalize_ticket_priority,
    normalize_ticket_status,
)
from backend.modules.domains.support_cases.tickets.policies import (
    TicketSlaSnapshot,
    sla_state,
)

MAX_TICKET_TOPIC_LENGTH = 160
MAX_TICKET_MESSAGE_LENGTH = 4_000
TICKET_STATUS_RANK = {
    TicketStatus.NEW: 0,
    TicketStatus.ESCALATED: 1,
    TicketStatus.IN_PROGRESS: 2,
    TicketStatus.RESOLVED: 3,
}


class TicketNotFoundError(LookupError):
    pass


class TicketLifecycleError(ValueError):
    pass


@dataclass(frozen=True)
class TicketMessageData:
    message_id: int
    author_type: str
    author_name: str
    body: str
    created_at: str


@dataclass(frozen=True)
class TicketData:
    ticket_id: int
    parent_id: int
    parent_name: str
    student_id: int | None
    student_row_id: int
    student_name: str
    student_code: str
    school_id: int
    school_name: str
    category: TicketCategory
    topic: str
    status: TicketStatus
    priority: TicketPriority
    sla_state: TicketSlaState
    assigned_staff_id: int | None
    assigned_staff_name: str
    first_response_due_at: str
    resolution_due_at: str
    first_responded_at: str
    waiting_on_requester_at: str
    requester_wait_seconds: int
    created_at: str
    updated_at: str
    cursor_updated_at: str
    resolved_at: str
    messages: tuple[TicketMessageData, ...]


def _now() -> datetime:
    return datetime.now(UTC)


def _text(value: object) -> str:
    return str(value or "").strip()


def _datetime(value: object) -> datetime | None:
    normalized = _text(value).replace("Z", "+00:00")
    if not normalized:
        return None
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _row_value(row, key: str, default: object = None) -> object:
    try:
        return row[key]
    except (KeyError, TypeError):
        return default


def _integer(value: object) -> int:
    return int(str(value or 0))


def _validate_topic(value: object) -> str:
    topic = _text(value)
    if len(topic) < 2:
        raise ValueError("Ticket topic must contain at least 2 characters.")
    if len(topic) > MAX_TICKET_TOPIC_LENGTH:
        raise ValueError(f"Ticket topic cannot exceed {MAX_TICKET_TOPIC_LENGTH} characters.")
    return topic


def _validate_message(value: object, *, minimum: int = 1) -> str:
    body = _text(value)
    if len(body) < minimum:
        raise ValueError("Ticket message is too short.")
    if len(body) > MAX_TICKET_MESSAGE_LENGTH:
        raise ValueError(f"Ticket message cannot exceed {MAX_TICKET_MESSAGE_LENGTH} characters.")
    return body


def _messages(conn: Connection, ticket_id: int) -> tuple[TicketMessageData, ...]:
    return tuple(
        TicketMessageData(
            message_id=int(row["id"]),
            author_type=_text(row["author_role"]) or "system",
            author_name=_text(row["author_login"]),
            body=_text(row["body"]),
            created_at=_text(row["created_at"]),
        )
        for row in repository.list_complaint_message_rows(conn, ticket_id)
    )


def _ticket(conn: Connection, row) -> TicketData:
    assigned_staff_id = row["assigned_to_staff_id"]
    canonical_student_id = int(row["student_id"] or 0)
    status = TicketStatus(normalize_ticket_status(row["status"]))
    first_response_due_at = _datetime(_row_value(row, "first_response_due_at"))
    resolution_due_at = _datetime(_row_value(row, "resolution_due_at"))
    first_responded_at = _datetime(_row_value(row, "first_responded_at"))
    waiting_on_requester_at = _datetime(_row_value(row, "waiting_on_requester_at"))
    resolved_at = _datetime(row["resolved_at"])
    return TicketData(
        ticket_id=int(row["id"]),
        parent_id=int(row["parent_admin_id"] or 0),
        parent_name=_text(row["parent_display_name"] or row["parent_login"]),
        student_id=canonical_student_id or None,
        student_row_id=int(row["student_row_id"] or 0),
        student_name=_text(row["student_name"]),
        student_code=_text(row["student_code"]),
        school_id=int(row["school_id"] or 0),
        school_name=_text(row["school_name"]),
        category=TicketCategory(normalize_ticket_category(row["category"])),
        topic=_text(row["topic"]),
        status=status,
        priority=TicketPriority(normalize_ticket_priority(_row_value(row, "priority"))),
        sla_state=sla_state(
            TicketSlaSnapshot(
                status=status,
                first_response_target_minutes=_integer(
                    _row_value(row, "first_response_target_minutes", 0) or 0
                ),
                resolution_target_minutes=_integer(
                    _row_value(row, "resolution_target_minutes", 0) or 0
                ),
                first_response_due_at=first_response_due_at,
                resolution_due_at=resolution_due_at,
                first_responded_at=first_responded_at,
                waiting_on_requester_at=waiting_on_requester_at,
                resolved_at=resolved_at,
            ),
            now=_now(),
        ),
        assigned_staff_id=int(assigned_staff_id) if assigned_staff_id else None,
        assigned_staff_name=_text(row["assigned_to"]),
        first_response_due_at=_text(_row_value(row, "first_response_due_at")),
        resolution_due_at=_text(_row_value(row, "resolution_due_at")),
        first_responded_at=_text(_row_value(row, "first_responded_at")),
        waiting_on_requester_at=_text(_row_value(row, "waiting_on_requester_at")),
        requester_wait_seconds=_integer(_row_value(row, "requester_wait_seconds", 0) or 0),
        created_at=_text(row["created_at"]),
        updated_at=_text(row["updated_at"]),
        cursor_updated_at=_text(row["cursor_updated_at"]),
        resolved_at=_text(row["resolved_at"]),
        messages=_messages(conn, int(row["id"])),
    )


def list_parent_tickets(
    conn: Connection,
    *,
    parent_id: int,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[TicketData, ...]:
    rows = repository.list_parent_complaint_rows(conn, parent_id)
    return tuple(_ticket(conn, row) for row in rows[: normalize_page_size(limit)])


def get_parent_ticket(
    conn: Connection,
    *,
    parent_id: int,
    ticket_id: int,
) -> TicketData:
    row = repository.get_parent_ticket_row(
        conn,
        ticket_id=ticket_id,
        parent_id=parent_id,
    )
    if row is None:
        raise TicketNotFoundError("Ticket was not found.")
    return _ticket(conn, row)


def create_parent_ticket(
    conn: Connection,
    *,
    parent_id: int,
    student_row_id: int,
    category: TicketCategory | str,
    topic: str,
    message: str,
) -> TicketData:
    if not parent_can_access_student_on_connection(
        conn,
        parent_id=parent_id,
        student_row_id=student_row_id,
    ):
        raise ValueError("This child is not linked to your parent account.")
    timestamp = _now()
    inserted = repository.insert_parent_complaint_row(
        conn,
        parent_admin_id=parent_id,
        student_row_id=student_row_id,
        category=normalize_ticket_category(category),
        topic=_validate_topic(topic),
        message=_validate_message(message, minimum=5),
        status=TicketStatus.NEW.value,
        created_at=timestamp.isoformat(),
        updated_at=timestamp.isoformat(),
    )
    if inserted is None:
        raise RuntimeError("Ticket could not be created.")
    repository.insert_ticket_audit_event(
        conn,
        ticket_id=int(inserted["id"]),
        event_type="support_ticket.created",
        actor_staff_id=None,
        actor_account_id=None,
        detail={"parent_id": int(parent_id), "student_row_id": int(student_row_id)},
        created_at=timestamp,
    )
    return get_parent_ticket(conn, parent_id=parent_id, ticket_id=int(inserted["id"]))


def reply_to_parent_ticket(
    conn: Connection,
    *,
    parent_id: int,
    ticket_id: int,
    body: str,
) -> TicketData:
    row = repository.get_parent_ticket_row(
        conn,
        ticket_id=ticket_id,
        parent_id=parent_id,
        for_update=True,
    )
    if row is None:
        raise TicketNotFoundError("Ticket was not found.")
    status = TicketStatus(normalize_ticket_status(row["status"]))
    if status is TicketStatus.RESOLVED:
        raise TicketLifecycleError("Resolved tickets are read-only. Create a new ticket.")
    timestamp = _now()
    repository.set_ticket_waiting_on_requester_row(
        conn,
        ticket_id=ticket_id,
        is_waiting=False,
        changed_at=timestamp,
    )
    repository.insert_complaint_message_row(
        conn,
        complaint_id=ticket_id,
        author_role="parent",
        author_login="",
        body=_validate_message(body),
        created_at=timestamp.isoformat(),
    )
    repository.update_ticket_state_row(
        conn,
        ticket_id=ticket_id,
        status=status.value,
        assigned_staff_id=row["assigned_to_staff_id"],
        resolved_at=None,
        updated_at=timestamp,
    )
    repository.insert_ticket_audit_event(
        conn,
        ticket_id=ticket_id,
        event_type="support_ticket.parent_replied",
        actor_staff_id=None,
        actor_account_id=None,
        detail={"parent_id": int(parent_id)},
        created_at=timestamp,
    )
    return get_parent_ticket(conn, parent_id=parent_id, ticket_id=ticket_id)


def list_support_tickets(
    conn: Connection,
    *,
    allowed_school_ids: frozenset[int],
    all_schools: bool,
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    sla_state_filter: TicketSlaState | None = None,
    search_text: str = "",
    school_id: int | None = None,
    assigned_staff_id: int | None = None,
    is_unassigned: bool = False,
    cursor_status_rank: int = -1,
    cursor_updated_at: str = "",
    cursor_id: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[TicketData, ...]:
    rows = repository.list_support_ticket_rows(
        conn,
        search_text=search_text,
        selected_school_id=school_id,
        allowed_school_ids=tuple(sorted(allowed_school_ids)),
        all_schools=all_schools,
        status=status.value if status else "",
        category=category.value if category else "",
        priority=priority.value if priority else "",
        sla_state=sla_state_filter.value if sla_state_filter else "",
        assigned_staff_id=assigned_staff_id,
        is_unassigned=is_unassigned,
        cursor_status_rank=cursor_status_rank,
        cursor_updated_at=cursor_updated_at,
        cursor_id=cursor_id,
        limit=min(max(1, int(limit)), MAX_PAGE_SIZE + 1),
    )
    return tuple(_ticket(conn, row) for row in rows)


def get_support_ticket(
    conn: Connection,
    *,
    ticket_id: int,
    allowed_school_ids: frozenset[int],
    all_schools: bool,
    for_update: bool = False,
) -> TicketData:
    row = repository.get_ticket_row(conn, ticket_id=ticket_id, for_update=for_update)
    if row is None:
        raise TicketNotFoundError("Ticket was not found.")
    school_id = int(row["school_id"] or 0)
    if not all_schools and school_id not in allowed_school_ids:
        raise TicketNotFoundError("Ticket was not found.")
    return _ticket(conn, row)


def reply_to_support_ticket(
    conn: Connection,
    *,
    ticket_id: int,
    staff_id: int,
    account_id: int | None,
    allowed_school_ids: frozenset[int],
    all_schools: bool,
    body: str,
) -> TicketData:
    current = get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
        for_update=True,
    )
    if current.status is TicketStatus.RESOLVED:
        raise TicketLifecycleError("Resolved tickets are read-only. Create a new ticket.")
    timestamp = _now()
    repository.insert_staff_ticket_message_row(
        conn,
        ticket_id=ticket_id,
        author_type="customer_support",
        staff_id=staff_id,
        body=_validate_message(body),
        created_at=timestamp,
    )
    repository.mark_first_staff_response_row(
        conn,
        ticket_id=ticket_id,
        responded_at=timestamp,
    )
    next_status = TicketStatus.IN_PROGRESS if current.status is TicketStatus.NEW else current.status
    repository.update_ticket_state_row(
        conn,
        ticket_id=ticket_id,
        status=next_status.value,
        assigned_staff_id=current.assigned_staff_id or staff_id,
        resolved_at=None,
        updated_at=timestamp,
    )
    repository.insert_ticket_audit_event(
        conn,
        ticket_id=ticket_id,
        event_type="support_ticket.staff_replied",
        actor_staff_id=staff_id,
        actor_account_id=account_id,
        detail={
            "previous_status": current.status.value,
            "status": next_status.value,
        },
        created_at=timestamp,
    )
    return get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
    )


def update_support_ticket(
    conn: Connection,
    *,
    ticket_id: int,
    assigned_staff_id: int | None,
    status: TicketStatus,
    actor_staff_id: int | None = None,
    actor_account_id: int | None = None,
    reason: str = "",
    allowed_school_ids: frozenset[int],
    all_schools: bool,
) -> TicketData:
    current = get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
        for_update=True,
    )
    if current.status is TicketStatus.RESOLVED and status is not TicketStatus.RESOLVED:
        raise TicketLifecycleError("Resolved tickets cannot be reopened.")
    timestamp = _now()
    repository.update_ticket_state_row(
        conn,
        ticket_id=ticket_id,
        status=status.value,
        assigned_staff_id=assigned_staff_id,
        resolved_at=timestamp if status is TicketStatus.RESOLVED else None,
        updated_at=timestamp,
    )
    event_type = "support_ticket.updated"
    if current.assigned_staff_id != assigned_staff_id:
        event_type = "support_ticket.assignment_changed"
    if current.status is not status:
        event_type = {
            TicketStatus.ESCALATED: "support_ticket.escalated",
            TicketStatus.RESOLVED: "support_ticket.resolved",
        }.get(status, "support_ticket.status_changed")
    repository.insert_ticket_audit_event(
        conn,
        ticket_id=ticket_id,
        event_type=event_type,
        actor_staff_id=actor_staff_id,
        actor_account_id=actor_account_id,
        detail={
            "previous_status": current.status.value,
            "status": status.value,
            "previous_assigned_staff_id": current.assigned_staff_id,
            "assigned_staff_id": assigned_staff_id,
            "reason": _text(reason),
        },
        created_at=timestamp,
    )
    return get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
    )


def change_ticket_priority(
    conn: Connection,
    *,
    ticket_id: int,
    priority: TicketPriority,
    actor_staff_id: int,
    actor_account_id: int | None,
    allowed_school_ids: frozenset[int],
    all_schools: bool,
) -> TicketData:
    current = get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
        for_update=True,
    )
    if current.status is TicketStatus.RESOLVED:
        raise TicketLifecycleError("Resolved tickets are read-only.")
    timestamp = _now()
    updated = repository.update_ticket_priority_row(
        conn,
        ticket_id=ticket_id,
        priority=priority.value,
        updated_at=timestamp,
    )
    if updated is None:
        raise RuntimeError("No active SLA policy is available for this ticket.")
    repository.insert_ticket_audit_event(
        conn,
        ticket_id=ticket_id,
        event_type="support_ticket.priority_changed",
        actor_staff_id=actor_staff_id,
        actor_account_id=actor_account_id,
        detail={
            "previous_priority": current.priority.value,
            "priority": priority.value,
        },
        created_at=timestamp,
    )
    return get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
    )


def set_ticket_waiting_on_requester(
    conn: Connection,
    *,
    ticket_id: int,
    is_waiting: bool,
    actor_staff_id: int,
    actor_account_id: int | None,
    allowed_school_ids: frozenset[int],
    all_schools: bool,
) -> TicketData:
    current = get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
        for_update=True,
    )
    if current.status is TicketStatus.RESOLVED:
        raise TicketLifecycleError("Resolved tickets are read-only.")
    if is_waiting and not current.first_responded_at:
        raise TicketLifecycleError(
            "Send the first staff response before waiting on the parent."
        )
    timestamp = _now()
    repository.set_ticket_waiting_on_requester_row(
        conn,
        ticket_id=ticket_id,
        is_waiting=is_waiting,
        changed_at=timestamp,
    )
    repository.insert_ticket_audit_event(
        conn,
        ticket_id=ticket_id,
        event_type=(
            "support_ticket.waiting_on_requester"
            if is_waiting
            else "support_ticket.requester_wait_cleared"
        ),
        actor_staff_id=actor_staff_id,
        actor_account_id=actor_account_id,
        detail={"is_waiting": is_waiting},
        created_at=timestamp,
    )
    return get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
    )


__all__ = [
    "MAX_TICKET_MESSAGE_LENGTH",
    "MAX_TICKET_TOPIC_LENGTH",
    "TICKET_STATUS_RANK",
    "TicketData",
    "TicketLifecycleError",
    "TicketMessageData",
    "TicketNotFoundError",
    "change_ticket_priority",
    "create_parent_ticket",
    "get_parent_ticket",
    "get_support_ticket",
    "list_parent_tickets",
    "list_support_tickets",
    "reply_to_parent_ticket",
    "reply_to_support_ticket",
    "set_ticket_waiting_on_requester",
    "update_support_ticket",
]
