"""People/profile domain facade."""

from shared.identity.account_service import (  # noqa: F401
    get_admin_student_profile,
    get_dashboard_student_profile,
    get_student_db_id_by_enrollment_id,
)
from web.backend.roles.admin.services.parent_service import (  # noqa: F401
    assign_parent_child,
    create_parent_account,
    list_parent_accounts,
    list_parent_children,
    remove_parent_child,
)
from shared.identity.account_service import (  # noqa: F401
    assign_teacher_to_group,
    delete_teacher_by_id,
    get_teacher_by_id,
    get_teacher_name_by_group,
    list_teachers,
    update_student_admin_profile,
    update_teacher_by_id,
    upsert_teacher,
)

__all__ = [
    "assign_parent_child",
    "assign_teacher_to_group",
    "create_parent_account",
    "delete_teacher_by_id",
    "get_admin_student_profile",
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "get_teacher_by_id",
    "get_teacher_name_by_group",
    "list_parent_accounts",
    "list_parent_children",
    "list_teachers",
    "remove_parent_child",
    "update_student_admin_profile",
    "update_teacher_by_id",
    "upsert_teacher",
]

