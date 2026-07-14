"""Head of Department Teacher Academy API v1 route registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException

from backend.core.api import ApiSuccess
from backend.modules.teacher_academy.responses import (
    add_assessment_response,
    delete_assessment_response,
    sync_lessons_response,
    update_assignment_response,
    update_status_response,
)
from backend.modules.teacher_academy.schemas import (
    AddAcademyAssessmentForm,
    SyncAcademyLessonsForm,
    TeacherAcademyMutationResult,
    UpdateAcademyAssignmentForm,
    UpdateAcademyStatusForm,
)
from backend.modules.teacher_academy.policies import (
    can_user_manage_academy_assignment,
    can_user_manage_academy_teacher,
)
from backend.core.access import CurrentUser, get_current_user


def register_teacher_academy_routes(router: APIRouter) -> None:
    @router.post(
        "/teacher-academy/assignments/{assignment_id}",
        operation_id="api_v1_head_of_department_update_academy_assignment",
        response_model=ApiSuccess[TeacherAcademyMutationResult],
    )
    def update_academy_assignment(
        assignment_id: int,
        payload: Annotated[UpdateAcademyAssignmentForm, Form()],
        user: CurrentUser = Depends(get_current_user),
    ):
        if not can_user_manage_academy_assignment(user, assignment_id):
            raise HTTPException(status_code=403, detail="This Teacher Academy lesson is outside your subject scope.")
        return update_assignment_response(assignment_id, payload, scope_user=user)

    @router.post(
        "/teacher-academy/{academy_teacher_id}/lessons",
        operation_id="api_v1_head_of_department_sync_academy_lessons",
        response_model=ApiSuccess[TeacherAcademyMutationResult],
    )
    def sync_academy_lessons(
        academy_teacher_id: int,
        payload: Annotated[SyncAcademyLessonsForm, Form()],
        user: CurrentUser = Depends(get_current_user),
    ):
        if not can_user_manage_academy_teacher(user, academy_teacher_id):
            raise HTTPException(status_code=403, detail="This Teacher Academy teacher is outside your subject scope.")
        return sync_lessons_response(
            academy_teacher_id,
            payload,
            created_by_label="Head of Department",
            created_by_login=user.login,
            scope_user=user,
        )

    @router.post(
        "/teacher-academy/{academy_teacher_id}/assessments",
        operation_id="api_v1_head_of_department_add_academy_assessment",
        response_model=ApiSuccess[TeacherAcademyMutationResult],
    )
    def add_academy_assessment(
        academy_teacher_id: int,
        payload: Annotated[AddAcademyAssessmentForm, Form()],
        user: CurrentUser = Depends(get_current_user),
    ):
        if not can_user_manage_academy_teacher(user, academy_teacher_id):
            raise HTTPException(status_code=403, detail="This Teacher Academy teacher is outside your subject scope.")
        return add_assessment_response(
            academy_teacher_id,
            payload,
            created_by_label="Head of Department",
            created_by_login=user.login,
            scope_user=user,
        )

    @router.post(
        "/teacher-academy/{academy_teacher_id}/assessments/{assessment_id}/delete",
        operation_id="api_v1_head_of_department_delete_academy_assessment",
        response_model=ApiSuccess[TeacherAcademyMutationResult],
    )
    def delete_academy_assessment(
        academy_teacher_id: int,
        assessment_id: int,
        user: CurrentUser = Depends(get_current_user),
    ):
        if not can_user_manage_academy_teacher(user, academy_teacher_id):
            raise HTTPException(status_code=403, detail="This Teacher Academy teacher is outside your subject scope.")
        return delete_assessment_response(academy_teacher_id, assessment_id, scope_user=user)

    @router.post(
        "/teacher-academy/{academy_teacher_id}/status",
        operation_id="api_v1_head_of_department_update_academy_status",
        response_model=ApiSuccess[TeacherAcademyMutationResult],
    )
    def update_academy_status(
        academy_teacher_id: int,
        payload: Annotated[UpdateAcademyStatusForm, Form()],
        user: CurrentUser = Depends(get_current_user),
    ):
        if not can_user_manage_academy_teacher(user, academy_teacher_id):
            raise HTTPException(status_code=403, detail="This Teacher Academy teacher is outside your subject scope.")
        return update_status_response(academy_teacher_id, payload, scope_user=user)


__all__ = ["register_teacher_academy_routes"]
