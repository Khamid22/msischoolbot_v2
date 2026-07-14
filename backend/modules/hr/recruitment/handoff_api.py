"""Narrow onboarding handoff APIs shared with retained teacher-management tabs."""

from fastapi import APIRouter, Depends, HTTPException

from backend.core.access import CurrentUser, require_role
from backend.core.api import api_success
from backend.modules.hr.recruitment.schemas import AcademyIntakeOnboarding
from backend.modules.people.teachers.service import provision_recruitment_teacher_account
from backend.modules.teacher_academy.service import onboard_recruitment_academy_teacher


router = APIRouter(prefix="/recruitment", tags=["teacher-onboarding-handoff"])


@router.post(
    "/academy-intakes/{academy_teacher_id}/onboard",
    operation_id="api_v1_recruitment_onboard_academy_intake",
)
def onboard_academy_intake(
    academy_teacher_id: int,
    payload: AcademyIntakeOnboarding,
    user: CurrentUser = Depends(require_role("admin", "system_admin", "academic_director")),
):
    created, message, credentials = onboard_recruitment_academy_teacher(
        academy_teacher_id=academy_teacher_id,
        subject_program_id=payload.subject_program_id,
        selected_curriculum_item_ids=payload.curriculum_item_ids,
        actor_account_id=user.account_id,
        actor_login=user.login,
    )
    if not created:
        raise HTTPException(
            status_code=400,
            detail=message or "Unable to onboard this Academy teacher.",
        )
    return api_success({"message": message, "credentials": credentials})


@router.post(
    "/active-teacher-intakes/{teacher_id}/provision-account",
    operation_id="api_v1_recruitment_provision_active_teacher",
)
def provision_active_teacher_intake(
    teacher_id: int,
    user: CurrentUser = Depends(require_role("admin", "system_admin")),
):
    created, message, credentials = provision_recruitment_teacher_account(
        teacher_id,
        actor_account_id=user.account_id,
        actor_login=user.login,
    )
    if not created:
        raise HTTPException(
            status_code=400,
            detail=message or "Unable to provision this teacher account.",
        )
    return api_success({"message": message, "credentials": credentials})


__all__ = ["router"]
