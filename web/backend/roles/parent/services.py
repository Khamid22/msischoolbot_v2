"""Parent role service facade."""

from shared.db import queries
from shared.identity.parent_accounts import (
    link_parent_via_invite,
    parent_children,
    parent_from_telegram_user_id,
)
from web.backend.roles.admin.services.parent_service import (  # noqa: F401
    _to_invite_child,
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


def list_parent_client_children(parent_id):
    """Children for a parent CLIENT account, shaped for the parent portal."""
    raw_rows = parent_children(parent_id)
    if not raw_rows:
        return []
    with queries.connect_auth_db() as conn:
        return [
            child
            for child in (_to_invite_child(row, conn=conn) for row in raw_rows)
            if child
        ]


__all__ = [
    "assign_parent_child",
    "create_parent_account",
    "link_parent_via_invite",
    "list_parent_accounts",
    "list_parent_client_children",
    "list_parent_children",
    "list_student_payments",
    "payment_summary_for_student",
    "parent_from_telegram_user_id",
    "remove_parent_child",
]
