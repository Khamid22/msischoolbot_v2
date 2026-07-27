"""Academic Director commands.

Persistence stays in the identity domain; this module owns the actor-specific
orchestration boundary used by the Academic Director workspace.
"""

from backend.modules.domains.identity.contracts import (
    create_academic_director_account,
    create_head_of_department_account,
    reset_head_of_department_password,
)

__all__ = [
    "create_academic_director_account",
    "create_head_of_department_account",
    "reset_head_of_department_password",
]
