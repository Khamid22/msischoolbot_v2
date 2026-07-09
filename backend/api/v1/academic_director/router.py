"""Academic Director JSON/action API v1 routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException

from backend.api import ApiSuccess, api_success
from backend.api.v1.academic_director.schemas import (
    CreateHeadOfDepartmentForm,
    HeadOfDepartmentCreated,
)
from backend.api.v1.academic_director.academic import router as academic_router
from backend.api.v1.academic_director.teacher_academy import register_teacher_academy_routes
from backend.roles.academic_director.staff_registration import create_head_of_department_account
from backend.domains.admin.page_cache import invalidate_admin_page_context_cache
from backend.security import CurrentUser, get_current_user, require_role

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
    invalidate_admin_page_context_cache()
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


register_teacher_academy_routes(router)
router.include_router(academic_router)


__all__ = ["router"]
