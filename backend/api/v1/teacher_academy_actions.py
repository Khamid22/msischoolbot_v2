"""Shared service adapters and schemas for Teacher Academy API v1 routes."""

from __future__ import annotations

from typing import Annotated, Any, Mapping

from fastapi import HTTPException
from pydantic import BaseModel, BeforeValidator, Field

from backend.api import api_success
from backend.domains.teacher_academy.service import (
    add_assessment,
    create_academy_teacher,
    delete_assessment,
    delete_academy_teacher,
    list_academy_teachers,
    promote_academy_teacher,
    update_academy_status,
    update_assignment,
)
from backend.domains.teachers.service import list_teachers
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache


ACADEMY_SECTIONS = (
    "starter",
    "warmup",
    "teaching_session_1",
    "teaching_session_2",
    "teaching_session_3",
    "end_activity",
    "homework",
)

ACADEMY_CRITERIA_REMARKS = (
    ("tgc", "teacher_guidance_compliance_score", "teacher_guidance_compliance_remarks"),
    ("ta", "timing_adherence_score", "timing_adherence_remarks"),
    ("rf", "resource_familiarity_score", "resource_familiarity_remarks"),
    ("ef", "english_fluency_score", "english_fluency_remarks"),
    ("con", "confidence_delivery_score", "confidence_delivery_remarks"),
    ("se", "engagement_technique_score", "engagement_technique_remarks"),
)


def _split_form_items(value: Any) -> list[str]:
    if value is None:
        return []
    raw_items = value if isinstance(value, (list, tuple, set)) else [value]
    items: list[str] = []
    for raw_item in raw_items:
        items.extend(
            item.strip()
            for item in str(raw_item or "").split(",")
            if item.strip()
        )
    return items


FormStringList = Annotated[list[str], BeforeValidator(_split_form_items)]


class CreateAcademyTeacherForm(BaseModel):
    academy_full_name: str = ""
    academy_subject_program_id: str = ""
    academy_curriculum_item_ids: FormStringList = Field(default_factory=list)
    academy_position: str = "Trainee Teacher"
    academy_employment_type: str = "academy"
    academy_telegram_username: str = ""
    academy_phone: str = ""
    academy_email: str = ""
    academy_start_date: str = ""
    academy_mentor_id: str = "0"
    academy_department_head_id: str = "0"
    academy_notes: str = ""


class UpdateAcademyAssignmentForm(BaseModel):
    assignment_type: str = ""
    deadline_date: str = ""
    session_datetime: str = ""
    evaluator_id: str = "0"
    focus_areas: FormStringList = Field(default_factory=list)
    notes_to_trainee: str = ""
    assignment_status: str = "assigned"


class AddAcademyAssessmentForm(BaseModel):
    lesson_assignment_id: str = ""
    assessment_type: str = "academy_practice_lesson"
    evaluator_id: str = "0"
    assessment_datetime: str = ""
    session_type: str = "training_simulation"
    class_label: str = ""
    starter_status: str = "not_applicable"
    starter_time_used: str = ""
    starter_remarks: str = ""
    warmup_status: str = "not_applicable"
    warmup_time_used: str = ""
    warmup_remarks: str = ""
    teaching_session_1_status: str = "not_applicable"
    teaching_session_1_time_used: str = ""
    teaching_session_1_remarks: str = ""
    teaching_session_2_status: str = "not_applicable"
    teaching_session_2_time_used: str = ""
    teaching_session_2_remarks: str = ""
    teaching_session_3_status: str = "not_applicable"
    teaching_session_3_time_used: str = ""
    teaching_session_3_remarks: str = ""
    end_activity_status: str = "not_applicable"
    end_activity_time_used: str = ""
    end_activity_remarks: str = ""
    homework_status: str = "not_applicable"
    homework_time_used: str = ""
    homework_remarks: str = ""
    teacher_guidance_compliance_score: str = ""
    teacher_guidance_compliance_remarks: str = ""
    timing_adherence_score: str = ""
    timing_adherence_remarks: str = ""
    resource_familiarity_score: str = ""
    resource_familiarity_remarks: str = ""
    english_fluency_score: str = ""
    english_fluency_remarks: str = ""
    confidence_delivery_score: str = ""
    confidence_delivery_remarks: str = ""
    engagement_technique_score: str = ""
    engagement_technique_remarks: str = ""
    strengths: str = ""
    areas_for_improvement: str = ""
    final_recommendation: str = ""
    decision: str = "needs_improvement"

    def section_feedback(self) -> dict[str, Any]:
        sections: dict[str, Any] = {}
        for key in ACADEMY_SECTIONS:
            sections[key] = {
                "status": getattr(self, f"{key}_status"),
                "time_used": getattr(self, f"{key}_time_used"),
                "remarks": getattr(self, f"{key}_remarks"),
            }
        criteria = {}
        for key, score_key, remarks_key in ACADEMY_CRITERIA_REMARKS:
            criteria[key] = {
                "score": getattr(self, score_key),
                "remarks": getattr(self, remarks_key),
            }
        sections["marking_criteria"] = criteria
        return sections

    def scores(self) -> dict[str, str]:
        return {
            "teacher_guidance_compliance_score": self.teacher_guidance_compliance_score,
            "timing_adherence_score": self.timing_adherence_score,
            "resource_familiarity_score": self.resource_familiarity_score,
            "english_fluency_score": self.english_fluency_score,
            "confidence_delivery_score": self.confidence_delivery_score,
            "engagement_technique_score": self.engagement_technique_score,
        }


class UpdateAcademyStatusForm(BaseModel):
    academy_status: str = ""


class PromoteAcademyTeacherForm(BaseModel):
    teacher_assigned_group: str = ""
    teacher_pay_rate: str = "0"
    teacher_category: str = "junior"
    teacher_semester_stage: str = "1-2"
    teacher_promotion_notes: str = ""


class AcademyCredentials(BaseModel):
    role: str = "teacher"
    login: str = ""
    teacher_code: str = ""
    temporary_password: str = ""
    display_name: str = ""
    subject_name: str = ""


class TeacherAcademyMutationResult(BaseModel):
    message: str
    academy: list[dict[str, Any]] = Field(default_factory=list)
    teachers: list[dict[str, Any]] = Field(default_factory=list)
    credentials: AcademyCredentials | None = None


def form_list(value: Any) -> list[str]:
    return _split_form_items(value)


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


def filter_academy_teachers_for_current_scope(rows):
    from backend.roles.head_of_department.academy_scope import (
        filter_academy_teachers_for_current_scope as _filter_academy_teachers_for_current_scope,
    )

    return _filter_academy_teachers_for_current_scope(rows)


def academy_payload(message: str, *, credentials: dict | None = None):
    invalidate_admin_page_context_cache()
    payload: dict[str, Any] = {
        "message": message,
        "academy": filter_academy_teachers_for_current_scope(list_academy_teachers()),
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
    )


def update_assignment_response(assignment_id: int, payload: UpdateAcademyAssignmentForm):
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
    return academy_payload("Academy lesson updated.")


def add_assessment_response(
    academy_teacher_id: int,
    payload: AddAcademyAssessmentForm,
    *,
    created_by_label: str = "Academic Director",
    created_by_login: str = "",
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
    return academy_payload("Assessment saved.")


def delete_assessment_response(academy_teacher_id: int, assessment_id: int):
    deleted, error_message = delete_assessment(
        academy_teacher_id=academy_teacher_id,
        assessment_id=assessment_id,
    )
    if not deleted:
        academy_error(error_message or "Unable to delete assessment report.")
    return academy_payload("Assessment report deleted.")


def update_status_response(academy_teacher_id: int, payload: UpdateAcademyStatusForm):
    updated, error_message = update_academy_status(
        academy_teacher_id=academy_teacher_id,
        status=payload.academy_status,
    )
    if not updated:
        academy_error(error_message or "Unable to update academy status.")
    return academy_payload("Academy status updated.")


def delete_academy_teacher_response(academy_teacher_id: int):
    deleted, error_message = delete_academy_teacher(academy_teacher_id=academy_teacher_id)
    if not deleted:
        academy_error(error_message or "Unable to delete academy teacher.")
    return academy_payload("Academy teacher deleted.")


def promote_response(academy_teacher_id: int, payload: PromoteAcademyTeacherForm):
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
    return academy_payload("Academy teacher promoted to Active Teachers.")


__all__ = [
    "ACADEMY_CRITERIA_REMARKS",
    "ACADEMY_SECTIONS",
    "AcademyCredentials",
    "AddAcademyAssessmentForm",
    "CreateAcademyTeacherForm",
    "PromoteAcademyTeacherForm",
    "TeacherAcademyMutationResult",
    "UpdateAcademyAssignmentForm",
    "UpdateAcademyStatusForm",
    "academy_error",
    "academy_payload",
    "add_assessment_response",
    "assessment_scores_from_form",
    "assessment_sections_from_form",
    "create_academy_teacher_response",
    "delete_assessment_response",
    "delete_academy_teacher_response",
    "filter_academy_teachers_for_current_scope",
    "form_list",
    "promote_response",
    "safe_credentials",
    "update_assignment_response",
    "update_status_response",
]
