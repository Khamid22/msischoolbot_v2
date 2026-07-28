"""Admission lifecycle and payment invariants."""

from backend.modules.domains.admissions.domain_types import (
    AdmissionStatus,
    ContractStatus,
    InvoiceStatus,
)

ADMISSION_TOKEN_RATE_LIMIT = 120
ADMISSION_TOKEN_RATE_WINDOW_SECONDS = 60


class AdmissionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "admission_error",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def ensure_contract_can_be_sent(admission_status: AdmissionStatus) -> None:
    if admission_status not in {
        AdmissionStatus.DRAFT,
        AdmissionStatus.CONTRACT_SENT,
        AdmissionStatus.CONTRACT_SUBMITTED,
    }:
        raise AdmissionError("The contract cannot be sent in the current admission state.")


def ensure_contract_can_be_submitted(contract_status: ContractStatus) -> None:
    if contract_status not in {ContractStatus.SENT, ContractStatus.REJECTED}:
        raise AdmissionError("The signed contract cannot be submitted in its current state.")


def ensure_contract_can_be_reviewed(contract_status: ContractStatus) -> None:
    if contract_status is not ContractStatus.SUBMITTED:
        raise AdmissionError("Only a submitted contract can be reviewed.")


def ensure_invoice_can_be_issued(
    admission_status: AdmissionStatus,
    contract_status: ContractStatus | None,
) -> None:
    if contract_status is not ContractStatus.ACCEPTED:
        raise AdmissionError("Accept the signed contract before issuing an invoice.")
    if admission_status not in {
        AdmissionStatus.CONTRACT_SUBMITTED,
        AdmissionStatus.AWAITING_PAYMENT,
        AdmissionStatus.ACTIVE,
    }:
        raise AdmissionError("An invoice cannot be issued in the current admission state.")


def ensure_invoice_can_accept_payment(invoice_status: InvoiceStatus) -> None:
    if invoice_status not in {
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    }:
        raise AdmissionError("This invoice cannot accept a payment.")


def invoice_status_for_balance(*, total_minor: int, paid_minor: int) -> InvoiceStatus:
    if paid_minor <= 0:
        return InvoiceStatus.ISSUED
    if paid_minor < total_minor:
        return InvoiceStatus.PARTIALLY_PAID
    return InvoiceStatus.PAID


__all__ = [
    "ADMISSION_TOKEN_RATE_LIMIT",
    "ADMISSION_TOKEN_RATE_WINDOW_SECONDS",
    "AdmissionError",
    "ensure_contract_can_be_reviewed",
    "ensure_contract_can_be_sent",
    "ensure_contract_can_be_submitted",
    "ensure_invoice_can_accept_payment",
    "ensure_invoice_can_be_issued",
    "invoice_status_for_balance",
]
