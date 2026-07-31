"""Public Teacher orchestration interface used by the Teacher workspace."""

from backend.modules.domains.academics.contracts import (
    CurriculumDetail,
    CurriculumNotFoundError,
    CurriculumPermissionError,
    CurriculumValidationError,
    CurriculumVariant,
    CurriculumViewAcknowledgement,
    SubjectCurriculumCatalog,
    acknowledge_teacher_curriculum_view,
    curriculum_asset_url_for_teacher,
    get_teacher_subject_curriculum,
    list_teacher_subject_curricula,
)
from backend.modules.domains.identity.contracts import (
    current_auth_login,
    current_teacher_id,
    current_teacher_staff_id,
)
from backend.modules.domains.teacher_academy.contracts import (
    get_academy_teacher_for_teacher_account,
)
from backend.modules.domains.teacher_records.contracts import (
    get_active_teacher_workspace_profile,
)
from backend.modules.people.teacher.module import PERSON_MODULE

__all__ = [
    "PERSON_MODULE",
    "CurriculumDetail",
    "CurriculumNotFoundError",
    "CurriculumPermissionError",
    "CurriculumValidationError",
    "CurriculumVariant",
    "CurriculumViewAcknowledgement",
    "SubjectCurriculumCatalog",
    "acknowledge_teacher_curriculum_view",
    "curriculum_asset_url_for_teacher",
    "current_auth_login",
    "current_teacher_id",
    "current_teacher_staff_id",
    "get_academy_teacher_for_teacher_account",
    "get_active_teacher_workspace_profile",
    "get_teacher_subject_curriculum",
    "list_teacher_subject_curricula",
]
