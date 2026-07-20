"""PostgreSQL persistence for teacher recruitment."""

from __future__ import annotations

from backend.modules.hr.recruitment.appointments.repository import (
    active_appointment_for_type,
    cancel_active_appointments,
    cancel_scheduled_appointments,
    complete_appointment,
    complete_historical_appointment,
    complete_interview_session,
    get_appointment_row,
    insert_appointment,
    list_appointment_conflicts,
    list_appointment_rows,
    set_appointment_status,
    start_interview_session,
    update_appointment,
)
from backend.modules.hr.recruitment.candidates.read_repository import (
    _CANDIDATE_COLUMNS,
    _candidate_joins,
    _visibility_clause,
    candidate_assignment_row,
    get_candidate_row,
    list_academy_lifecycle_assessment_rows,
    list_academy_lifecycle_lesson_rows,
    list_activity_rows,
    list_assignment_rows,
    list_candidate_rows,
    list_decision_queue_rows,
    list_note_rows,
    list_pipeline_rows,
    list_stage_history_rows,
)
from backend.modules.hr.recruitment.candidates.repository import (
    _stage_history_transition_source,
    delete_closed_candidate,
    insert_audit,
    insert_candidate,
    insert_note,
    list_trash_candidates_for_purge,
    touch_candidate,
    update_candidate,
    update_candidate_stage,
)
from backend.modules.hr.recruitment.decisions.repository import (
    candidate_actionable_approval_row,
    consume_approval,
    final_decision_for_approval,
    get_approval_by_id,
    get_approval_row,
    insert_approval_request,
    insert_final_decision,
    list_approval_rows,
    list_decision_rows,
    lock_candidate_decision_row,
    review_approval,
    revoke_open_approvals,
    void_latest_closed_decision,
)
from backend.modules.hr.recruitment.documents.repository import (
    get_document_row,
    insert_document,
    list_document_rows,
    remove_document,
)
from backend.modules.hr.recruitment.evaluations.repository import (
    ensure_candidate_assignment,
    get_evaluation_row,
    get_system_decision_for_evaluation,
    hod_account_has_subject_scope,
    insert_demo,
    insert_interview,
    insert_subject_test,
    latest_active_final_decision,
    list_demo_rows,
    list_interview_rows,
    list_subject_test_rows,
    list_valid_evaluator_accounts,
    responsible_account_row,
    void_evaluation,
    void_system_final_decision,
)
from backend.modules.hr.recruitment.handoffs.repository import (
    cancel_pending_candidate_tasks,
    delete_generated_academy_identity,
    ensure_academy_intake,
    ensure_active_teacher_intake,
    exact_academy_identity_match,
    insert_academy_direct_profile,
    link_academy_profile,
    list_teacher_account_ids_for_staff,
    list_teacher_handoff_rows,
    lock_academy_identity_rows,
    lock_academy_removal_row,
    lock_teacher_handoff_row,
    mark_academy_removed,
    mark_teacher_handoff_closed,
    restore_teacher_handoff,
    set_teacher_identity_enabled,
)
from backend.modules.hr.recruitment.notification_repository import (
    cancel_recruitment_notification_reminders,
    claimable_recruitment_notification_rows,
    insert_recruitment_notification,
    list_future_demo_appointments_for_recipient,
    list_recruitment_notification_rows,
    mark_recruitment_notification_failed,
    mark_recruitment_notification_read,
    mark_recruitment_notification_sending,
    mark_recruitment_notification_sent,
    mark_recruitment_notification_waiting_link,
    recover_stale_recruitment_notification_deliveries,
    recruitment_notification_unread_count,
)
from backend.modules.hr.recruitment.settings_repository import (
    active_subsource_exists,
    deactivate_recruitment_setting,
    insert_recruitment_setting_audit,
    list_recruitment_options,
    list_recruitment_setting_rows,
    list_sla_rule_rows,
    recruitment_setting_by_id,
    recruitment_setting_by_label_or_value,
    recruitment_setting_value_exists,
    save_recruitment_setting,
    update_sla_rule,
)
from backend.modules.hr.recruitment.tasks.repository import (
    candidate_automation_state_row,
    insert_task,
    list_task_rows,
    replace_assignments,
    replace_system_tasks,
    update_task,
)

_STAGE_HISTORY_TRANSITION_SOURCES = frozenset(
    {"manual", "automatic", "migration", "restored"}
)
_STAGE_HISTORY_TRANSITION_SOURCE_ALIASES = {
    "historical_restoration": "restored",
}

__all__ = [name for name in globals() if not name.startswith("_")]
