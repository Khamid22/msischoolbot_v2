"""Public Customer Support ticket use-case contract."""

from backend.modules.domains.support_cases.tickets.contracts import (
    TicketCategory,
    TicketLifecycleError,
    TicketNotFoundError,
    TicketPriority,
    TicketSlaState,
    TicketStatus,
)
from backend.modules.people.customer_support.tickets.commands import (
    AssignTicketCommand,
    ChangeTicketPriorityCommand,
    ChangeTicketStatusCommand,
    CustomerSupportTicketCommands,
    ReplyToTicketCommand,
    SetTicketWaitingCommand,
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
    "ChangeTicketPriorityCommand",
    "ChangeTicketStatusCommand",
    "CustomerSupportTicketCommands",
    "CustomerSupportTicketQueries",
    "ReplyToTicketCommand",
    "SetTicketWaitingCommand",
    "TicketCategory",
    "TicketLifecycleError",
    "TicketNotFoundError",
    "TicketPriority",
    "TicketSlaState",
    "TicketDetailResult",
    "TicketMessageResult",
    "TicketMutationResult",
    "TicketQueueItem",
    "TicketQueuePage",
    "TicketQueueQuery",
    "TicketStatus",
]
