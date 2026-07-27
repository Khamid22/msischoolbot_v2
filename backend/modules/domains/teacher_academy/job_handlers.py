"""Worker handlers owned by the Teacher Academy module."""

from __future__ import annotations

from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.modules.domains.teacher_academy.domain_types import TeacherAcademyJobTopic
from backend.modules.domains.teacher_academy.events import SendAcademyNotificationPayload
from backend.modules.domains.teacher_academy.notifications import notify_academy_teacher_event


def send_academy_notification(
    payload: SendAcademyNotificationPayload,
    context: JobExecutionContext,
) -> None:
    """Deliver one idempotently claimed Teacher Academy notification."""

    del context
    result = notify_academy_teacher_event(
        academy_teacher=payload.academy_teacher.model_dump(),
        event_type=payload.event_type,
        title=payload.title,
        body=payload.body,
        source=payload.source,
        assignment=payload.assignment.model_dump() if payload.assignment else None,
        assessment=payload.assessment.model_dump() if payload.assessment else None,
        lessons_count=payload.lessons_count,
    )
    retryable_reasons = {
        "telegram_bot_token_missing",
        "telegram_send_failed",
    }
    reasons = {str(reason) for reason in result.get("reasons", ())}
    if reasons & retryable_reasons:
        raise RuntimeError(
            "Teacher Academy notification delivery failed: "
            + ", ".join(sorted(reasons & retryable_reasons))
        )


SEND_NOTIFICATION_HANDLER = JobHandlerSpec(
    topic=TeacherAcademyJobTopic.SEND_NOTIFICATION.value,
    payload_model=SendAcademyNotificationPayload,
    handler=send_academy_notification,
)


__all__ = ["SEND_NOTIFICATION_HANDLER", "send_academy_notification"]
