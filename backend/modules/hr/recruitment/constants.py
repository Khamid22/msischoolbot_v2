"""Stable recruitment enums shared by schemas, policy, and services."""

PRIMARY_STAGES = (
    "new_candidate",
    "responded",
    "job_interview",
    "test_and_demo",
    "under_review",
    "teacher_academy",
    "active_teacher",
)
ALTERNATIVE_STAGES = ("rejected", "candidate_withdrew", "trash_bin")
ALL_STAGES = frozenset((*PRIMARY_STAGES, *ALTERNATIVE_STAGES))
PROTECTED_HIRE_STAGES = frozenset({"teacher_academy", "active_teacher"})

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
CANDIDATE_SOURCES = (
    "hh.uz",
    "Telegram",
    "Referral",
    "Instagram",
    "LinkedIn",
    "University",
    "MSI website",
    "Other",
)

REJECTION_REASONS = (
    "insufficient_subject_knowledge",
    "insufficient_english_level",
    "weak_demo_lesson",
    "schedule_incompatibility",
    "salary_expectation_incompatibility",
    "insufficient_experience",
    "unprofessional_behaviour",
    "missing_or_invalid_documents",
    "candidate_did_not_attend",
    "position_already_filled",
    "other",
)

INTERVIEW_RESULTS = frozenset(
    {"passed", "failed", "additional_interview", "candidate_withdrew"}
)
SUBJECT_TEST_RESULTS = frozenset({"passed", "failed", "retake_required", "not_completed"})
DEMO_RESULTS = frozenset({"passed", "failed", "additional_demo"})
TASK_STATUSES = frozenset({"pending", "completed", "cancelled"})
APPOINTMENT_TYPES = frozenset({"job_interview", "demo_lesson"})
APPOINTMENT_STATUSES = frozenset({"scheduled", "completed", "cancelled", "no_show"})
SCHEDULED_STAGE_TYPES = {"job_interview": "job_interview", "test_and_demo": "demo_lesson"}

RECRUITMENT_ROLES = frozenset(
    {"hr_manager", "academic_director", "head_of_department", "ceo"}
)
FULL_VIEW_ROLES = frozenset({"hr_manager", "ceo"})
ACADEMIC_ROLES = frozenset({"academic_director", "head_of_department"})


__all__ = [
    "ACADEMIC_ROLES",
    "APPOINTMENT_STATUSES",
    "APPOINTMENT_TYPES",
    "ALL_STAGES",
    "ALTERNATIVE_STAGES",
    "CANDIDATE_SOURCES",
    "DEMO_RESULTS",
    "DOCUMENT_TYPES",
    "FULL_VIEW_ROLES",
    "INTERVIEW_RESULTS",
    "PRIMARY_STAGES",
    "PROTECTED_HIRE_STAGES",
    "REQUIRED_DOCUMENT_TYPES",
    "RECRUITMENT_ROLES",
    "REJECTION_REASONS",
    "SCHEDULED_STAGE_TYPES",
    "SLA_STAGES",
    "OPTIONAL_DOCUMENT_TYPES",
    "SUBJECT_TEST_RESULTS",
    "TASK_STATUSES",
]
