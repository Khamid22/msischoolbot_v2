"""Compatibility wrapper for parent admin services.

Parent account service ownership moved to ``backend.domains.parents.service`` in
DB-4. Keep this module temporarily so admin routes and older imports continue
to work while callers migrate to the parent domain package.
"""

from backend.domains.parents.service import (  # noqa: F401
    _to_invite_child,
    assign_parent_child,
    delete_parent_account,
    list_linked_parents_for_student,
    list_parent_accounts,
    list_parent_children,
    remove_parent_child,
)

__all__ = [
    "_to_invite_child",
    "assign_parent_child",
    "delete_parent_account",
    "list_linked_parents_for_student",
    "list_parent_accounts",
    "list_parent_children",
    "remove_parent_child",
]
