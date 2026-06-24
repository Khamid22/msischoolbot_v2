"""Parent role service facade."""

from datetime import datetime

from shared.db import queries
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


def link_parent_via_invite(student_row_id, full_name, phone, telegram_username):
    """Create/update a parent CLIENT record from the invite form and link them
    to the student. Writes to the dedicated `parents` tables — never `admins`."""
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with queries.connect_auth_db() as conn:
        parent = queries.link_parent_from_invite(
            conn,
            student_row_id=int(student_row_id),
            full_name=full_name,
            phone=phone,
            telegram_username=telegram_username,
            now=now,
        )
    return dict(parent) if parent else None


__all__ = [
    "assign_parent_child",
    "create_parent_account",
    "link_parent_via_invite",
    "list_parent_accounts",
    "list_parent_children",
    "list_student_payments",
    "payment_summary_for_student",
    "remove_parent_child",
]

