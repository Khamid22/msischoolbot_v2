"""Public Teacher orchestration interface used by the Teacher workspace."""

from backend.modules.domains.identity.contracts import (
    current_auth_login,
    current_teacher_id,
    current_teacher_staff_id,
)
from backend.modules.domains.teacher_academy.contracts import (
    get_academy_teacher_for_teacher_account,
)
from backend.modules.people.teacher.module import PERSON_MODULE

__all__ = [
    "PERSON_MODULE",
    "current_auth_login",
    "current_teacher_id",
    "current_teacher_staff_id",
    "get_academy_teacher_for_teacher_account",
]
