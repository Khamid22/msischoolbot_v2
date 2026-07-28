"""Customer Support and public admission commands."""

from __future__ import annotations

from datetime import date
from typing import Any

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability, Domain
from backend.core.runtime.config import StorageSettings
from backend.core.unit_of_work import UnitOfWorkFactory, commit_unit_of_work
from backend.modules.domains.admissions import contracts
from backend.modules.people.customer_support.policies import require_capability
from backend.modules.people.customer_support.scope import CustomerSupportScopeProvider
from backend.platform.storage.private_documents import (
    build_private_document_url,
    upload_private_document,
)

ADMISSION_DOCUMENT_NAMESPACE = "admissions"

AdmissionDetail = contracts.AdmissionDetail
AdmissionGroupOption = contracts.AdmissionGroupOption
AdmissionLink = contracts.AdmissionLink
AdmissionPage = contracts.AdmissionPage
AddPaidInvoiceCommand = contracts.AddPaidInvoiceCommand
CancelAdmissionCommand = contracts.CancelAdmissionCommand
ContractUploadMetadata = contracts.ContractUploadMetadata
CreateAdmissionCommand = contracts.CreateAdmissionCommand
InvoiceKind = contracts.InvoiceKind
InvoiceQueuePage = contracts.InvoiceQueuePage
ManualPaymentCommand = contracts.ManualPaymentCommand
ReverseManualPaymentCommand = contracts.ReverseManualPaymentCommand
ReviewContractCommand = contracts.ReviewContractCommand
UpdateAdmissionCommand = contracts.UpdateAdmissionCommand
VoidInvoiceCommand = contracts.VoidInvoiceCommand


def _actor(actor: ActorContext) -> contracts.AdmissionActor:
    return contracts.AdmissionActor(
        staff_id=actor.staff_id,
        account_id=actor.account_id,
    )


def _scope(actor: ActorContext) -> contracts.AdmissionSchoolScope:
    return contracts.AdmissionSchoolScope(
        school_ids=actor.school_scope.allowed_school_ids,
        all_schools=actor.school_scope.all_schools,
    )


class CustomerSupportAdmissions:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        scope_resolver: CustomerSupportScopeProvider,
        storage_settings: StorageSettings,
        public_base_url: str,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._scope_resolver = scope_resolver
        self._storage_settings = storage_settings
        self._public_base_url = public_base_url.rstrip("/")

    def _scoped_actor(self, actor: ActorContext) -> ActorContext:
        require_capability(actor, Capability.MANAGE_ADMISSIONS)
        if not actor.can_use_domain(Domain.ADMISSIONS):
            raise PermissionError("Admissions are not enabled for this person module.")
        return self._scope_resolver.resolve(actor)

    def list_group_options(self, actor: ActorContext) -> list[AdmissionGroupOption]:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return contracts.list_group_options(unit_of_work.conn, _scope(scoped_actor))

    def list_admissions(
        self,
        actor: ActorContext,
        *,
        query: str = "",
        status: str = "all",
        limit: int = 50,
    ) -> AdmissionPage:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return contracts.list_admissions(
                unit_of_work.conn,
                scope=_scope(scoped_actor),
                query=query,
                status=status,
                limit=limit,
            )

    def get_admission(self, actor: ActorContext, admission_id: int) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )

    def update_admission(
        self,
        actor: ActorContext,
        admission_id: int,
        command: UpdateAdmissionCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            contracts.update_admission(
                unit_of_work.conn,
                admission_id,
                command,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def list_invoices(
        self,
        actor: ActorContext,
        *,
        query: str = "",
        status: str = "all",
        limit: int = 50,
    ) -> InvoiceQueuePage:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            return contracts.list_invoices(
                unit_of_work.conn,
                scope=_scope(scoped_actor),
                query=query,
                status=status,
                limit=limit,
            )

    def create_admission(
        self,
        actor: ActorContext,
        command: CreateAdmissionCommand,
    ) -> tuple[AdmissionDetail, AdmissionLink, str]:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            admission_id = contracts.create_admission(
                unit_of_work.conn,
                command,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            link = contracts.issue_access_link(
                unit_of_work.conn,
                admission_id,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
                replace_active=False,
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail, link, self._admission_url(link.access_token)

    def upload_contract(
        self,
        actor: ActorContext,
        admission_id: int,
        uploaded_file: Any,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        self.get_admission(scoped_actor, admission_id)
        metadata, error = upload_private_document(
            uploaded_file,
            namespace=ADMISSION_DOCUMENT_NAMESPACE,
            record_id=admission_id,
            document_type="school-contract",
            max_bytes=min(self._storage_settings.upload_max_bytes, 20 * 1024 * 1024),
        )
        if error:
            raise contracts.AdmissionError(error)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            contracts.add_contract(
                unit_of_work.conn,
                admission_id,
                ContractUploadMetadata.model_validate(metadata),
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def send_contract(
        self,
        actor: ActorContext,
        admission_id: int,
    ) -> tuple[AdmissionDetail, str]:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            contracts.send_contract(
                unit_of_work.conn,
                admission_id,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            link = contracts.issue_access_link(
                unit_of_work.conn,
                admission_id,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail, self._admission_url(link.access_token)

    def review_contract(
        self,
        actor: ActorContext,
        admission_id: int,
        command: ReviewContractCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            existing_detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
                for_update=True,
            )
            contracts.review_contract(
                unit_of_work.conn,
                admission_id,
                accepted=command.accepted,
                reason=command.reason,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            if command.accepted:
                first_due_date: date = existing_detail.first_due_date
                contracts.issue_invoice(
                    unit_of_work.conn,
                    admission_id,
                    due_date=first_due_date,
                    billing_period=first_due_date.replace(day=1),
                    invoice_kind=InvoiceKind.FIRST,
                    actor=_actor(scoped_actor),
                    scope=_scope(scoped_actor),
                )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def record_manual_payment(
        self,
        actor: ActorContext,
        invoice_id: int,
        command: ManualPaymentCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            payment = contracts.record_manual_payment(
                unit_of_work.conn,
                invoice_id,
                amount_minor=command.amount_minor,
                method=command.method.value,
                paid_at=command.paid_at,
                reference=command.reference,
                reason=command.reason,
                expected_version=command.expected_version,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                payment.admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def add_paid_invoice(
        self,
        actor: ActorContext,
        admission_id: int,
        command: AddPaidInvoiceCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            invoice_id = contracts.issue_invoice(
                unit_of_work.conn,
                admission_id,
                due_date=command.due_date,
                billing_period=command.billing_period,
                invoice_kind=InvoiceKind.FIRST,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            invoice = next(
                item for item in detail.invoices if item.invoice_id == invoice_id
            )
            if invoice.balance_minor > 0:
                contracts.record_manual_payment(
                    unit_of_work.conn,
                    invoice_id,
                    amount_minor=invoice.balance_minor,
                    method=command.method.value,
                    paid_at=command.paid_at,
                    reference=command.reference,
                    reason=command.reason,
                    expected_version=invoice.version,
                    actor=_actor(scoped_actor),
                    scope=_scope(scoped_actor),
                )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def reverse_manual_payment(
        self,
        actor: ActorContext,
        payment_id: int,
        command: ReverseManualPaymentCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            admission_id = contracts.reverse_manual_payment(
                unit_of_work.conn,
                payment_id,
                expected_invoice_version=command.expected_invoice_version,
                reason=command.reason,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def void_invoice(
        self,
        actor: ActorContext,
        invoice_id: int,
        command: VoidInvoiceCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            admission_id = contracts.void_invoice(
                unit_of_work.conn,
                invoice_id,
                expected_version=command.expected_version,
                reason=command.reason,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def cancel_admission(
        self,
        actor: ActorContext,
        admission_id: int,
        command: CancelAdmissionCommand,
    ) -> AdmissionDetail:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.transaction() as unit_of_work:
            contracts.cancel_admission(
                unit_of_work.conn,
                admission_id,
                expected_version=command.expected_version,
                reason=command.reason,
                actor=_actor(scoped_actor),
                scope=_scope(scoped_actor),
            )
            detail = contracts.get_admission(
                unit_of_work.conn,
                admission_id,
                scope=_scope(scoped_actor),
            )
            commit_unit_of_work(unit_of_work)
        return detail

    def contract_download_url(
        self,
        actor: ActorContext,
        admission_id: int,
        *,
        signed: bool,
    ) -> str:
        scoped_actor = self._scoped_actor(actor)
        with self._unit_of_work_factory.read() as unit_of_work:
            document = contracts.get_staff_contract_document(
                unit_of_work.conn,
                admission_id,
                signed=signed,
                scope=_scope(scoped_actor),
            )
        url = build_private_document_url(
            document.object_key,
            namespace=ADMISSION_DOCUMENT_NAMESPACE,
            original_file_name=document.original_file_name,
            download=True,
        )
        if not url:
            raise contracts.AdmissionError(
                "The contract document could not be opened."
            )
        return url

    def _admission_url(self, access_token: str) -> str:
        path = f"/admissions/{access_token}"
        return f"{self._public_base_url}{path}" if self._public_base_url else path


__all__ = [
    "ADMISSION_DOCUMENT_NAMESPACE",
    "CustomerSupportAdmissions",
]
