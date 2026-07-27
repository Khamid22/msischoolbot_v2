"""Academic Director queries exposed to its workspace."""

from backend.modules.domains.identity.contracts import (
    list_active_subjects,
    list_head_of_department_accounts,
)

__all__ = ["list_active_subjects", "list_head_of_department_accounts"]
