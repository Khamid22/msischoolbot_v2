"""Academic Director JSON/action API v1 routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException

from backend.api import ApiSuccess, api_success
from backend.api.v1.academic_director.schemas import (
    CreateHeadOfDepartmentForm,
    HeadOfDepartmentCreated,
)
from backend.api.v1.teacher_academy_actions import (
    AddAcademyAssessmentForm,
    CreateAcademyTeacherForm,
    PromoteAcademyTeacherForm,
    TeacherAcademyMutationResult,
    UpdateAcademyAssignmentForm,
    UpdateAcademyStatusForm,
    add_assessment_response,
    create_academy_teacher_response,
    delete_assessment_response,
    delete_academy_teacher_response,
    promote_response,
    update_assignment_response,
    update_status_response,
)
from backend.roles.academic_director.staff_registration import create_head_of_department_account
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
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


@router.post(
    "/teacher-academy",
    operation_id="api_v1_academic_director_create_academy_teacher",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def create_academy_teacher(
    payload: Annotated[CreateAcademyTeacherForm, Form()],
    user: CurrentUser = Depends(get_current_user),
):
    return create_academy_teacher_response(
        payload,
        created_by_label="Academic Director",
        created_by_login=user.login,
    )


@router.post(
    "/teacher-academy/assignments/{assignment_id}",
    operation_id="api_v1_academic_director_update_academy_assignment",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def update_academy_assignment(
    assignment_id: int,
    payload: Annotated[UpdateAcademyAssignmentForm, Form()],
):
    return update_assignment_response(assignment_id, payload)


@router.post(
    "/teacher-academy/{academy_teacher_id}/assessments",
    operation_id="api_v1_academic_director_add_academy_assessment",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def add_academy_assessment(
    academy_teacher_id: int,
    payload: Annotated[AddAcademyAssessmentForm, Form()],
    user: CurrentUser = Depends(get_current_user),
):
    return add_assessment_response(
        academy_teacher_id,
        payload,
        created_by_label="Academic Director",
        created_by_login=user.login,
    )


@router.post(
    "/teacher-academy/{academy_teacher_id}/assessments/{assessment_id}/delete",
    operation_id="api_v1_academic_director_delete_academy_assessment",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def delete_academy_assessment(academy_teacher_id: int, assessment_id: int):
    return delete_assessment_response(academy_teacher_id, assessment_id)


@router.post(
    "/teacher-academy/{academy_teacher_id}/status",
    operation_id="api_v1_academic_director_update_academy_status",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def update_academy_status(
    academy_teacher_id: int,
    payload: Annotated[UpdateAcademyStatusForm, Form()],
):
    return update_status_response(academy_teacher_id, payload)


@router.post(
    "/teacher-academy/{academy_teacher_id}/delete",
    operation_id="api_v1_academic_director_delete_academy_teacher",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def delete_academy_teacher(academy_teacher_id: int):
    return delete_academy_teacher_response(academy_teacher_id)


@router.post(
    "/teacher-academy/{academy_teacher_id}/promote",
    operation_id="api_v1_academic_director_promote_academy_teacher",
    response_model=ApiSuccess[TeacherAcademyMutationResult],
)
def promote_academy_teacher(
    academy_teacher_id: int,
    payload: Annotated[PromoteAcademyTeacherForm, Form()],
):
    return promote_response(academy_teacher_id, payload)


__all__ = ["router"]
