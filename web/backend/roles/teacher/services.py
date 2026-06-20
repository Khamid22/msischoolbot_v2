"""Teacher role service facade."""

from shared.identity.account_service import (  # noqa: F401
    assign_teacher_to_group,
    get_teacher_by_id,
    get_teacher_name_by_group,
    list_teachers,
    update_teacher_by_id,
    upsert_teacher,
)
from web.backend.roles.admin.services.teacher_candidate_service import (  # noqa: F401
    create_teacher_candidate,
    get_teacher_candidate,
    list_teacher_candidates,
    update_teacher_candidate_status,
)

__all__ = [
    "assign_teacher_to_group",
    "create_teacher_candidate",
    "get_teacher_by_id",
    "get_teacher_candidate",
    "get_teacher_name_by_group",
    "list_teacher_candidates",
    "list_teachers",
    "update_teacher_by_id",
    "update_teacher_candidate_status",
    "upsert_teacher",
]

