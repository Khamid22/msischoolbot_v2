"""Teacher Academy API v1 response adapters."""

from __future__ import annotations

from typing import Any, Mapping

from fastapi import HTTPException

from backend.core.api import api_success
from backend.modules.domains.teacher_academy.schemas import (
    AddAcademyAssessmentForm,
    CreateAcademyTeacherForm,
    PromoteAcademyTeacherForm,
    SyncAcademyLessonsForm,
    UpdateAcademyAssignmentForm,
    UpdateAcademyStatusForm,
    form_list,
)
from backend.modules.domains.teacher_academy.policies import filter_academy_teachers_for_user
from backend.modules.domains.teacher_academy.service import (
    add_assessment,
    create_academy_teacher,
    delete_academy_teacher,
    delete_assessment,
    promote_academy_teacher,
    sync_academy_lessons,
    update_academy_status,
    update_assignment,
)
from backend.modules.domains.teacher_academy.read_service import list_academy_teachers
from backend.modules.domains.teacher_records.service import list_teachers
from backend.core.access import CurrentUser


def academy_error(message: str, status: int = 400) -> None:
    raise HTTPException(status_code=status, detail=message)


def safe_credentials(credentials: dict | None) -> dict[str, str]:
    credentials = credentials or {}
    return {
        "role": "teacher",
        "login": credentials.get("login", ""),
        "teacher_code": credentials.get("teacher_code", ""),
        "temporary_password": credentials.get("temporary_password", ""),
        "display_name": credentials.get("display_name", ""),
        "subject_name": credentials.get("subject_name", ""),
    }


def academy_payload(
    message: str,
    *,
    credentials: dict | None = None,
    scope_user: CurrentUser | None = None,
):
    academy_rows = list_academy_teachers()
    if scope_user is not None:
        academy_rows = filter_academy_teachers_for_user(academy_rows, scope_user)
    payload: dict[str, Any] = {
        "message": message,
        "academy": academy_rows,
        "teachers": list_teachers(),
    }
    if credentials:
        payload["credentials"] = safe_credentials(credentials)
    return api_success(payload)


def _assessment_form_from_mapping(form_data: Mapping[str, Any] | None = None) -> AddAcademyAssessmentForm:
    return AddAcademyAssessmentForm.model_validate(dict(form_data or {}))


def assessment_sections_from_form(form_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _assessment_form_from_mapping(form_data).section_feedback()


def assessment_scores_from_form(form_data: Mapping[str, Any] | None = None) -> dict[str, str]:
    return _assessment_form_from_mapping(form_data).scores()


def create_academy_teacher_response(
    payload: CreateAcademyTeacherForm,
    *,
    created_by_label: str = "Academic Director",
    created_by_login: str = "",
    scope_user: CurrentUser | None = None,
):
    create_result = create_academy_teacher(
        full_name=payload.academy_full_name,
        subject_program_id=payload.academy_subject_program_id,
        selected_curriculum_item_ids=payload.academy_curriculum_item_ids,
        position=payload.academy_position,
        employment_type=payload.academy_employment_type,
        telegram_username=payload.academy_telegram_username,
        phone=payload.academy_phone,
        email=payload.academy_email,
        academy_start_date=payload.academy_start_date,
        mentor_id=payload.academy_mentor_id,
        department_head_id=payload.academy_department_head_id,
        notes=payload.academy_notes,
        created_by=created_by_login or created_by_label,
        return_credentials=True,
    )
    if isinstance(create_result, tuple) and len(create_result) == 3:
        created, error_message, credentials = create_result
    else:
        created, error_message = create_result
        credentials = {}
    if not created:
        academy_error(error_message or "Unable to create academy teacher.")
    return academy_payload(
        "Academy teacher created with selected Teacher Academy lessons.",
        credentials=credentials,
        scope_user=scope_user,
    )


def update_assignment_response(
    assignment_id: int,
    payload: UpdateAcademyAssignmentForm,
    *,
    scope_user: CurrentUser | None = None,
):
    updated, error_message = update_assignment(
        assignment_id=assignment_id,
        assignment_type=payload.assignment_type,
        deadline_date=payload.deadline_date,
        session_datetime=payload.session_datetime,
        evaluator_id=payload.evaluator_id,
        focus_areas=payload.focus_areas,
        notes_to_trainee=payload.notes_to_trainee,
        status=payload.assignment_status,
    )
    if not updated:
        academy_error(error_message or "Unable to update assignment.")
    return academy_payload("Academy lesson updated.", scope_user=scope_user)


def sync_lessons_response(
    academy_teacher_id: int,
    payload: SyncAcademyLessonsForm,
    *,
    created_by_label: str = "Academic Director",
    created_by_login: str = "",
    scope_user: CurrentUser | None = None,
):
    synced, error_message = sync_academy_lessons(
        academy_teacher_id=academy_teacher_id,
        selected_curriculum_item_ids=payload.academy_curriculum_item_ids,
        created_by=created_by_login or created_by_label,
    )
    if not synced:
        academy_error(error_message or "Unable to update academy lessons.")
    return academy_payload("Academy lessons updated.", scope_user=scope_user)


def add_assessment_response(
    academy_teacher_id: int,
    payload: AddAcademyAssessmentForm,
    *,
    created_by_label: str = "Academic Director",
    created_by_login: str = "",
    scope_user: CurrentUser | None = None,
):
    saved, error_message = add_assessment(
        academy_teacher_id=academy_teacher_id,
        lesson_assignment_id=payload.lesson_assignment_id,
        assessment_type=payload.assessment_type,
        evaluator_id=payload.evaluator_id,
        assessment_datetime=payload.assessment_datetime,
        session_type=payload.session_type,
        class_label=payload.class_label,
        section_feedback=payload.section_feedback(),
        scores=payload.scores(),
        strengths=payload.strengths,
        areas_for_improvement=payload.areas_for_improvement,
        final_recommendation=payload.final_recommendation,
        decision=payload.decision,
        created_by=created_by_login or created_by_label,
    )
    if not saved:
        academy_error(error_message or "Unable to save assessment.")
    return academy_payload("Assessment saved.", scope_user=scope_user)


def delete_assessment_response(
    academy_teacher_id: int,
    assessment_id: int,
    *,
    scope_user: CurrentUser | None = None,
):
    deleted, error_message = delete_assessment(
        academy_teacher_id=academy_teacher_id,
        assessment_id=assessment_id,
    )
    if not deleted:
        academy_error(error_message or "Unable to delete assessment report.")
    return academy_payload("Assessment report deleted.", scope_user=scope_user)


def update_status_response(
    academy_teacher_id: int,
    payload: UpdateAcademyStatusForm,
    *,
    scope_user: CurrentUser | None = None,
):
    updated, error_message = update_academy_status(
        academy_teacher_id=academy_teacher_id,
        status=payload.academy_status,
    )
    if not updated:
        academy_error(error_message or "Unable to update academy status.")
    return academy_payload("Academy status updated.", scope_user=scope_user)


def delete_academy_teacher_response(
    academy_teacher_id: int,
    *,
    scope_user: CurrentUser | None = None,
):
    deleted, error_message = delete_academy_teacher(academy_teacher_id=academy_teacher_id)
    if not deleted:
        academy_error(error_message or "Unable to delete academy teacher.")
    return academy_payload("Academy teacher deleted.", scope_user=scope_user)


def promote_response(
    academy_teacher_id: int,
    payload: PromoteAcademyTeacherForm,
    *,
    scope_user: CurrentUser | None = None,
):
    promoted, error_message = promote_academy_teacher(
        academy_teacher_id=academy_teacher_id,
        assigned_group=payload.teacher_assigned_group,
        pay_rate=payload.teacher_pay_rate,
        category=payload.teacher_category,
        semester_stage=payload.teacher_semester_stage,
        promotion_notes=payload.teacher_promotion_notes,
    )
    if not promoted:
        academy_error(error_message or "Unable to promote academy teacher.")
    return academy_payload("Academy teacher promoted to Active Teachers.", scope_user=scope_user)


__all__ = [
    "academy_error",
    "academy_payload",
    "add_assessment_response",
    "assessment_scores_from_form",
    "assessment_sections_from_form",
    "create_academy_teacher_response",
    "delete_academy_teacher_response",
    "delete_assessment_response",
    "form_list",
    "promote_response",
    "safe_credentials",
    "sync_lessons_response",
    "update_assignment_response",
    "update_status_response",
]
