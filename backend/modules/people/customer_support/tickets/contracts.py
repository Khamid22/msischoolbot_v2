"""Public Customer Support ticket use-case contract."""

from backend.modules.domains.support_cases.tickets.contracts import (
    TicketCategory,
    TicketLifecycleError,
    TicketNotFoundError,
    TicketStatus,
)
from backend.modules.people.customer_support.tickets.commands import (
    AssignTicketCommand,
    ChangeTicketStatusCommand,
    CustomerSupportTicketCommands,
    ReplyToTicketCommand,
    TicketMutationResult,
)
from backend.modules.people.customer_support.tickets.queries import (
    CustomerSupportTicketQueries,
    TicketDetailResult,
    TicketMessageResult,
    TicketQueueItem,
    TicketQueuePage,
    TicketQueueQuery,
)

__all__ = [
    "AssignTicketCommand",
    "ChangeTicketStatusCommand",
    "CustomerSupportTicketCommands",
    "CustomerSupportTicketQueries",
    "ReplyToTicketCommand",
    "TicketCategory",
    "TicketLifecycleError",
    "TicketNotFoundError",
    "TicketDetailResult",
    "TicketMessageResult",
    "TicketMutationResult",
    "TicketQueueItem",
    "TicketQueuePage",
    "TicketQueueQuery",
    "TicketStatus",
]
