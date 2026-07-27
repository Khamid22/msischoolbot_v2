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
    TicketStatus,
    normalize_ticket_category,
    normalize_ticket_status,
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
    assigned_staff_id: int | None
    assigned_staff_name: str
    created_at: str
    updated_at: str
    cursor_updated_at: str
    resolved_at: str
    messages: tuple[TicketMessageData, ...]


def _now() -> datetime:
    return datetime.now(UTC)


def _text(value: object) -> str:
    return str(value or "").strip()


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
        raise ValueError(
            f"Ticket message cannot exceed {MAX_TICKET_MESSAGE_LENGTH} characters."
        )
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
        status=TicketStatus(normalize_ticket_status(row["status"])),
        assigned_staff_id=int(assigned_staff_id) if assigned_staff_id else None,
        assigned_staff_name=_text(row["assigned_to"]),
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
    return get_parent_ticket(conn, parent_id=parent_id, ticket_id=ticket_id)


def list_support_tickets(
    conn: Connection,
    *,
    allowed_school_ids: frozenset[int],
    all_schools: bool,
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
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
        raise TicketLifecycleError("Reopen the ticket before replying.")
    timestamp = _now()
    repository.insert_staff_ticket_message_row(
        conn,
        ticket_id=ticket_id,
        author_type="customer_support",
        staff_id=staff_id,
        body=_validate_message(body),
        created_at=timestamp,
    )
    next_status = (
        TicketStatus.IN_PROGRESS
        if current.status is TicketStatus.NEW
        else current.status
    )
    repository.update_ticket_state_row(
        conn,
        ticket_id=ticket_id,
        status=next_status.value,
        assigned_staff_id=current.assigned_staff_id or staff_id,
        resolved_at=None,
        updated_at=timestamp,
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
    allowed_school_ids: frozenset[int],
    all_schools: bool,
) -> TicketData:
    get_support_ticket(
        conn,
        ticket_id=ticket_id,
        allowed_school_ids=allowed_school_ids,
        all_schools=all_schools,
        for_update=True,
    )
    timestamp = _now()
    repository.update_ticket_state_row(
        conn,
        ticket_id=ticket_id,
        status=status.value,
        assigned_staff_id=assigned_staff_id,
        resolved_at=timestamp if status is TicketStatus.RESOLVED else None,
        updated_at=timestamp,
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
    "create_parent_ticket",
    "get_parent_ticket",
    "get_support_ticket",
    "list_parent_tickets",
    "list_support_tickets",
    "reply_to_parent_ticket",
    "reply_to_support_ticket",
    "update_support_ticket",
]
