"""Compatibility facade for the ticket repository.

New domain code imports the private repository from
``backend.modules.domains.support_cases.tickets``.
"""

from backend.modules.domains.support_cases.tickets.repository import (
    count_complaints_by_parent,
    get_parent_complaint_row,
    insert_complaint_message_row,
    insert_parent_complaint_row,
    list_complaint_message_rows,
    list_parent_complaint_rows,
    update_parent_complaint_row,
)

__all__ = [
    "count_complaints_by_parent",
    "get_parent_complaint_row",
    "insert_complaint_message_row",
    "insert_parent_complaint_row",
    "list_complaint_message_rows",
    "list_parent_complaint_rows",
    "update_parent_complaint_row",
]
