"""Compatibility facade for Recruitment handoff persistence."""

from backend.modules.hr.recruitment.handoffs.intake_repository import (
    active_subject_program_id,
    ensure_academy_intake,
    ensure_active_teacher_intake,
    exact_academy_identity_match,
    insert_academy_direct_profile,
    link_academy_profile,
    list_teacher_handoff_rows,
    sync_academy_subject_from_candidate,
)
from backend.modules.hr.recruitment.handoffs.lifecycle_repository import (
    cancel_pending_candidate_tasks,
    delete_generated_academy_identity,
    list_teacher_account_ids_for_staff,
    lock_academy_identity_rows,
    lock_academy_removal_row,
    lock_teacher_handoff_row,
    mark_academy_removed,
    mark_teacher_handoff_closed,
    restore_teacher_handoff,
    set_teacher_identity_enabled,
)

__all__ = [name for name in globals() if not name.startswith("_")]
