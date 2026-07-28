"""Admission lifecycle and Payme Merchant boundary tests."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.core.runtime.config import PaymeSettings
from backend.core.runtime.observability import redact_sensitive_path
from backend.modules.domains.admissions import contracts as admission_contracts
from backend.modules.domains.admissions import repository as admission_repository
from backend.modules.domains.admissions.domain_types import (
    AdmissionStatus,
    ContractStatus,
    InvoiceStatus,
)
from backend.modules.domains.admissions.policies import (
    AdmissionError,
    ensure_contract_can_be_reviewed,
    ensure_invoice_can_accept_payment,
    ensure_invoice_can_be_issued,
    invoice_status_for_balance,
)
from backend.modules.domains.finance.integrations.payme import repository
from backend.modules.domains.finance.integrations.payme.service import (
    PaymeMerchant,
    PaymeRpcError,
)
from backend.platform.storage.private_documents import _has_expected_signature


class _ReadUnitOfWork:
    conn = object()


class _ReadFactory:
    @contextmanager
    def read(self):
        yield _ReadUnitOfWork()


def _settings() -> PaymeSettings:
    return PaymeSettings(
        environment="test",
        merchant_id="test-merchant",
        login="Paycom",
        key="not-a-real-key",
        checkout_url="https://checkout.test",
        callback_base_url="https://portal.test",
        request_body_max_bytes=64 * 1024,
        transaction_timeout_seconds=43_200,
    )


def _merchant() -> PaymeMerchant:
    return PaymeMerchant(
        unit_of_work_factory=_ReadFactory(),  # type: ignore[arg-type]
        settings=_settings(),
    )


def _payable_invoice(**overrides):
    row = {
        "id": 41,
        "admission_id": 7,
        "total_minor": 250_000_00,
        "paid_minor": 50_000_00,
        "status": "partially_paid",
        "contract_status": "accepted",
        "admission_status": "awaiting_payment",
        "selected_group_count": 2,
        "available_group_count": 2,
    }
    row.update(overrides)
    return row


def test_admission_and_invoice_states_use_stable_wire_values():
    assert AdmissionStatus.AWAITING_PAYMENT.value == "awaiting_payment"
    assert ContractStatus.SUPERSEDED.value == "superseded"
    assert InvoiceStatus.PARTIALLY_PAID.value == "partially_paid"


def test_invoice_balance_state_is_deterministic():
    assert invoice_status_for_balance(total_minor=100, paid_minor=0) is InvoiceStatus.ISSUED
    assert (
        invoice_status_for_balance(total_minor=100, paid_minor=40)
        is InvoiceStatus.PARTIALLY_PAID
    )
    assert invoice_status_for_balance(total_minor=100, paid_minor=100) is InvoiceStatus.PAID


def test_contract_and_payment_policies_reject_invalid_lifecycle_steps():
    with pytest.raises(AdmissionError, match="submitted"):
        ensure_contract_can_be_reviewed(ContractStatus.SENT)
    with pytest.raises(AdmissionError, match="Accept"):
        ensure_invoice_can_be_issued(AdmissionStatus.CONTRACT_SENT, ContractStatus.SENT)
    with pytest.raises(AdmissionError, match="cannot accept"):
        ensure_invoice_can_accept_payment(InvoiceStatus.PAID)


def test_payme_missing_or_invalid_invoice_account_uses_invoice_error():
    merchant = _merchant()

    for params in ({}, {"account": {}}, {"account": {"invoice_id": "not-an-id"}}):
        with pytest.raises(PaymeRpcError) as caught:
            merchant.check_perform_transaction({"amount": 1, **params})
        assert caught.value.code == -31050
        assert caught.value.data == "invoice_id"


def test_payme_requires_official_transaction_id_shape():
    with pytest.raises(PaymeRpcError) as caught:
        _merchant().check_transaction({"id": "short"})

    assert caught.value.code == -32600
    assert caught.value.data == "id"


def test_payme_checks_exact_remaining_balance(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_payable_invoice_row",
        lambda *_args, **_kwargs: _payable_invoice(),
    )
    merchant = _merchant()

    assert merchant.check_perform_transaction(
        {
            "amount": 200_000_00,
            "account": {"invoice_id": 41},
        }
    ) == {"allow": True}
    with pytest.raises(PaymeRpcError) as caught:
        merchant.check_perform_transaction(
            {
                "amount": 250_000_00,
                "account": {"invoice_id": 41},
            }
        )
    assert caught.value.code == -31001
    assert caught.value.data == "amount"


def test_payme_rejects_invoice_when_contract_or_group_reservation_is_invalid(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_payable_invoice_row",
        lambda *_args, **_kwargs: _payable_invoice(contract_status="submitted"),
    )

    with pytest.raises(PaymeRpcError) as caught:
        _merchant().check_perform_transaction(
            {
                "amount": 200_000_00,
                "account": {"invoice_id": 41},
            }
        )

    assert caught.value.code == -31008


def test_manual_settlement_is_blocked_while_payme_is_pending(monkeypatch):
    monkeypatch.setattr(
        admission_repository,
        "get_invoice_row",
        lambda *_args, **_kwargs: {
            "id": 41,
            "admission_id": 7,
            "version": 3,
            "status": "issued",
            "invoice_kind": "first",
            "total_minor": 200_000_00,
            "paid_minor": 0,
        },
    )
    monkeypatch.setattr(
        admission_repository,
        "get_admission_row",
        lambda *_args, **_kwargs: {"id": 7, "school_id": 2},
    )
    monkeypatch.setattr(
        admission_repository,
        "has_pending_payme_transaction",
        lambda *_args, **_kwargs: True,
    )

    with pytest.raises(AdmissionError) as caught:
        admission_contracts.record_manual_payment(
            object(),  # type: ignore[arg-type]
            41,
            amount_minor=200_000_00,
            method="cash",
            paid_at=datetime.now(UTC),
            reference="receipt-1",
            reason="Paid at school",
            expected_version=3,
            actor=admission_contracts.AdmissionActor(staff_id=8, account_id=9),
            scope=admission_contracts.AdmissionSchoolScope(
                school_ids=frozenset({2}),
                all_schools=False,
            ),
        )

    assert caught.value.code == "payme_transaction_pending"
    assert caught.value.status_code == 409


def test_payme_key_is_redacted_from_settings_repr():
    rendered = repr(_settings())

    assert "not-a-real-key" not in rendered
    assert "key=" not in rendered


def test_admission_bearer_token_is_redacted_from_observability_paths():
    token = "example-admission-bearer-token"

    assert redact_sensitive_path(f"/admissions/{token}") == "/admissions/[redacted]"
    assert (
        redact_sensitive_path(f"/api/v1/public/admissions/{token}/contract")
        == "/api/v1/public/admissions/[redacted]/contract"
    )


def test_private_contract_documents_require_matching_file_signatures():
    assert _has_expected_signature(".pdf", b"%PDF-1.7\n")
    assert _has_expected_signature(".docx", b"PK\x03\x04archive")
    assert _has_expected_signature(".png", b"\x89PNG\r\n\x1a\ncontent")
    assert not _has_expected_signature(".pdf", b"<html>not a pdf")
    assert not _has_expected_signature(".docx", b"%PDF-1.7")


def test_admission_migration_is_additive_and_has_required_payme_constraints():
    source = Path(
        "database/alembic/versions/0046_admission_contracts_invoices_payme.py"
    ).read_text(encoding="utf-8")
    upgrade_source = source.split("def downgrade()", 1)[0]

    assert "DROP TABLE" not in upgrade_source.upper()
    assert "msi_v2.payme_transactions" in source
    assert "idx_invoices_admission_period_kind" in source
    assert "provider_transaction_id" in source
    assert "invoice_payments_amount_check" in source
