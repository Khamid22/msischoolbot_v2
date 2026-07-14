"""Public recruitment service contract."""

from backend.modules.hr.recruitment.repository import (
    create_teacher_candidate,
    delete_candidate_event,
    get_teacher_candidate,
    get_teacher_candidate_training_summary,
    list_teacher_candidates,
    update_candidate_event,
    update_teacher_candidate_status,
)

__all__ = [
    "create_teacher_candidate",
    "delete_candidate_event",
    "get_teacher_candidate",
    "get_teacher_candidate_training_summary",
    "list_teacher_candidates",
    "update_candidate_event",
    "update_teacher_candidate_status",
]
