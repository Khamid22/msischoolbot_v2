"""Durable workers for invoice generation, reminders, and account holds."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from datetime import time as datetime_time

from pydantic import BaseModel, ConfigDict

from backend.core.clock import SystemClock
from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.core.time import SCHOOL_TIMEZONE
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.finance import billing_profile_repository
from backend.modules.domains.finance import enforcement as billing_enforcement
from backend.modules.domains.finance import enforcement_repository
from backend.modules.domains.finance.domain_types import (
    BillingHoldTarget,
    BillingJobTopic,
    BillingNotificationStage,
)
from backend.modules.domains.finance.notification_sender import (
    billing_notification_text,
    send_billing_telegram_message,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand

GENERATE_INVOICES_TOPIC = BillingJobTopic.GENERATE_INVOICES.value
BOOTSTRAP_ENFORCEMENT_TOPIC = BillingJobTopic.BOOTSTRAP_ENFORCEMENT.value
PROCESS_ENFORCEMENT_STAGE_TOPIC = BillingJobTopic.PROCESS_ENFORCEMENT_STAGE.value
SEND_BILLING_NOTIFICATION_TOPIC = BillingJobTopic.SEND_BILLING_NOTIFICATION.value
RECONCILE_ENFORCEMENT_TOPIC = BillingJobTopic.RECONCILE_ENFORCEMENT.value
RECONCILE_INTERVAL_MINUTES = 15


class JobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerateInvoicesPayload(JobPayload):
    run_date: date | None = None


class BootstrapEnforcementPayload(JobPayload):
    pass


class ProcessEnforcementStagePayload(JobPayload):
    schedule_id: int
    stage: BillingNotificationStage


class SendBillingNotificationPayload(JobPayload):
    delivery_id: int
    target_type: BillingHoldTarget


class ReconcileEnforcementPayload(JobPayload):
    pass


def _next_school_midnight(now: datetime) -> datetime:
    tomorrow = now.astimezone(SCHOOL_TIMEZONE).date() + timedelta(days=1)
    return datetime.combine(
        tomorrow,
        datetime_time(hour=0, minute=5),
        tzinfo=SCHOOL_TIMEZONE,
    ).astimezone(UTC)


def _enqueue_reconciliation(conn, now: datetime) -> None:
    next_run = now.astimezone(UTC) + timedelta(minutes=RECONCILE_INTERVAL_MINUTES)
    enqueue_on_connection(
        conn,
        EnqueueJobCommand(
            topic=RECONCILE_ENFORCEMENT_TOPIC,
            payload={},
            idempotency_key=(
                "billing-enforcement-reconcile:"
                f"{next_run.strftime('%Y-%m-%dT%H:%M')}"
            ),
            available_at=next_run,
            max_attempts=10,
        ),
    )


def generate_recurring_invoices(
    payload: GenerateInvoicesPayload,
    context: JobExecutionContext,
) -> None:
    del context
    now = SystemClock().now()
    run_date = payload.run_date or now.astimezone(SCHOOL_TIMEZONE).date()
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
            invoice_id = billing_profile_repository.insert_generated_monthly_invoice(
                unit_of_work.conn,
                profile_row=profile,
                item_rows=items,
                run_date=run_date,
            )
            if invoice_id:
                billing_enforcement.start_invoice_enforcement(
                    unit_of_work.conn,
                    invoice_id=invoice_id,
                    now=now,
                )
        unit_of_work.enqueue(
            EnqueueJobCommand(
                topic=GENERATE_INVOICES_TOPIC,
                payload={},
                idempotency_key=(
                    "finance-generate-invoices:"
                    f"{(run_date + timedelta(days=1)).isoformat()}"
                ),
                available_at=_next_school_midnight(now),
                max_attempts=10,
            )
        )
        commit_unit_of_work(unit_of_work)


def bootstrap_billing_enforcement(
    payload: BootstrapEnforcementPayload,
    context: JobExecutionContext,
) -> None:
    del payload, context
    now = SystemClock().now()
    unit_of_work_factory = UnitOfWorkFactory(job_enqueuer=enqueue_on_connection)
    with unit_of_work_factory.transaction() as unit_of_work:
        rows = enforcement_repository.list_bootstrap_invoice_rows(
            unit_of_work.conn,
            limit=500,
        )
        for row in rows:
            billing_enforcement.start_invoice_enforcement(
                unit_of_work.conn,
                invoice_id=int(row["id"]),
                now=now,
                bootstrap=True,
            )
        if len(rows) == 500:
            unit_of_work.enqueue(
                EnqueueJobCommand(
                    topic=BOOTSTRAP_ENFORCEMENT_TOPIC,
                    payload={},
                    idempotency_key=(
                        "finance-bootstrap-billing-enforcement:"
                        f"after-{int(rows[-1]['id'])}"
                    ),
                    max_attempts=10,
                )
            )
        _enqueue_reconciliation(unit_of_work.conn, now)
        commit_unit_of_work(unit_of_work)


def process_enforcement_stage(
    payload: ProcessEnforcementStagePayload,
    context: JobExecutionContext,
) -> None:
    del context
    unit_of_work_factory = UnitOfWorkFactory(job_enqueuer=enqueue_on_connection)
    with unit_of_work_factory.transaction() as unit_of_work:
        billing_enforcement.process_enforcement_stage(
            unit_of_work.conn,
            schedule_id=payload.schedule_id,
            stage=payload.stage,
            now=SystemClock().now(),
        )
        commit_unit_of_work(unit_of_work)


def send_billing_notification(
    payload: SendBillingNotificationPayload,
    context: JobExecutionContext,
) -> None:
    del context
    unit_of_work_factory = UnitOfWorkFactory()
    with unit_of_work_factory.read() as unit_of_work:
        row = enforcement_repository.get_notification_delivery_row(
            unit_of_work.conn,
            payload.delivery_id,
        )
    if not row or str(row["status"]) in {"sent", "skipped"}:
        return
    if row["telegram_user_id"] is None:
        with unit_of_work_factory.transaction() as unit_of_work:
            enforcement_repository.update_notification_delivery(
                unit_of_work.conn,
                delivery_id=payload.delivery_id,
                status="skipped",
                error="telegram_not_linked",
            )
            commit_unit_of_work(unit_of_work)
        return
    if (
        payload.target_type is not BillingHoldTarget.HOUSEHOLD_STUDENT
        and payload.target_type is not BillingHoldTarget.LINKED_PARENT
        and payload.target_type is not BillingHoldTarget.DEBTOR_STUDENT
    ):
        return
    if (
        str(row["invoice_status"]) not in enforcement_repository.OPEN_INVOICE_STATUSES
        and str(row["stage"]) != BillingNotificationStage.RESTORED.value
    ):
        with unit_of_work_factory.transaction() as unit_of_work:
            enforcement_repository.update_notification_delivery(
                unit_of_work.conn,
                delivery_id=payload.delivery_id,
                status="skipped",
                error="invoice_no_longer_payable",
            )
            commit_unit_of_work(unit_of_work)
        return
    text = billing_notification_text(
        stage=BillingNotificationStage(str(row["stage"])),
        target_type=payload.target_type,
        language=str(row["language"]),
        student_name=str(row["student_name"]),
        invoice_number=str(row["invoice_number"]),
        balance_minor=int(row["total_minor"]) - int(row["paid_minor"]),
        currency=str(row["currency"]),
        deadline_at=row["deadline_at"],
    )
    try:
        send_billing_telegram_message(
            telegram_user_id=int(row["telegram_user_id"]),
            text=text,
            target_type=payload.target_type,
            language=str(row["language"]),
        )
    except Exception as exc:
        with unit_of_work_factory.transaction() as unit_of_work:
            enforcement_repository.update_notification_delivery(
                unit_of_work.conn,
                delivery_id=payload.delivery_id,
                status="failed",
                error=str(exc),
            )
            commit_unit_of_work(unit_of_work)
        raise
    with unit_of_work_factory.transaction() as unit_of_work:
        enforcement_repository.update_notification_delivery(
            unit_of_work.conn,
            delivery_id=payload.delivery_id,
            status="sent",
        )
        commit_unit_of_work(unit_of_work)


def reconcile_billing_enforcement(
    payload: ReconcileEnforcementPayload,
    context: JobExecutionContext,
) -> None:
    del payload, context
    now = SystemClock().now()
    unit_of_work_factory = UnitOfWorkFactory(job_enqueuer=enqueue_on_connection)
    with unit_of_work_factory.transaction() as unit_of_work:
        billing_enforcement.reconcile_active_schedules(
            unit_of_work.conn,
            now=now,
        )
        _enqueue_reconciliation(unit_of_work.conn, now)
        commit_unit_of_work(unit_of_work)


GENERATE_INVOICES_HANDLER = JobHandlerSpec(
    topic=GENERATE_INVOICES_TOPIC,
    payload_model=GenerateInvoicesPayload,
    handler=generate_recurring_invoices,
)
BOOTSTRAP_ENFORCEMENT_HANDLER = JobHandlerSpec(
    topic=BOOTSTRAP_ENFORCEMENT_TOPIC,
    payload_model=BootstrapEnforcementPayload,
    handler=bootstrap_billing_enforcement,
)
PROCESS_ENFORCEMENT_STAGE_HANDLER = JobHandlerSpec(
    topic=PROCESS_ENFORCEMENT_STAGE_TOPIC,
    payload_model=ProcessEnforcementStagePayload,
    handler=process_enforcement_stage,
)
SEND_BILLING_NOTIFICATION_HANDLER = JobHandlerSpec(
    topic=SEND_BILLING_NOTIFICATION_TOPIC,
    payload_model=SendBillingNotificationPayload,
    handler=send_billing_notification,
)
RECONCILE_ENFORCEMENT_HANDLER = JobHandlerSpec(
    topic=RECONCILE_ENFORCEMENT_TOPIC,
    payload_model=ReconcileEnforcementPayload,
    handler=reconcile_billing_enforcement,
)


__all__ = [
    "BOOTSTRAP_ENFORCEMENT_HANDLER",
    "BOOTSTRAP_ENFORCEMENT_TOPIC",
    "GENERATE_INVOICES_HANDLER",
    "GENERATE_INVOICES_TOPIC",
    "PROCESS_ENFORCEMENT_STAGE_HANDLER",
    "PROCESS_ENFORCEMENT_STAGE_TOPIC",
    "RECONCILE_ENFORCEMENT_HANDLER",
    "RECONCILE_ENFORCEMENT_TOPIC",
    "SEND_BILLING_NOTIFICATION_HANDLER",
    "SEND_BILLING_NOTIFICATION_TOPIC",
    "bootstrap_billing_enforcement",
    "generate_recurring_invoices",
    "process_enforcement_stage",
    "reconcile_billing_enforcement",
    "send_billing_notification",
]
