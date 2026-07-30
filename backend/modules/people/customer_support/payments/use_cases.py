"""Customer Support orchestration over typed Finance contracts."""

from __future__ import annotations

from datetime import date

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability, Domain
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.finance import contracts as finance_contracts
from backend.modules.domains.finance.contracts import (
    AddPaidStudentInvoiceCommand,
    BillingAccountDetail,
    BillingAccountPage,
    BillingAccountType,
    BillingActor,
    BillingAutomationStatus,
    BillingProfileResult,
    BillingSchoolScope,
    ConfigureBillingProfileCommand,
    InvoiceDetail,
    InvoicePage,
    IssueStudentInvoiceCommand,
    RecordManualInvoicePaymentCommand,
    ReverseInvoicePaymentCommand,
    VoidStudentInvoiceCommand,
)
from backend.modules.people.customer_support.policies import require_capability
from backend.modules.people.customer_support.scope import CustomerSupportScopeProvider


def _scope(actor: ActorContext) -> BillingSchoolScope:
    return BillingSchoolScope(
        school_ids=actor.school_scope.allowed_school_ids,
        all_schools=actor.school_scope.all_schools,
    )


def _billing_actor(actor: ActorContext) -> BillingActor:
    return BillingActor(staff_id=actor.staff_id, account_id=actor.account_id)


class CustomerSupportPayments:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        scope_resolver: CustomerSupportScopeProvider,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._scope_resolver = scope_resolver

    def _scoped_actor(self, actor: ActorContext) -> ActorContext:
        require_capability(actor, Capability.MANAGE_PAYMENTS)
        if not actor.can_use_domain(Domain.FINANCE):
            raise PermissionError("Finance is not enabled for this person module.")
        return self._scope_resolver.resolve(actor)

    def list_invoices(
        self,
        actor: ActorContext,
        *,
        query: str = "",
        status: str = "all",
        origin: str = "all",
        enforcement: str = "all",
        school_id: int | None = None,
        billing_period: date | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> InvoicePage:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return finance_contracts.list_invoices(
                unit_of_work.conn,
                scope=_scope(scoped_actor),
                query=query,
                status=status,
                origin=origin,
                enforcement=enforcement,
                school_id=school_id,
                billing_period=billing_period,
                cursor=cursor,
                limit=limit,
            )

    def list_billing_accounts(
        self,
        actor: ActorContext,
        *,
        query: str = "",
        school_id: int | None = None,
        account_type: str = "all",
        schedule_status: str = "all",
        attention: str = "all",
        access: str = "all",
        cursor: str | None = None,
        limit: int = 25,
    ) -> BillingAccountPage:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return finance_contracts.list_billing_accounts(
                unit_of_work.conn,
                scope=_scope(scoped_actor),
                query=query,
                school_id=school_id,
                account_type=account_type,
                schedule_status=schedule_status,
                attention=attention,
                access=access,
                cursor=cursor,
                limit=limit,
            )

    def get_billing_account(
        self,
        actor: ActorContext,
        *,
        account_type: BillingAccountType,
        account_id: int,
    ) -> BillingAccountDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return finance_contracts.get_billing_account(
                unit_of_work.conn,
                scope=_scope(scoped_actor),
                account_type=account_type,
                account_id=account_id,
            )

    def get_invoice(self, actor: ActorContext, invoice_id: int) -> InvoiceDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return finance_contracts.get_invoice(
                unit_of_work.conn,
                invoice_id,
                scope=_scope(scoped_actor),
            )

    def get_automation_status(
        self,
        actor: ActorContext,
    ) -> BillingAutomationStatus:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return finance_contracts.get_billing_automation_status(
                unit_of_work.conn,
                scope=_scope(scoped_actor),
            )

    def issue_invoice(
        self,
        actor: ActorContext,
        command: IssueStudentInvoiceCommand,
    ) -> InvoiceDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            result = finance_contracts.issue_student_invoice(
                unit_of_work.conn,
                command,
                actor=_billing_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return result

    def add_paid_invoice(
        self,
        actor: ActorContext,
        command: AddPaidStudentInvoiceCommand,
    ) -> InvoiceDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            result = finance_contracts.add_paid_student_invoice(
                unit_of_work.conn,
                command,
                actor=_billing_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return result

    def record_manual_payment(
        self,
        actor: ActorContext,
        invoice_id: int,
        command: RecordManualInvoicePaymentCommand,
    ) -> InvoiceDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            result = finance_contracts.record_manual_invoice_payment(
                unit_of_work.conn,
                invoice_id,
                command,
                actor=_billing_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return result

    def reverse_payment(
        self,
        actor: ActorContext,
        payment_id: int,
        command: ReverseInvoicePaymentCommand,
    ) -> InvoiceDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            result = finance_contracts.reverse_invoice_payment(
                unit_of_work.conn,
                payment_id,
                command,
                actor=_billing_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return result

    def void_invoice(
        self,
        actor: ActorContext,
        invoice_id: int,
        command: VoidStudentInvoiceCommand,
    ) -> InvoiceDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            result = finance_contracts.void_student_invoice(
                unit_of_work.conn,
                invoice_id,
                command,
                actor=_billing_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return result

    def get_billing_profile(
        self,
        actor: ActorContext,
        student_id: int,
    ) -> BillingProfileResult | None:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return finance_contracts.get_billing_profile(
                unit_of_work.conn,
                student_id=student_id,
                scope=_scope(scoped_actor),
            )

    def configure_billing_profile(
        self,
        actor: ActorContext,
        command: ConfigureBillingProfileCommand,
    ) -> BillingProfileResult:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            result = finance_contracts.configure_billing_profile(
                unit_of_work.conn,
                command,
                actor=_billing_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return result


__all__ = ["CustomerSupportPayments"]
