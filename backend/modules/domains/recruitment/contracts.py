"""Typed transaction-aware contracts exposed to other product modules."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.unit_of_work import Connection
from backend.modules.domains.recruitment import repository
from backend.modules.domains.recruitment.domain_types import RecruitmentEventType


@dataclass(frozen=True)
class CreateAcademyLifecycleProfileCommand:
    academy_teacher_id: int
    full_name: str
    subject_id: int
    applied_position: str
    phone: str
    email: str
    telegram_username: str
    linked_account_id: int | None
    created_by: str
    occurred_at: str


@dataclass(frozen=True)
class AcademyLifecycleProfileResult:
    candidate_id: int
    is_linked: bool


def create_academy_lifecycle_profile(
    conn: Connection,
    command: CreateAcademyLifecycleProfileCommand,
) -> AcademyLifecycleProfileResult:
    """Create and link the Recruitment lifecycle profile in the caller's transaction."""

    candidate_id = repository.insert_academy_direct_profile(
        conn,
        full_name=command.full_name,
        subject_id=command.subject_id,
        applied_position=command.applied_position,
        phone=command.phone,
        email=command.email,
        telegram_username=command.telegram_username,
        linked_account_id=command.linked_account_id,
        now=command.occurred_at,
        actor_account_id=None,
        transition_source="manual",
        history_comment="Lifecycle profile created with a Teacher Academy teacher.",
    )
    if not candidate_id:
        return AcademyLifecycleProfileResult(candidate_id=0, is_linked=False)

    is_linked = repository.link_academy_profile(
        conn,
        academy_teacher_id=command.academy_teacher_id,
        candidate_id=candidate_id,
        full_name=command.full_name,
        linked_account_id=command.linked_account_id,
        now=command.occurred_at,
    )
    if is_linked:
        repository.insert_audit(
            conn,
            candidate_id=candidate_id,
            event_type=RecruitmentEventType.ACADEMY_PROFILE_CREATED.value,
            detail={
                "academy_teacher_id": command.academy_teacher_id,
                "profile_origin": "academy_direct",
                "created_by": command.created_by,
            },
            actor_account_id=None,
            actor_staff_id=None,
            now=command.occurred_at,
        )
    return AcademyLifecycleProfileResult(
        candidate_id=candidate_id,
        is_linked=bool(is_linked),
    )


__all__ = [
    "AcademyLifecycleProfileResult",
    "CreateAcademyLifecycleProfileCommand",
    "create_academy_lifecycle_profile",
]
