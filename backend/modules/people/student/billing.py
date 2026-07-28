"""Student-owned billing queries backed by the Finance domain contract."""

from __future__ import annotations

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability, Role
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.finance.contracts import (
    BillingAccessStatus,
    PaymentRecord,
    get_account_billing_access,
    list_student_account_payment_records,
    student_invoice_checkout_data,
)


class StudentBillingAccessError(PermissionError):
    pass


def _student_identity(actor: ActorContext) -> tuple[int, int]:
    if actor.role is not Role.STUDENT:
        raise StudentBillingAccessError("Student access is required.")
    if Capability.VIEW_PAYMENTS not in actor.capabilities:
        raise StudentBillingAccessError("Payment access is not available.")
    if actor.account_id is None or actor.student_id is None:
        raise StudentBillingAccessError("Student account was not found.")
    return actor.account_id, actor.student_id


class StudentBillingQueries:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def get_access_status(self, actor: ActorContext) -> BillingAccessStatus:
        account_id, _ = _student_identity(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return get_account_billing_access(
                unit_of_work.conn,
                account_id=account_id,
            )

    def list_payments(self, actor: ActorContext) -> tuple[PaymentRecord, ...]:
        _, student_id = _student_identity(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return list_student_account_payment_records(
                unit_of_work.conn,
                student_id=student_id,
            )

    def get_invoice_checkout(
        self,
        actor: ActorContext,
        *,
        invoice_id: int,
    ) -> tuple[int, str]:
        _, student_id = _student_identity(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return student_invoice_checkout_data(
                unit_of_work.conn,
                student_id=student_id,
                invoice_id=invoice_id,
            )


__all__ = [
    "StudentBillingAccessError",
    "StudentBillingQueries",
]
