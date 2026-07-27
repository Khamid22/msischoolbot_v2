"""Public reporting read models."""

from backend.modules.domains.communications.contracts import list_announcements
from backend.modules.domains.reporting.service import (
    academic_director_workspace_cards,
    ceo_workspace_cards,
    customer_support_workspace_cards,
)

list_workspace_announcements = list_announcements

__all__ = [
    "academic_director_workspace_cards",
    "ceo_workspace_cards",
    "customer_support_workspace_cards",
    "list_workspace_announcements",
]
