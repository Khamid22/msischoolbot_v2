"""Pydantic contracts for the recruitment API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from backend.modules.hr.recruitment.constants import (
    DEMO_CRITERIA,
    DEMO_FAILURE_REJECTION_REASONS,
)


def _blank_to_none(value: Any) -> Any:
    return None if isinstance(value, str) and not value.strip() else value


OptionalDate = Annotated[date | None, BeforeValidator(_blank_to_none)]
OptionalDateTime = Annotated[datetime | None, BeforeValidator(_blank_to_none)]
OptionalDecimal = Annotated[Decimal | None, BeforeValidator(_blank_to_none)]
OptionalInt = Annotated[int | None, BeforeValidator(_blank_to_none)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CandidateCreate(StrictModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(default="", max_length=80)
    email: str = Field(default="", max_length=254)
    telegram_username: str = Field(default="", max_length=120)
    age: OptionalInt = Field(default=None, ge=14, le=100)
    address: str = Field(default="", max_length=1000)
    applied_position: str = Field(default="", max_length=200)
    position_option_id: OptionalInt = Field(default=None, ge=1)
    subject_id: OptionalInt = Field(default=None, ge=1)
    application_date: OptionalDate = None
    source_option_id: OptionalInt = Field(default=None, ge=1)
    subsource_option_id: OptionalInt = Field(default=None, ge=1)


class CandidateUpdate(StrictModel):
    expected_version: OptionalInt = Field(default=None, ge=1)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=254)
    telegram_username: str | None = Field(default=None, max_length=120)
    applied_position: str | None = Field(default=None, max_length=200)
    position_option_id: OptionalInt = Field(default=None, ge=1)
    subject_id: OptionalInt = Field(default=None, ge=1)
    application_date: OptionalDate = None
    age: OptionalInt = Field(default=None, ge=14, le=100)
    address: str | None = Field(default=None, max_length=1000)
    source_option_id: OptionalInt = Field(default=None, ge=1)
    subsource_option_id: OptionalInt = Field(default=None, ge=1)
    english_level_option_id: OptionalInt = Field(default=None, ge=1)
    motivation_expectations: str | None = Field(default=None, max_length=5000)
    interests_hobbies: str | None = Field(default=None, max_length=3000)
    schedule_option_id: OptionalInt = Field(default=None, ge=1)
    availability_option_id: OptionalInt = Field(default=None, ge=1)
    education_background: str | None = Field(default=None, max_length=5000)
    work_experience: str | None = Field(default=None, max_length=5000)
    teaching_experience_option_id: OptionalInt = Field(default=None, ge=1)
    previous_workplace: str | None = Field(default=None, max_length=1000)
    expected_salary_option_id: OptionalInt = Field(default=None, ge=1)
    available_start_date: OptionalDate = None


class StageChange(StrictModel):
    stage: str = Field(min_length=1, max_length=80)
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)


class CandidateRestore(StrictModel):
    expected_version: int = Field(ge=1)


class CandidatePermanentDelete(StrictModel):
    expected_version: int = Field(ge=1)
    confirmation: str = Field(min_length=1, max_length=80)


class TrashPurge(StrictModel):
    confirmation: str = Field(min_length=1, max_length=80)


class AppointmentFields(StrictModel):
    starts_at: datetime
    responsible_account_id: OptionalInt = Field(default=None, ge=1)
    appointment_format: str = Field(default="", max_length=120)
    location_or_link: str = Field(default="", max_length=1000)
    topic: str = Field(default="", max_length=500)
    note: str | None = Field(default=None, max_length=5000)


class ScheduledStageMove(AppointmentFields):
    stage: str = Field(pattern="^(job_interview|test_and_demo)$")
    expected_version: int = Field(ge=1)


class AppointmentCreate(AppointmentFields):
    appointment_type: str = Field(pattern="^(job_interview|demo_lesson)$")


class AppointmentUpdate(AppointmentFields):
    expected_version: int = Field(ge=1)


class AppointmentStatusChange(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)


class InterviewSessionStart(StrictModel):
    expected_version: int = Field(ge=1)


class InterviewSessionComplete(StrictModel):
    expected_version: int = Field(ge=1)
    result: str = Field(pattern="^(passed|failed)$")
    reason_detail: str = Field(default="", max_length=10000)
    english_level_option_id: OptionalInt = Field(default=None, ge=1)
    education_background: str = Field(default="", max_length=5000)
    teaching_experience_option_id: OptionalInt = Field(default=None, ge=1)
    interests_hobbies: str = Field(default="", max_length=3000)
    motivation_expectations: str = Field(default="", max_length=5000)


class AssignmentReplace(StrictModel):
    assignee_account_ids: list[int] = Field(default_factory=list, max_length=20)
    subject_id: OptionalInt = Field(default=None, ge=1)


class InterviewWrite(StrictModel):
    appointment_id: OptionalInt = Field(default=None, ge=1)
    interview_at: OptionalDateTime = None
    interviewer_account_id: OptionalInt = Field(default=None, ge=1)
    interview_format: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=10000)
    english_level: str = Field(default="", max_length=120)
    cefr_level: str = Field(default="", max_length=20)
    overall_score: OptionalDecimal = Field(default=None, ge=0, le=10)
    communication_score: OptionalDecimal = Field(default=None, ge=0, le=10)
    strengths: str = Field(default="", max_length=5000)
    concerns: str = Field(default="", max_length=5000)
    hr_recommendation: str = Field(default="", max_length=5000)
    recommendation_code: str = Field(default="", max_length=80)
    result: str = Field(min_length=1, max_length=80)


class StructuredScore(StrictModel):
    score: Decimal = Field(ge=0)
    maximum_score: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def score_does_not_exceed_maximum(self):
        if self.score > self.maximum_score:
            raise ValueError("Score cannot exceed maximum score.")
        return self


class TopicScore(StructuredScore):
    topic: str = Field(min_length=1, max_length=200)


class DemoCriterionScore(StructuredScore):
    criterion: str = Field(min_length=1, max_length=200)
    maximum_score: Decimal = Field(
        default=Decimal("10"), ge=Decimal("10"), le=Decimal("10")
    )


class SubjectTestWrite(StrictModel):
    test_at: OptionalDateTime = None
    subject_id: OptionalInt = Field(default=None, ge=1)
    subject_label: str = Field(default="", max_length=200)
    evaluator_account_id: OptionalInt = Field(default=None, ge=1)
    score: OptionalDecimal = Field(default=None, ge=0)
    maximum_score: OptionalDecimal = Field(default=None, gt=0)
    paper: str = Field(default="", max_length=200)
    topic_scores: list[TopicScore] = Field(default_factory=list, max_length=50)
    notes: str = Field(default="", max_length=10000)
    result: str = Field(min_length=1, max_length=80)


class DemoLessonWrite(StrictModel):
    appointment_id: OptionalInt = Field(default=None, ge=1)
    expected_version: OptionalInt = Field(default=None, ge=1)
    demo_at: OptionalDateTime = None
    subject_id: OptionalInt = Field(default=None, ge=1)
    subject_label: str = Field(default="", max_length=200)
    topic: str = Field(default="", max_length=500)
    evaluator_account_id: OptionalInt = Field(default=None, ge=1)
    overview: str = Field(default="", max_length=10000)
    strengths: str = Field(default="", max_length=5000)
    areas_for_improvement: str = Field(default="", max_length=5000)
    score: OptionalDecimal = Field(default=None, ge=0, le=10)
    criteria_scores: list[DemoCriterionScore] = Field(min_length=5, max_length=5)
    result: str = Field(pattern="^(passed|failed)$")
    recommendation: str = Field(default="", max_length=5000)
    rejection_reason: str = Field(default="", max_length=120)
    reason_detail: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def validate_demo_fields(self):
        criteria = [item.criterion for item in self.criteria_scores]
        if len(set(criteria)) != len(criteria):
            raise ValueError("Demo lesson criteria cannot be duplicated.")
        if set(criteria) != set(DEMO_CRITERIA):
            raise ValueError(
                "Demo lesson scores are required for English fluency, lesson structure, "
                "board skills, student engagement, and confidence & delivery."
            )
        if self.rejection_reason and self.rejection_reason not in DEMO_FAILURE_REJECTION_REASONS:
            raise ValueError("Select a valid demo lesson rejection reason.")
        if self.result == "passed" and (self.rejection_reason or self.reason_detail):
            raise ValueError("Passing demo lessons cannot include a rejection reason.")
        if self.rejection_reason == "other" and not self.reason_detail:
            raise ValueError("Explain the reason when Other is selected.")
        return self


class TaskWrite(StrictModel):
    title: str = Field(min_length=1, max_length=500)
    due_at: OptionalDateTime = None
    responsible_account_id: OptionalInt = Field(default=None, ge=1)
    status: str = Field(default="pending", max_length=40)
    note: str = Field(default="", max_length=5000)


class NoteCreate(StrictModel):
    body: str = Field(min_length=1, max_length=10000)


class ApprovalRequestCreate(StrictModel):
    requested_outcome: str = Field(min_length=1, max_length=80)
    request_note: str = Field(default="", max_length=5000)


class ApprovalReview(StrictModel):
    status: str = Field(pattern="^(approved|returned)$")
    review_comment: str = Field(default="", max_length=5000)


class FinalDecisionCreate(StrictModel):
    decision: str = Field(min_length=1, max_length=80)
    rejection_reason: str = Field(default="", max_length=120)
    reason_detail: str = Field(default="", max_length=5000)
    follow_up_at: OptionalDateTime = None
    approval_id: OptionalInt = Field(default=None, ge=1)


class AcademyTeacherRemoval(StrictModel):
    rejection_reason: str = Field(min_length=1, max_length=120)
    reason_detail: str = Field(default="", max_length=5000)


class TeacherHandoffClose(StrictModel):
    action: str = Field(pattern="^(trash_bin|rejected)$")
    rejection_reason: str = Field(default="", max_length=120)
    reason_detail: str = Field(default="", max_length=5000)


class RecruitmentSettingCreate(StrictModel):
    category: str = Field(
        pattern="^(source|subsource|rejection_reason|position|english_level|schedule|availability|expected_salary|teaching_experience)$"
    )
    label: str = Field(min_length=1, max_length=120)
    parent_id: OptionalInt = Field(default=None, ge=1)


class RecruitmentSettingRename(StrictModel):
    label: str = Field(min_length=1, max_length=120)


class RecruitmentSlaRuleUpdate(StrictModel):
    target_days: int = Field(ge=1, le=90)


class RecruitmentAppointmentReminderUpdate(StrictModel):
    lead_minutes: int = Field(ge=5, le=120)
    expected_version: int = Field(ge=1)


class RecruitmentBrowserPreferenceUpdate(StrictModel):
    enabled: bool
    expected_version: int = Field(ge=0)


class PipelineStageCreate(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    color_token: str = Field(
        pattern="^(neutral|blue|cyan|violet|green|amber|orange|rose)$"
    )
    after_stage_key: str = Field(min_length=1, max_length=80)
    sla_target_days: int = Field(ge=1, le=90)


class PipelineStageUpdate(StrictModel):
    expected_version: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=80)
    color_token: str | None = Field(
        default=None,
        pattern="^(neutral|blue|cyan|violet|green|amber|orange|rose)$",
    )
    after_stage_key: str | None = Field(default=None, min_length=1, max_length=80)
    sla_target_days: OptionalInt = Field(default=None, ge=1, le=90)


class PipelineStageArchive(StrictModel):
    expected_version: int = Field(ge=1)
    replacement_stage_key: str = Field(min_length=1, max_length=80)


class RecruitmentMutationResult(BaseModel):
    message: str
    candidate: dict[str, Any] | None = None


class AcademyIntakeOnboarding(StrictModel):
    subject_program_id: int = Field(ge=1)
    curriculum_item_ids: list[int] = Field(min_length=1, max_length=100)


__all__ = [
    "AcademyTeacherRemoval",
    "ApprovalRequestCreate",
    "AcademyIntakeOnboarding",
    "ApprovalReview",
    "AppointmentCreate",
    "AppointmentStatusChange",
    "AppointmentUpdate",
    "AssignmentReplace",
    "CandidateCreate",
    "CandidatePermanentDelete",
    "CandidateRestore",
    "CandidateUpdate",
    "DemoLessonWrite",
    "FinalDecisionCreate",
    "InterviewWrite",
    "InterviewSessionComplete",
    "InterviewSessionStart",
    "NoteCreate",
    "PipelineStageArchive",
    "PipelineStageCreate",
    "PipelineStageUpdate",
    "RecruitmentSettingCreate",
    "RecruitmentAppointmentReminderUpdate",
    "RecruitmentBrowserPreferenceUpdate",
    "RecruitmentSlaRuleUpdate",
    "RecruitmentMutationResult",
    "ScheduledStageMove",
    "StageChange",
    "SubjectTestWrite",
    "TaskWrite",
    "TrashPurge",
]
