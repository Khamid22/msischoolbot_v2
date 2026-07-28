"""Durable worker handlers owned by admissions."""

from __future__ import annotations

import json
from urllib import error as urlerror
from urllib import request

from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.core.runtime.config import get_app_settings
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.admissions import repository
from backend.modules.domains.admissions.domain_types import AdmissionJobTopic
from backend.modules.domains.admissions.events import (
    ActivationCompletedPayload,
    GenerateInvoicesPayload,
)
from backend.modules.domains.finance.job_handlers import (
    GenerateInvoicesPayload as FinanceGenerateInvoicesPayload,
)
from backend.modules.domains.finance.job_handlers import (
    generate_recurring_invoices as generate_finance_invoices,
)


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
    """Compatibility entrypoint; recurring billing is now owned by Finance."""

    generate_finance_invoices(
        FinanceGenerateInvoicesPayload(run_date=payload.run_date),
        context,
    )


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
