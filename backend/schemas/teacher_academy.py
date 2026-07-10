"""Teacher Academy API v1 request and response schemas."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field


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


class SyncAcademyLessonsForm(BaseModel):
    academy_curriculum_item_ids: FormStringList = Field(default_factory=list)


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


__all__ = [
    "ACADEMY_CRITERIA_REMARKS",
    "ACADEMY_SECTIONS",
    "AcademyCredentials",
    "AddAcademyAssessmentForm",
    "CreateAcademyTeacherForm",
    "FormStringList",
    "PromoteAcademyTeacherForm",
    "SyncAcademyLessonsForm",
    "TeacherAcademyMutationResult",
    "UpdateAcademyAssignmentForm",
    "UpdateAcademyStatusForm",
    "form_list",
]
