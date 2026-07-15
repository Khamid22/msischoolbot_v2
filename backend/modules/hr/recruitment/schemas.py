"""Pydantic contracts for the recruitment API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


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
    telegram_username: str = Field(default="", max_length=120)
    applied_position: str = Field(default="", max_length=200)
    subject_id: OptionalInt = Field(default=None, ge=1)
    application_date: OptionalDate = None
    source: str = Field(default="", max_length=120)
    comment: str = Field(default="", max_length=5000)


class CandidateUpdate(StrictModel):
    expected_version: OptionalInt = Field(default=None, ge=1)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=80)
    telegram_username: str | None = Field(default=None, max_length=120)
    applied_position: str | None = Field(default=None, max_length=200)
    subject_id: OptionalInt = Field(default=None, ge=1)
    application_date: OptionalDate = None
    age: OptionalInt = Field(default=None, ge=14, le=100)
    address: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default=None, max_length=120)
    english_level: str | None = Field(default=None, max_length=120)
    motivation_expectations: str | None = Field(default=None, max_length=5000)
    interests_hobbies: str | None = Field(default=None, max_length=3000)
    preferred_schedule: str | None = Field(default=None, max_length=1000)
    employment_availability: str | None = Field(default=None, max_length=120)
    work_experience: str | None = Field(default=None, max_length=5000)
    teaching_experience: str | None = Field(default=None, max_length=5000)
    previous_workplace: str | None = Field(default=None, max_length=1000)
    expected_salary_uzs: OptionalDecimal = Field(default=None, ge=0)
    available_start_date: OptionalDate = None


class StageChange(StrictModel):
    stage: str = Field(min_length=1, max_length=80)
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)


class CandidateHold(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=5000)
    application_date: OptionalDate = None


class AppointmentFields(StrictModel):
    starts_at: datetime
    duration_minutes: OptionalInt = Field(default=None, ge=15, le=240)
    responsible_account_id: OptionalInt = Field(default=None, ge=1)
    appointment_format: str = Field(default="", max_length=120)
    location_or_link: str = Field(default="", max_length=1000)
    topic: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=5000)
    allow_conflict: bool = False


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
    strengths: str = Field(default="", max_length=5000)
    concerns: str = Field(default="", max_length=5000)
    hr_recommendation: str = Field(default="", max_length=5000)
    result: str = Field(min_length=1, max_length=80)


class SubjectTestWrite(StrictModel):
    test_at: OptionalDateTime = None
    subject_id: OptionalInt = Field(default=None, ge=1)
    subject_label: str = Field(default="", max_length=200)
    evaluator_account_id: OptionalInt = Field(default=None, ge=1)
    score: OptionalDecimal = Field(default=None, ge=0)
    maximum_score: OptionalDecimal = Field(default=None, gt=0)
    notes: str = Field(default="", max_length=10000)
    result: str = Field(min_length=1, max_length=80)


class DemoLessonWrite(StrictModel):
    appointment_id: OptionalInt = Field(default=None, ge=1)
    demo_at: OptionalDateTime = None
    subject_id: OptionalInt = Field(default=None, ge=1)
    subject_label: str = Field(default="", max_length=200)
    topic: str = Field(default="", max_length=500)
    evaluator_account_id: OptionalInt = Field(default=None, ge=1)
    overview: str = Field(default="", max_length=10000)
    strengths: str = Field(default="", max_length=5000)
    areas_for_improvement: str = Field(default="", max_length=5000)
    score: OptionalDecimal = Field(default=None, ge=0, le=10)
    result: str = Field(min_length=1, max_length=80)
    recommendation: str = Field(default="", max_length=5000)


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


class EvaluationVoid(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)


class RecruitmentSettingCreate(StrictModel):
    category: str = Field(pattern="^(source|rejection_reason)$")
    label: str = Field(min_length=1, max_length=120)


class RecruitmentMutationResult(BaseModel):
    message: str
    candidate: dict[str, Any] | None = None


class AcademyIntakeOnboarding(StrictModel):
    subject_program_id: int = Field(ge=1)
    curriculum_item_ids: list[int] = Field(min_length=1, max_length=100)


__all__ = [
    "ApprovalRequestCreate",
    "AcademyIntakeOnboarding",
    "ApprovalReview",
    "AppointmentCreate",
    "AppointmentStatusChange",
    "AppointmentUpdate",
    "AssignmentReplace",
    "CandidateCreate",
    "CandidateHold",
    "CandidateUpdate",
    "DemoLessonWrite",
    "EvaluationVoid",
    "FinalDecisionCreate",
    "InterviewWrite",
    "NoteCreate",
    "RecruitmentSettingCreate",
    "RecruitmentMutationResult",
    "ScheduledStageMove",
    "StageChange",
    "SubjectTestWrite",
    "TaskWrite",
]
