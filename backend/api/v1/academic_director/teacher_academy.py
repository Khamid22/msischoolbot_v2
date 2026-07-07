"""Academic Director Teacher Academy API v1 route registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form

from backend.api import ApiSuccess
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
from backend.security import CurrentUser, get_current_user


def register_teacher_academy_routes(router: APIRouter) -> None:
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


__all__ = ["register_teacher_academy_routes"]
