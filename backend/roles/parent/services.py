"""Compatibility facade for parent role services.

Parent DB access and workflow ownership moved to
``backend.domains.parents.service`` in DB-4. Keep this role-level module as a
temporary import surface for routes and tests while callers migrate.

Temporary compatibility wrapper. Delete after parent role routes import
``backend.domains.parents.service`` directly.
"""

from backend.domains.parents.service import (  # noqa: F401
    assign_parent_child,
    link_parent_via_invite,
    list_parent_accounts,
    list_parent_children,
    list_parent_client_children,
    list_student_payments,
    parent_can_access_dashboard,
    parent_can_access_student,
    parent_from_telegram_user_id,
    payment_summary_for_student,
    remove_parent_child,
    resolve_parent_child_dashboard,
)

__all__ = [
    "assign_parent_child",
    "link_parent_via_invite",
    "list_parent_accounts",
    "list_parent_children",
    "list_parent_client_children",
    "list_student_payments",
    "payment_summary_for_student",
    "parent_can_access_dashboard",
    "parent_can_access_student",
    "parent_from_telegram_user_id",
    "remove_parent_child",
    "resolve_parent_child_dashboard",
]
