"""Idempotent Payme Merchant API state machine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import time
from typing import Any

from backend.core.clock import SystemClock
from backend.core.runtime.config import PaymeSettings
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.admissions.contracts import (
    AdmissionActor,
    activate_paid_admission,
)
from backend.modules.domains.finance.integrations.payme import repository
from backend.modules.domains.finance.enforcement import reconcile_invoice_enforcement

PAYME_ACCOUNT_FIELD = "invoice_id"
PAYME_TIMEOUT_REASON = 4


@dataclass
class PaymeRpcError(Exception):
    code: int
    messages: Mapping[str, str]
    data: str = ""


def _messages(en: str, ru: str, uz: str) -> dict[str, str]:
    return {"en": en, "ru": ru, "uz": uz}


def _rpc_error(code: int, en: str, ru: str, uz: str, data: str = "") -> PaymeRpcError:
    return PaymeRpcError(code=code, messages=_messages(en, ru, uz), data=data)


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise _rpc_error(-32600, "Invalid request.", "Неверный запрос.", "Noto'g'ri so'rov.", field_name)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise _rpc_error(
            -32600,
            "Invalid request.",
            "Неверный запрос.",
            "Noto'g'ri so'rov.",
            field_name,
        ) from exc
    if parsed <= 0:
        raise _rpc_error(-32600, "Invalid request.", "Неверный запрос.", "Noto'g'ri so'rov.", field_name)
    return parsed


def _provider_id(params: Mapping[str, Any]) -> str:
    provider_transaction_id = str(params.get("id") or "").strip()
    if len(provider_transaction_id) != 24:
        raise _rpc_error(-32600, "Invalid request.", "Неверный запрос.", "Noto'g'ri so'rov.", "id")
    return provider_transaction_id


def _transaction_result(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "create_time": int(row["create_time_ms"]),
        "perform_time": int(row["perform_time_ms"]),
        "cancel_time": int(row["cancel_time_ms"]),
        "transaction": str(row["id"]),
        "state": int(row["state"]),
        "reason": row.get("reason"),
    }


class PaymeMerchant:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        settings: PaymeSettings,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._settings = settings

    def dispatch(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        handlers = {
            "CheckPerformTransaction": self.check_perform_transaction,
            "CreateTransaction": self.create_transaction,
            "PerformTransaction": self.perform_transaction,
            "CancelTransaction": self.cancel_transaction,
            "CheckTransaction": self.check_transaction,
            "GetStatement": self.get_statement,
        }
        handler = handlers.get(str(method or "").strip())
        if handler is None:
            raise _rpc_error(
                -32601,
                "Method not found.",
                "Метод не найден.",
                "Metod topilmadi.",
                str(method or ""),
            )
        return handler(params)

    def _invoice_id(self, params: Mapping[str, Any]) -> int:
        account = params.get("account")
        if not isinstance(account, Mapping):
            raise _rpc_error(
                -31050,
                "Invoice was not found.",
                "Счёт не найден.",
                "Hisob topilmadi.",
                PAYME_ACCOUNT_FIELD,
            )
        try:
            return _positive_int(account.get(PAYME_ACCOUNT_FIELD), PAYME_ACCOUNT_FIELD)
        except PaymeRpcError as exc:
            raise _rpc_error(
                -31050,
                "Invoice was not found.",
                "Счёт не найден.",
                "Hisob topilmadi.",
                PAYME_ACCOUNT_FIELD,
            ) from exc

    def _validate_invoice(
        self,
        conn,
        *,
        invoice_id: int,
        amount_minor: int,
        for_update: bool,
    ):
        row = repository.get_payable_invoice_row(
            conn,
            invoice_id,
            for_update=for_update,
        )
        if not row:
            raise _rpc_error(
                -31050,
                "Invoice was not found.",
                "Счёт не найден.",
                "Hisob topilmadi.",
                PAYME_ACCOUNT_FIELD,
            )
        balance_minor = int(row["total_minor"]) - int(row["paid_minor"])
        if amount_minor != balance_minor:
            raise _rpc_error(
                -31001,
                "Incorrect amount.",
                "Неверная сумма.",
                "Noto'g'ri summa.",
                "amount",
            )
        is_open_invoice = str(row["status"]) in {
            "issued",
            "partially_paid",
            "overdue",
        }
        if row["admission_id"] is not None:
            is_payable = (
                is_open_invoice
                and str(row["contract_status"]) == "accepted"
                and str(row["admission_status"]) == "awaiting_payment"
                and int(row["selected_group_count"]) > 0
                and int(row["selected_group_count"])
                == int(row["available_group_count"])
            )
        else:
            is_payable = (
                is_open_invoice
                and row["student_id"] is not None
                and str(row["student_status"]) == "active"
            )
        if not is_payable:
            raise _rpc_error(
                -31008,
                "The operation cannot be performed.",
                "Операция невозможна.",
                "Amalni bajarib bo'lmaydi.",
            )
        return row

    def check_perform_transaction(self, params: Mapping[str, Any]) -> dict[str, Any]:
        invoice_id = self._invoice_id(params)
        amount_minor = _positive_int(params.get("amount"), "amount")
        with self._unit_of_work_factory.read() as unit_of_work:
            self._validate_invoice(
                unit_of_work.conn,
                invoice_id=invoice_id,
                amount_minor=amount_minor,
                for_update=False,
            )
        return {"allow": True}

    def create_transaction(self, params: Mapping[str, Any]) -> dict[str, Any]:
        provider_transaction_id = _provider_id(params)
        provider_created_at_ms = _positive_int(params.get("time"), "time")
        amount_minor = _positive_int(params.get("amount"), "amount")
        invoice_id = self._invoice_id(params)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            existing = repository.get_transaction_row(
                unit_of_work.conn,
                provider_transaction_id,
                for_update=True,
            )
            if existing:
                if (
                    int(existing["invoice_id"]) != invoice_id
                    or int(existing["amount_minor"]) != amount_minor
                ):
                    raise _rpc_error(
                        -31008,
                        "The operation cannot be performed.",
                        "Операция невозможна.",
                        "Amalni bajarib bo'lmaydi.",
                    )
                result = {
                    "create_time": int(existing["create_time_ms"]),
                    "transaction": str(existing["id"]),
                    "state": int(existing["state"]),
                }
                commit_unit_of_work(unit_of_work)
                return result
            self._validate_invoice(
                unit_of_work.conn,
                invoice_id=invoice_id,
                amount_minor=amount_minor,
                for_update=True,
            )
            pending = repository.find_pending_invoice_transaction_row(
                unit_of_work.conn,
                invoice_id,
            )
            if pending:
                raise _rpc_error(
                    -31008,
                    "Another transaction is pending.",
                    "Другая транзакция ожидает завершения.",
                    "Boshqa tranzaksiya kutilmoqda.",
                )
            create_time_ms = int(time() * 1000)
            row = repository.insert_transaction(
                unit_of_work.conn,
                provider_transaction_id=provider_transaction_id,
                invoice_id=invoice_id,
                provider_created_at_ms=provider_created_at_ms,
                amount_minor=amount_minor,
                create_time_ms=create_time_ms,
            )
            if not row:
                row = repository.get_transaction_row(
                    unit_of_work.conn,
                    provider_transaction_id,
                    for_update=True,
                )
            repository.insert_payme_audit_event(
                unit_of_work.conn,
                event_type="payme_transaction_created",
                transaction_id=int(row["id"]),
                detail={
                    "invoice_id": invoice_id,
                    "amount_minor": amount_minor,
                    "state": int(row["state"]),
                },
            )
            commit_unit_of_work(unit_of_work)
        return {
            "create_time": int(row["create_time_ms"]),
            "transaction": str(row["id"]),
            "state": int(row["state"]),
        }

    def perform_transaction(self, params: Mapping[str, Any]) -> dict[str, Any]:
        provider_transaction_id = _provider_id(params)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            row = repository.get_transaction_row(
                unit_of_work.conn,
                provider_transaction_id,
                for_update=True,
            )
            if not row:
                raise _rpc_error(
                    -31003,
                    "Transaction was not found.",
                    "Транзакция не найдена.",
                    "Tranzaksiya topilmadi.",
                )
            state = int(row["state"])
            if state == 2:
                result = {
                    "transaction": str(row["id"]),
                    "perform_time": int(row["perform_time_ms"]),
                    "state": 2,
                }
                commit_unit_of_work(unit_of_work)
                return result
            if state != 1:
                raise _rpc_error(
                    -31008,
                    "The operation cannot be performed.",
                    "Операция невозможна.",
                    "Amalni bajarib bo'lmaydi.",
                )
            now_ms = int(time() * 1000)
            timeout_ms = self._settings.transaction_timeout_seconds * 1000
            if now_ms - int(row["provider_created_at_ms"]) >= timeout_ms:
                cancelled = repository.cancel_transaction(
                    unit_of_work.conn,
                    provider_transaction_id=provider_transaction_id,
                    state=-1,
                    reason=PAYME_TIMEOUT_REASON,
                    cancel_time_ms=now_ms,
                )
                repository.insert_payme_audit_event(
                    unit_of_work.conn,
                    event_type="payme_transaction_timed_out",
                    transaction_id=int(cancelled["id"]),
                    detail={
                        "invoice_id": int(row["invoice_id"]),
                        "reason": PAYME_TIMEOUT_REASON,
                    },
                )
                commit_unit_of_work(unit_of_work)
                raise _rpc_error(
                    -31008,
                    "The transaction expired.",
                    "Срок транзакции истёк.",
                    "Tranzaksiya muddati tugadi.",
                )
            invoice = self._validate_invoice(
                unit_of_work.conn,
                invoice_id=int(row["invoice_id"]),
                amount_minor=int(row["amount_minor"]),
                for_update=True,
            )
            repository.insert_completed_invoice_payment(
                unit_of_work.conn,
                invoice_id=int(row["invoice_id"]),
                amount_minor=int(row["amount_minor"]),
                provider_transaction_id=provider_transaction_id,
            )
            repository.set_invoice_paid(
                unit_of_work.conn,
                invoice_id=int(row["invoice_id"]),
                amount_minor=int(row["amount_minor"]),
            )
            reconcile_invoice_enforcement(
                unit_of_work.conn,
                invoice_id=int(row["invoice_id"]),
                now=SystemClock().now(),
            )
            performed = repository.perform_transaction(
                unit_of_work.conn,
                provider_transaction_id=provider_transaction_id,
                perform_time_ms=now_ms,
            )
            repository.insert_payme_audit_event(
                unit_of_work.conn,
                event_type="payme_transaction_performed",
                transaction_id=int(performed["id"]),
                detail={
                    "invoice_id": int(row["invoice_id"]),
                    "amount_minor": int(row["amount_minor"]),
                    "state": 2,
                },
            )
            if invoice["admission_id"] is not None:
                activate_paid_admission(
                    unit_of_work.conn,
                    int(invoice["admission_id"]),
                    actor=AdmissionActor(staff_id=None, account_id=None),
                )
            commit_unit_of_work(unit_of_work)
        return {
            "transaction": str(performed["id"]),
            "perform_time": int(performed["perform_time_ms"]),
            "state": 2,
        }

    def cancel_transaction(self, params: Mapping[str, Any]) -> dict[str, Any]:
        provider_transaction_id = _provider_id(params)
        reason = _positive_int(params.get("reason"), "reason")
        with self._unit_of_work_factory.transaction() as unit_of_work:
            row = repository.get_transaction_row(
                unit_of_work.conn,
                provider_transaction_id,
                for_update=True,
            )
            if not row:
                raise _rpc_error(
                    -31003,
                    "Transaction was not found.",
                    "Транзакция не найдена.",
                    "Tranzaksiya topilmadi.",
                )
            state = int(row["state"])
            if state in {-2, -1}:
                result = {
                    "transaction": str(row["id"]),
                    "cancel_time": int(row["cancel_time_ms"]),
                    "state": state,
                }
                commit_unit_of_work(unit_of_work)
                return result
            cancel_time_ms = int(time() * 1000)
            new_state = -2 if state == 2 else -1
            cancelled = repository.cancel_transaction(
                unit_of_work.conn,
                provider_transaction_id=provider_transaction_id,
                state=new_state,
                reason=reason,
                cancel_time_ms=cancel_time_ms,
            )
            repository.insert_payme_audit_event(
                unit_of_work.conn,
                event_type="payme_transaction_cancelled",
                transaction_id=int(cancelled["id"]),
                detail={
                    "invoice_id": int(row["invoice_id"]),
                    "reason": reason,
                    "previous_state": state,
                    "state": new_state,
                },
            )
            if state == 2:
                invoice_id = repository.refund_invoice_payment(
                    unit_of_work.conn,
                    provider_transaction_id=provider_transaction_id,
                    reason=reason,
                )
                if invoice_id:
                    reconcile_invoice_enforcement(
                        unit_of_work.conn,
                        invoice_id=invoice_id,
                        now=SystemClock().now(),
                    )
                    invoice = repository.get_payable_invoice_row(
                        unit_of_work.conn,
                        invoice_id,
                        for_update=True,
                    )
                    if invoice["admission_id"] is not None:
                        repository.set_admission_after_refund(
                            unit_of_work.conn,
                            admission_id=int(invoice["admission_id"]),
                        )
            commit_unit_of_work(unit_of_work)
        return {
            "transaction": str(cancelled["id"]),
            "cancel_time": int(cancelled["cancel_time_ms"]),
            "state": int(cancelled["state"]),
        }

    def check_transaction(self, params: Mapping[str, Any]) -> dict[str, Any]:
        provider_transaction_id = _provider_id(params)
        with self._unit_of_work_factory.read() as unit_of_work:
            row = repository.get_transaction_row(
                unit_of_work.conn,
                provider_transaction_id,
            )
        if not row:
            raise _rpc_error(
                -31003,
                "Transaction was not found.",
                "Транзакция не найдена.",
                "Tranzaksiya topilmadi.",
            )
        return _transaction_result(row)

    def get_statement(self, params: Mapping[str, Any]) -> dict[str, Any]:
        from_ms = _positive_int(params.get("from"), "from")
        to_ms = _positive_int(params.get("to"), "to")
        if from_ms > to_ms:
            raise _rpc_error(
                -32600,
                "Invalid statement period.",
                "Неверный период.",
                "Noto'g'ri davr.",
                "from",
            )
        with self._unit_of_work_factory.read() as unit_of_work:
            rows = repository.list_statement_rows(
                unit_of_work.conn,
                from_ms=from_ms,
                to_ms=to_ms,
            )
        return {
            "transactions": [
                {
                    "id": str(row["provider_transaction_id"]),
                    "time": int(row["provider_created_at_ms"]),
                    "amount": int(row["amount_minor"]),
                    "account": {PAYME_ACCOUNT_FIELD: int(row["invoice_id"])},
                    **_transaction_result(row),
                }
                for row in rows
            ]
        }


__all__ = [
    "PAYME_ACCOUNT_FIELD",
    "PAYME_TIMEOUT_REASON",
    "PaymeMerchant",
    "PaymeRpcError",
]
