"""Durable monthly invoice generation owned by Finance."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from datetime import time as datetime_time

from pydantic import BaseModel, ConfigDict

from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.core.time import SCHOOL_TIMEZONE, school_now
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.finance import billing_profile_repository
from backend.modules.domains.finance.domain_types import BillingJobTopic
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand

GENERATE_INVOICES_TOPIC = BillingJobTopic.GENERATE_INVOICES.value


class GenerateInvoicesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_date: date | None = None


def _next_school_midnight() -> datetime:
    tomorrow = school_now().date() + timedelta(days=1)
    return datetime.combine(
        tomorrow,
        datetime_time(hour=0, minute=5),
        tzinfo=SCHOOL_TIMEZONE,
    ).astimezone(UTC)


def generate_recurring_invoices(
    payload: GenerateInvoicesPayload,
    context: JobExecutionContext,
) -> None:
    del context
    run_date = payload.run_date or school_now().date()
    unit_of_work_factory = UnitOfWorkFactory(job_enqueuer=enqueue_on_connection)
    with unit_of_work_factory.transaction() as unit_of_work:
        profiles = billing_profile_repository.list_due_billing_profile_rows(
            unit_of_work.conn,
            run_date,
        )
        for profile in profiles:
            items = billing_profile_repository.list_active_profile_item_rows(
                unit_of_work.conn,
                profile_id=int(profile["id"]),
                run_date=run_date,
            )
            billing_profile_repository.insert_generated_monthly_invoice(
                unit_of_work.conn,
                profile_row=profile,
                item_rows=items,
                run_date=run_date,
            )
        unit_of_work.enqueue(
            EnqueueJobCommand(
                topic=GENERATE_INVOICES_TOPIC,
                payload={},
                idempotency_key=(
                    "finance-generate-invoices:"
                    f"{(run_date + timedelta(days=1)).isoformat()}"
                ),
                available_at=_next_school_midnight(),
                max_attempts=10,
            )
        )
        commit_unit_of_work(unit_of_work)


GENERATE_INVOICES_HANDLER = JobHandlerSpec(
    topic=GENERATE_INVOICES_TOPIC,
    payload_model=GenerateInvoicesPayload,
    handler=generate_recurring_invoices,
)


__all__ = [
    "GENERATE_INVOICES_HANDLER",
    "GENERATE_INVOICES_TOPIC",
    "generate_recurring_invoices",
]
