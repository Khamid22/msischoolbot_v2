"""Parent role service facade."""

from web.backend.roles.admin.services.parent_service import (  # noqa: F401
    assign_parent_child,
    create_parent_account,
    list_parent_accounts,
    list_parent_children,
    remove_parent_child,
)
from web.backend.domains.payments.service import (  # noqa: F401
    list_student_payments,
    payment_summary_for_student,
)

__all__ = [
    "assign_parent_child",
    "create_parent_account",
    "list_parent_accounts",
    "list_parent_children",
    "list_student_payments",
    "payment_summary_for_student",
    "remove_parent_child",
]

