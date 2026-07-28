"""Durable worker handlers owned by admissions."""

from __future__ import annotations

import json
from datetime import UTC, datetime, time as datetime_time, timedelta
from urllib import error as urlerror
from urllib import request

from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.core.runtime.config import get_app_settings
from backend.core.time import SCHOOL_TIMEZONE, school_now
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.admissions import contracts, repository
from backend.modules.domains.admissions.domain_types import AdmissionJobTopic, InvoiceKind
from backend.modules.domains.admissions.events import (
    ActivationCompletedPayload,
    GenerateInvoicesPayload,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand


def _next_school_midnight() -> datetime:
    tomorrow = school_now().date() + timedelta(days=1)
    return datetime.combine(
        tomorrow,
        datetime_time(hour=0, minute=5),
        tzinfo=SCHOOL_TIMEZONE,
    ).astimezone(UTC)


def _send_telegram_message(chat_id: int, text: str) -> None:
    settings = get_app_settings().telegram
    if not settings.bot_token:
        raise RuntimeError("Telegram bot token is not configured.")
    payload = json.dumps(
        {
            "chat_id": int(chat_id),
            "text": text,
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    telegram_request = request.Request(
        f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(
            telegram_request,
            timeout=settings.api_timeout_seconds,
        ) as response:
            if not 200 <= int(response.status) < 300:
                raise RuntimeError("Telegram rejected the activation notification.")
    except (OSError, urlerror.URLError, urlerror.HTTPError) as exc:
        raise RuntimeError("Telegram activation notification failed.") from exc


def notify_activation(
    payload: ActivationCompletedPayload,
    context: JobExecutionContext,
) -> None:
    del context
    unit_of_work_factory = UnitOfWorkFactory()
    with unit_of_work_factory.read() as unit_of_work:
        row = repository.get_activation_notification_row(
            unit_of_work.conn,
            admission_id=payload.admission_id,
            parent_id=payload.parent_id,
        )
    if not row or not row["telegram_user_id"]:
        return
    language = str(row["preferred_language"] or "uz")
    student_name = str(row["student_full_name"])
    text = (
        f"{student_name} uchun ro'yxatdan o'tish faollashtirildi."
        if language == "uz"
        else f"Зачисление для {student_name} активировано."
    )
    _send_telegram_message(int(row["telegram_user_id"]), text)


def generate_recurring_invoices(
    payload: GenerateInvoicesPayload,
    context: JobExecutionContext,
) -> None:
    del context
    run_date = payload.run_date or school_now().date()
    unit_of_work_factory = UnitOfWorkFactory(job_enqueuer=enqueue_on_connection)
    with unit_of_work_factory.transaction() as unit_of_work:
        rows = repository.list_due_recurring_admission_rows(
            unit_of_work.conn,
            run_date,
        )
        for row in rows:
            contracts.issue_invoice(
                unit_of_work.conn,
                int(row["id"]),
                due_date=run_date,
                billing_period=run_date.replace(day=1),
                invoice_kind=InvoiceKind.MONTHLY,
                actor=contracts.AdmissionActor(staff_id=None, account_id=None),
            )
        unit_of_work.enqueue(
            EnqueueJobCommand(
                topic=AdmissionJobTopic.GENERATE_INVOICES.value,
                payload={},
                idempotency_key=(
                    "admissions-generate-invoices:"
                    f"{(run_date + timedelta(days=1)).isoformat()}"
                ),
                available_at=_next_school_midnight(),
                max_attempts=10,
            )
        )
        commit_unit_of_work(unit_of_work)


ACTIVATION_COMPLETED_HANDLER = JobHandlerSpec(
    topic=AdmissionJobTopic.ACTIVATION_COMPLETED.value,
    payload_model=ActivationCompletedPayload,
    handler=notify_activation,
)

GENERATE_INVOICES_HANDLER = JobHandlerSpec(
    topic=AdmissionJobTopic.GENERATE_INVOICES.value,
    payload_model=GenerateInvoicesPayload,
    handler=generate_recurring_invoices,
)


__all__ = [
    "ACTIVATION_COMPLETED_HANDLER",
    "GENERATE_INVOICES_HANDLER",
    "generate_recurring_invoices",
    "notify_activation",
]
