"""Academic Director JSON/action API v1 routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException

from backend.core.api import ApiSuccess, api_success
from backend.modules.people.academic_director.contracts import (
    CreateHeadOfDepartmentForm,
    HeadOfDepartmentCreated,
    HeadOfDepartmentPasswordReset,
    create_head_of_department_account,
    reset_head_of_department_password,
)
from backend.modules.people.academic_director.workspace.academics_api import router as academic_router
from backend.modules.people.academic_director.workspace.staff_records_api import register_teacher_academy_routes
from backend.core.access import CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/academic-director", dependencies=[Depends(require_role("academic_director"))])


@router.post(
    "/head-of-departments",
    operation_id="api_v1_academic_director_create_hod",
    response_model=ApiSuccess[HeadOfDepartmentCreated],
)
def create_hod(
    payload: Annotated[CreateHeadOfDepartmentForm, Form()],
    user: CurrentUser = Depends(get_current_user),
):
    created, error_message, credentials = create_head_of_department_account(
        display_name=payload.hod_display_name,
        subject_id=payload.hod_subject_id,
        created_by=user.login or "Academic Director",
    )
    if not created:
        raise HTTPException(status_code=400, detail=error_message or "Unable to create Head of Department.")
    return api_success(
        {
            "message": "Head of Department account created.",
            "credentials": {
                "role": "head_of_department",
                "login": credentials.get("login", ""),
                "temporary_password": credentials.get("temporary_password", ""),
                "display_name": credentials.get("display_name", ""),
                "subject_name": credentials.get("subject_name", ""),
            },
            "headOfDepartment": {
                "login": credentials.get("login", ""),
                "display_name": credentials.get("display_name", ""),
                "role": "head_of_department",
                "status": "active",
                "subject_name": credentials.get("subject_name", ""),
            },
        }
    )


@router.post(
    "/head-of-departments/{account_id}/reset-password",
    operation_id="api_v1_academic_director_reset_hod_password",
    response_model=ApiSuccess[HeadOfDepartmentPasswordReset],
)
def reset_hod_password(
    account_id: int,
    user: CurrentUser = Depends(get_current_user),
):
    reset, error_message, credentials = reset_head_of_department_password(
        account_id,
        actor_account_id=user.account_id,
        actor_login=user.login,
    )
    if not reset:
        status_code = 404 if "not found" in (error_message or "").casefold() else 400
        raise HTTPException(status_code=status_code, detail=error_message or "Unable to reset password.")
    return api_success(
        {
            "message": "Temporary password generated.",
            "login": credentials.get("login", ""),
            "temporary_password": credentials.get("temporary_password", ""),
            "display_name": credentials.get("display_name", ""),
            "must_change_password": True,
            "updated_at": credentials.get("updated_at", ""),
        }
    )


register_teacher_academy_routes(router)
router.include_router(academic_router)


__all__ = ["router"]
