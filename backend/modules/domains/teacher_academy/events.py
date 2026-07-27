"""Typed durable events emitted by Teacher Academy commands."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.core.unit_of_work import UnitOfWork
from backend.modules.domains.teacher_academy.domain_types import TeacherAcademyJobTopic
from backend.modules.jobs.schemas import EnqueueJobCommand


class AcademyJobModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AcademyTeacherSummary(AcademyJobModel):
    academy_teacher_id: int = 0
    full_name: str = ""
    subject_id: int = 0
    subject: str = ""
    telegram_username: str = ""
    telegram_user_id: int = 0


class AcademyAssignmentSummary(AcademyJobModel):
    assignment_id: int = 0
    lesson_number: str = ""
    lesson_topic: str = ""
    assignment_type: str = ""
    deadline_date: str = ""
    session_datetime: str = ""
    evaluator_id: int = 0
    evaluator_name: str = ""


class AcademyAssessmentSummary(AcademyJobModel):
    decision: str = ""
    weighted_score: float | None = None
    assessment_datetime: str = ""


class SendAcademyNotificationPayload(AcademyJobModel):
    academy_teacher: AcademyTeacherSummary = Field(default_factory=AcademyTeacherSummary)
    event_type: str
    title: str = ""
    body: str = ""
    source: str = "Academic Department"
    assignment: AcademyAssignmentSummary | None = None
    assessment: AcademyAssessmentSummary | None = None
    lessons_count: int = Field(default=0, ge=0)


def enqueue_academy_notification(
    uow: UnitOfWork,
    *,
    payload: SendAcademyNotificationPayload,
    idempotency_key: str,
) -> int:
    """Write a notification job in the command's existing transaction."""

    return uow.enqueue(
        EnqueueJobCommand(
            topic=TeacherAcademyJobTopic.SEND_NOTIFICATION.value,
            payload=payload.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
    )


__all__ = [
    "AcademyAssessmentSummary",
    "AcademyAssignmentSummary",
    "AcademyTeacherSummary",
    "SendAcademyNotificationPayload",
    "enqueue_academy_notification",
]
