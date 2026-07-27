"""Stable recruitment enums shared by schemas, policy, and services."""

from backend.core.access.domain_types import Role
from backend.modules.domains.recruitment.catalog import (
    DEMO_CRITERIA,
    PIPELINE_STAGE_COLOR_TOKENS,
)
from backend.modules.domains.recruitment.domain_types import (
    AppointmentStatus,
    AppointmentType,
    CandidateStage,
    TaskStatus,
)


PRIMARY_STAGES = (
    CandidateStage.NEW_CANDIDATE.value,
    CandidateStage.RESPONDED.value,
    CandidateStage.JOB_INTERVIEW.value,
    CandidateStage.TEST_AND_DEMO.value,
    CandidateStage.UNDER_REVIEW.value,
    CandidateStage.TEACHER_ACADEMY.value,
    CandidateStage.ACTIVE_TEACHER.value,
)
ALTERNATIVE_STAGES = (
    CandidateStage.REJECTED.value,
    CandidateStage.CANDIDATE_WITHDREW.value,
    CandidateStage.TRASH_BIN.value,
)
ALL_STAGES = frozenset((*PRIMARY_STAGES, *ALTERNATIVE_STAGES))
PROTECTED_HIRE_STAGES = frozenset(
    {
        CandidateStage.TEACHER_ACADEMY.value,
        CandidateStage.ACTIVE_TEACHER.value,
    }
)

DOCUMENT_TYPES = (
    "cv",
    "a_level",
    "igcse",
    "id_passport",
    "ielts",
    "sat",
    "diploma",
    "certificate",
    "recommendation",
    "other",
)
REQUIRED_DOCUMENT_TYPES = frozenset({"cv", "id_passport", "diploma"})
OPTIONAL_DOCUMENT_TYPES = frozenset(set(DOCUMENT_TYPES) - REQUIRED_DOCUMENT_TYPES)
SLA_STAGES = (
    "new_candidate",
    "responded",
    "job_interview",
    "test_and_demo",
    "under_review",
)
RECRUITMENT_OPTION_CATEGORIES = frozenset(
    {
        "source",
        "subsource",
        "rejection_reason",
        "withdrawal_reason",
        "position",
        "english_level",
        "schedule",
        "availability",
        "expected_salary",
        "teaching_experience",
    }
)

REJECTION_REASONS = (
    "low_english_level",
    "low_subject_knowledge",
    "poor_soft_skills",
    "weak_demo_lesson",
    "schedule_incompatibility",
    "salary_expectation_incompatibility",
    "unprofessional_behaviour",
    "missing_or_invalid_documents",
    "candidate_did_not_attend",
    "position_already_filled",
)

WITHDRAWAL_REASONS = (
    "candidate_no_longer_interested",
    "received_counter_offer",
    "personal_reasons",
    "schedule_incompatibility",
    "salary_expectation_incompatibility",
    "relocation_or_location",
    "unresponsive",
    "other",
)

INTERVIEW_RESULTS = frozenset(
    {"passed", "failed", "additional_interview", "candidate_withdrew"}
)
SUBJECT_TEST_RESULTS = frozenset({"passed", "failed", "retake_required", "not_completed"})
DEMO_RESULTS = frozenset({"passed", "failed", "additional_demo"})
TASK_STATUSES = frozenset(status.value for status in TaskStatus)
APPOINTMENT_TYPES = frozenset(
    appointment_type.value for appointment_type in AppointmentType
)
APPOINTMENT_STATUSES = frozenset(status.value for status in AppointmentStatus)
APPOINTMENT_DISPLAY_STATUSES = frozenset(
    {"passed", "failed", "scheduled", "in_progress", "overdue", "not_conducted"}
)
SCHEDULED_STAGE_TYPES = {
    CandidateStage.JOB_INTERVIEW.value: AppointmentType.JOB_INTERVIEW.value,
    CandidateStage.TEST_AND_DEMO.value: AppointmentType.DEMO_LESSON.value,
}

RECRUITMENT_ROLES = frozenset(
    {
        Role.HR_MANAGER.value,
        Role.ACADEMIC_DIRECTOR.value,
        Role.HEAD_OF_DEPARTMENT.value,
        Role.CEO.value,
    }
)
DEMO_EVALUATOR_ROLES = frozenset(
    {
        Role.HR_MANAGER.value,
        Role.ACADEMIC_DIRECTOR.value,
        Role.HEAD_OF_DEPARTMENT.value,
    }
)
FULL_VIEW_ROLES = frozenset({Role.HR_MANAGER.value, Role.CEO.value})
ACADEMIC_ROLES = frozenset(
    {Role.ACADEMIC_DIRECTOR.value, Role.HEAD_OF_DEPARTMENT.value}
)


__all__ = [
    "ACADEMIC_ROLES",
    "APPOINTMENT_STATUSES",
    "APPOINTMENT_DISPLAY_STATUSES",
    "APPOINTMENT_TYPES",
    "ALL_STAGES",
    "ALTERNATIVE_STAGES",
    "DEMO_CRITERIA",
    "DEMO_RESULTS",
    "DOCUMENT_TYPES",
    "DEMO_EVALUATOR_ROLES",
    "FULL_VIEW_ROLES",
    "INTERVIEW_RESULTS",
    "PRIMARY_STAGES",
    "PROTECTED_HIRE_STAGES",
    "REQUIRED_DOCUMENT_TYPES",
    "RECRUITMENT_ROLES",
    "RECRUITMENT_OPTION_CATEGORIES",
    "REJECTION_REASONS",
    "SCHEDULED_STAGE_TYPES",
    "SLA_STAGES",
    "OPTIONAL_DOCUMENT_TYPES",
    "PIPELINE_STAGE_COLOR_TOKENS",
    "SUBJECT_TEST_RESULTS",
    "TASK_STATUSES",
    "WITHDRAWAL_REASONS",
]
