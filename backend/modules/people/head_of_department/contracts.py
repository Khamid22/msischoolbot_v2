"""Public Head of Department orchestration interface."""

from backend.modules.domains.academics.contracts import head_of_department_workspace_cards
from backend.modules.domains.identity.contracts import (
    current_auth_login,
    current_auth_role,
    current_staff_id,
)
from backend.modules.domains.recruitment.workspace_contracts import (
    register_head_of_department_recruitment_routes,
)
from backend.modules.domains.reporting.contracts import list_workspace_announcements
from backend.modules.domains.teacher_academy.contracts import (
    AddAcademyAssessmentForm,
    SyncAcademyLessonsForm,
    TeacherAcademyMutationResult,
    UpdateAcademyAssignmentForm,
    UpdateAcademyStatusForm,
    add_assessment_response,
    can_user_manage_academy_assignment,
    can_user_manage_academy_teacher,
    delete_assessment_response,
    filter_rows_by_subject_scope,
    hod_subject_ids_for_context,
    list_academy_timetable_events,
    list_teacher_academy_page_context,
    sync_lessons_response,
    update_assignment_response,
    update_status_response,
)
from backend.modules.people.head_of_department.module import PERSON_MODULE

list_announcements = list_workspace_announcements

__all__ = [
    "AddAcademyAssessmentForm",
    "PERSON_MODULE",
    "SyncAcademyLessonsForm",
    "TeacherAcademyMutationResult",
    "UpdateAcademyAssignmentForm",
    "UpdateAcademyStatusForm",
    "add_assessment_response",
    "can_user_manage_academy_assignment",
    "can_user_manage_academy_teacher",
    "current_auth_login",
    "current_auth_role",
    "current_staff_id",
    "delete_assessment_response",
    "filter_rows_by_subject_scope",
    "head_of_department_workspace_cards",
    "hod_subject_ids_for_context",
    "list_academy_timetable_events",
    "list_announcements",
    "list_teacher_academy_page_context",
    "register_head_of_department_recruitment_routes",
    "sync_lessons_response",
    "update_assignment_response",
    "update_status_response",
]
