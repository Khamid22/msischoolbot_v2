"""Transaction-bound 48-hour invoice enforcement orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.unit_of_work import Connection
from backend.modules.domains.finance import enforcement_repository as repository
from backend.modules.domains.finance import ledger_repository
from backend.modules.domains.finance.domain_types import (
    BillingAccessMode,
    BillingEnforcementState,
    BillingHoldTarget,
    BillingJobTopic,
    BillingNotificationStage,
)
from backend.modules.domains.finance.policies import (
    PAYMENT_WINDOW_HOURS,
    SIX_HOUR_REMINDER,
    TWENTY_FOUR_HOUR_REMINDER,
    enforcement_deadline,
    enforcement_start,
)
from backend.modules.domains.finance.schemas import (
    BillingAccessInvoice,
    BillingAccessStatus,
    BillingAccessStudent,
)
from backend.modules.jobs.contracts import enqueue_on_connection
from backend.modules.jobs.schemas import EnqueueJobCommand


def _stage_available_at(
    *,
    stage: BillingNotificationStage,
    countdown_started_at: datetime,
    deadline_at: datetime,
) -> datetime:
    if stage is BillingNotificationStage.INITIAL:
        return countdown_started_at
    if stage is BillingNotificationStage.TWENTY_FOUR_HOURS:
        return deadline_at - TWENTY_FOUR_HOUR_REMINDER
    if stage is BillingNotificationStage.SIX_HOURS:
        return deadline_at - SIX_HOUR_REMINDER
    return deadline_at


def _enqueue_stage_jobs(
    conn: Connection,
    *,
    schedule_id: int,
    countdown_started_at: datetime,
    deadline_at: datetime,
) -> None:
    for stage in (
        BillingNotificationStage.INITIAL,
        BillingNotificationStage.TWENTY_FOUR_HOURS,
        BillingNotificationStage.SIX_HOURS,
        BillingNotificationStage.HELD,
    ):
        enqueue_on_connection(
            conn,
            EnqueueJobCommand(
                topic=BillingJobTopic.PROCESS_ENFORCEMENT_STAGE.value,
                payload={"schedule_id": schedule_id, "stage": stage.value},
                idempotency_key=(
                    f"billing-enforcement-stage:{schedule_id}:{stage.value}"
                ),
                available_at=_stage_available_at(
                    stage=stage,
                    countdown_started_at=countdown_started_at,
                    deadline_at=deadline_at,
                ),
                max_attempts=10,
            ),
        )


def start_invoice_enforcement(
    conn: Connection,
    *,
    invoice_id: int,
    now: datetime,
    bootstrap: bool = False,
) -> int:
    invoice = ledger_repository.get_invoice_row(
        conn,
        invoice_id=invoice_id,
        for_update=True,
    )
    if (
        not invoice
        or invoice["admission_id"] is not None
        or invoice["student_id"] is None
        or str(invoice["status"]) not in repository.OPEN_INVOICE_STATUSES
        or int(invoice["total_minor"]) <= int(invoice["paid_minor"])
    ):
        return 0
    existing = repository.get_schedule_by_invoice_row(conn, invoice_id)
    if existing:
        return int(existing["id"])
    normalized_now = now.astimezone(UTC)
    if bootstrap:
        countdown_started_at = normalized_now
        deadline_at = normalized_now + timedelta(hours=PAYMENT_WINDOW_HOURS)
    else:
        deadline_at = enforcement_deadline(
            issued_at=invoice["issued_at"] or invoice["created_at"],
            due_date=invoice["due_date"],
        )
        countdown_started_at = enforcement_start(deadline_at)
    schedule_id = repository.insert_schedule(
        conn,
        invoice_id=invoice_id,
        student_id=int(invoice["student_id"]),
        countdown_started_at=countdown_started_at,
        deadline_at=deadline_at,
        bootstrap=bootstrap,
    )
    if schedule_id:
        _enqueue_stage_jobs(
            conn,
            schedule_id=schedule_id,
            countdown_started_at=countdown_started_at,
            deadline_at=deadline_at,
        )
    return schedule_id


def _recipient_key(target: Any) -> str:
    if target["account_id"] is not None:
        return f"account:{int(target['account_id'])}"
    return f"{str(target['target_type'])}:{int(target['person_id'])}"


def _enqueue_notifications(
    conn: Connection,
    *,
    schedule_id: int,
    stage: BillingNotificationStage,
    targets: list[Any],
) -> None:
    seen_telegram_ids: set[int] = set()
    for target in targets:
        telegram_user_id = (
            int(target["telegram_user_id"])
            if target["telegram_user_id"] is not None
            else None
        )
        delivery_id = repository.insert_notification_delivery(
            conn,
            schedule_id=schedule_id,
            stage=stage,
            recipient_key=_recipient_key(target),
            account_id=(
                int(target["account_id"])
                if target["account_id"] is not None
                else None
            ),
            telegram_user_id=telegram_user_id,
            language=str(target["language"]),
        )
        if not delivery_id:
            continue
        if telegram_user_id is None:
            repository.update_notification_delivery(
                conn,
                delivery_id=delivery_id,
                status="skipped",
                error="telegram_not_linked",
            )
            continue
        if telegram_user_id in seen_telegram_ids:
            repository.update_notification_delivery(
                conn,
                delivery_id=delivery_id,
                status="skipped",
                error="duplicate_telegram_recipient",
            )
            continue
        seen_telegram_ids.add(telegram_user_id)
        enqueue_on_connection(
            conn,
            EnqueueJobCommand(
                topic=BillingJobTopic.SEND_BILLING_NOTIFICATION.value,
                payload={
                    "delivery_id": delivery_id,
                    "target_type": str(target["target_type"]),
                },
                idempotency_key=f"billing-notification-delivery:{delivery_id}",
                max_attempts=10,
            ),
        )


def process_enforcement_stage(
    conn: Connection,
    *,
    schedule_id: int,
    stage: BillingNotificationStage,
    now: datetime,
) -> None:
    schedule = repository.get_schedule_row(conn, schedule_id, for_update=True)
    if not schedule:
        return
    if str(schedule["invoice_status"]) not in repository.OPEN_INVOICE_STATUSES:
        reconcile_invoice_enforcement(
            conn,
            invoice_id=int(schedule["invoice_id"]),
            now=now,
        )
        return
    if int(schedule["total_minor"]) <= int(schedule["paid_minor"]):
        reconcile_invoice_enforcement(
            conn,
            invoice_id=int(schedule["invoice_id"]),
            now=now,
        )
        return
    if str(schedule["state"]) in {
        BillingEnforcementState.CLEARED.value,
        BillingEnforcementState.CANCELLED.value,
    }:
        return
    normalized_now = now.astimezone(UTC)
    if stage is BillingNotificationStage.HELD:
        if normalized_now < schedule["deadline_at"]:
            return
        targets = repository.list_household_target_rows(
            conn,
            int(schedule["student_id"]),
        )
        repository.activate_household_holds(
            conn,
            schedule_id=schedule_id,
            targets=targets,
        )
        active_accounts = [
            int(target["account_id"])
            for target in targets
            if target["account_id"] is not None
        ]
        repository.release_removed_household_holds(
            conn,
            schedule_id=schedule_id,
            active_account_ids=active_accounts,
        )
        repository.set_schedule_state(
            conn,
            schedule_id=schedule_id,
            state=BillingEnforcementState.HELD,
        )
        _enqueue_notifications(
            conn,
            schedule_id=schedule_id,
            stage=stage,
            targets=targets,
        )
        return
    repository.set_schedule_state(
        conn,
        schedule_id=schedule_id,
        state=BillingEnforcementState.COUNTDOWN,
    )
    targets = repository.list_household_target_rows(
        conn,
        int(schedule["student_id"]),
    )
    _enqueue_notifications(
        conn,
        schedule_id=schedule_id,
        stage=stage,
        targets=targets,
    )


def reconcile_invoice_enforcement(
    conn: Connection,
    *,
    invoice_id: int,
    now: datetime,
) -> None:
    schedule = repository.get_schedule_by_invoice_row(
        conn,
        invoice_id,
        for_update=True,
    )
    if not schedule:
        start_invoice_enforcement(
            conn,
            invoice_id=invoice_id,
            now=now,
        )
        return
    is_payable = (
        str(schedule["invoice_status"]) in repository.OPEN_INVOICE_STATUSES
        and int(schedule["total_minor"]) > int(schedule["paid_minor"])
    )
    if not is_payable:
        was_held = str(schedule["state"]) == BillingEnforcementState.HELD.value
        released_account_ids = repository.release_schedule_holds(
            conn,
            schedule_id=int(schedule["id"]),
            reason=(
                "invoice_voided"
                if str(schedule["invoice_status"]) == "voided"
                else "invoice_settled"
            ),
        )
        repository.set_schedule_state(
            conn,
            schedule_id=int(schedule["id"]),
            state=(
                BillingEnforcementState.CANCELLED
                if str(schedule["invoice_status"]) == "voided"
                else BillingEnforcementState.CLEARED
            ),
        )
        if was_held and released_account_ids:
            targets = [
                target
                for target in repository.list_household_target_rows(
                    conn,
                    int(schedule["student_id"]),
                )
                if (
                    target["account_id"] is None
                    or (
                        int(target["account_id"]) in released_account_ids
                        and not repository.account_has_active_hold(
                            conn,
                            int(target["account_id"]),
                        )
                    )
                )
            ]
            _enqueue_notifications(
                conn,
                schedule_id=int(schedule["id"]),
                stage=BillingNotificationStage.RESTORED,
                targets=targets,
            )
        return
    if now.astimezone(UTC) >= schedule["deadline_at"]:
        process_enforcement_stage(
            conn,
            schedule_id=int(schedule["id"]),
            stage=BillingNotificationStage.HELD,
            now=now,
        )
        return
    repository.set_schedule_state(
        conn,
        schedule_id=int(schedule["id"]),
        state=BillingEnforcementState.COUNTDOWN,
    )


def reconcile_active_schedules(conn: Connection, *, now: datetime) -> None:
    for row in repository.list_active_schedule_rows(conn):
        schedule = repository.get_schedule_row(conn, int(row["id"]))
        if not schedule:
            continue
        reconcile_invoice_enforcement(
            conn,
            invoice_id=int(schedule["invoice_id"]),
            now=now,
        )
        refreshed = repository.get_schedule_row(conn, int(row["id"]))
        if not refreshed or str(refreshed["state"]) != BillingEnforcementState.HELD.value:
            continue
        targets = repository.list_household_target_rows(
            conn,
            int(refreshed["student_id"]),
        )
        repository.activate_household_holds(
            conn,
            schedule_id=int(refreshed["id"]),
            targets=targets,
        )
        repository.release_removed_household_holds(
            conn,
            schedule_id=int(refreshed["id"]),
            active_account_ids=[
                int(target["account_id"])
                for target in targets
                if target["account_id"] is not None
            ],
        )


def account_billing_access(
    conn: Connection,
    *,
    account_id: int,
    now: datetime,
) -> BillingAccessStatus:
    rows = repository.list_account_enforcement_rows(conn, account_id)
    is_held = any(str(row["hold_status"] or "") == "active" for row in rows)
    deadlines = [row["deadline_at"] for row in rows]
    earliest_deadline = min(deadlines) if deadlines else None
    remaining_seconds = (
        max(0, int((earliest_deadline - now.astimezone(UTC)).total_seconds()))
        if earliest_deadline
        else 0
    )
    invoices: list[BillingAccessInvoice] = []
    affected_students: list[BillingAccessStudent] = []
    for row in rows:
        target_type = BillingHoldTarget(str(row["target_type"]))
        affected_students.append(
            BillingAccessStudent(
                student_id=int(row["student_id"]),
                student_name=str(row["student_name"]),
                student_code=str(row["student_code"]),
                target_type=target_type,
            )
        )
        can_view = target_type is not BillingHoldTarget.HOUSEHOLD_STUDENT
        if can_view:
            invoices.append(
                BillingAccessInvoice(
                    invoice_id=int(row["invoice_id"]),
                    invoice_number=str(row["invoice_number"]),
                    student_id=int(row["student_id"]),
                    student_row_id=(
                        int(row["legacy_student_row_id"])
                        if row["legacy_student_row_id"] is not None
                        else None
                    ),
                    student_name=str(row["student_name"]),
                    student_code=str(row["student_code"]),
                    total_minor=int(row["total_minor"]),
                    paid_minor=int(row["paid_minor"]),
                    balance_minor=int(row["total_minor"]) - int(row["paid_minor"]),
                    currency=str(row["currency"]),
                    deadline_at=row["deadline_at"],
                    target_type=target_type,
                    can_view_invoice=True,
                    can_pay_online=True,
                )
            )
    return BillingAccessStatus(
        mode=(
            BillingAccessMode.PAYMENT_ONLY if is_held else BillingAccessMode.NORMAL
        ),
        countdown_deadline_at=earliest_deadline,
        remaining_seconds=remaining_seconds,
        blocking_invoice_count=len(
            {int(row["invoice_id"]) for row in rows if row["hold_status"] == "active"}
        ),
        invoices=invoices,
        affected_students=affected_students,
    )


def student_invoice_checkout_data(
    conn: Connection,
    *,
    student_id: int,
    invoice_id: int,
) -> tuple[int, str]:
    if not repository.student_has_invoice_access(
        conn,
        student_id=student_id,
        invoice_id=invoice_id,
    ):
        raise ValueError("Invoice was not found.")
    invoice = ledger_repository.get_invoice_row(conn, invoice_id=invoice_id)
    if (
        not invoice
        or str(invoice["status"]) not in repository.OPEN_INVOICE_STATUSES
    ):
        raise ValueError("This invoice is not payable.")
    balance_minor = int(invoice["total_minor"]) - int(invoice["paid_minor"])
    if balance_minor <= 0:
        raise ValueError("This invoice has no outstanding balance.")
    return balance_minor, str(invoice["currency"])


__all__ = [
    "account_billing_access",
    "process_enforcement_stage",
    "reconcile_active_schedules",
    "reconcile_invoice_enforcement",
    "start_invoice_enforcement",
    "student_invoice_checkout_data",
]
