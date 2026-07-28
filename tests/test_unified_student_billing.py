"""Unified current-student and admission billing regressions."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pytest

from backend.core.runtime.config import PaymeSettings
from backend.modules.domains.admissions.domain_types import (
    InvoiceStatus as AdmissionInvoiceStatus,
)
from backend.modules.domains.finance.domain_types import (
    BillingJobTopic,
    InvoiceStatus,
)
from backend.modules.domains.finance.integrations.payme import repository as payme_repository
from backend.modules.domains.finance.integrations.payme.service import (
    PaymeMerchant,
    PaymeRpcError,
)
from backend.modules.domains.finance.policies import BillingError, major_to_minor
from backend.modules.domains.finance.schemas import RecordManualInvoicePaymentCommand
from tests.test_admissions_and_payme import _ReadFactory


def _merchant() -> PaymeMerchant:
    return PaymeMerchant(
        unit_of_work_factory=_ReadFactory(),  # type: ignore[arg-type]
        settings=PaymeSettings(
            environment="test",
            merchant_id="merchant",
            login="Paycom",
            key="test-key",
            checkout_url="https://checkout.test",
            callback_base_url="https://portal.test",
            request_body_max_bytes=64 * 1024,
            transaction_timeout_seconds=43_200,
        ),
    )


def test_admissions_and_finance_share_one_invoice_vocabulary():
    assert AdmissionInvoiceStatus is InvoiceStatus
    assert InvoiceStatus.OVERDUE.value == "overdue"
    assert BillingJobTopic.GENERATE_INVOICES.value == "finance.generate_invoices"


@pytest.mark.parametrize(
    ("major", "minor"),
    [
        ("1", 100),
        ("0.01", 1),
        ("2000000", 200_000_000),
        ("12.345", 1235),
    ],
)
def test_uzs_major_amounts_convert_to_exact_minor_units(major: str, minor: int):
    assert major_to_minor(major) == minor


def test_new_amounts_must_be_positive():
    with pytest.raises(BillingError):
        major_to_minor("0")
    with pytest.raises(BillingError):
        major_to_minor("not-money")


def test_manual_settlement_timestamp_must_include_timezone():
    with pytest.raises(ValueError, match="timezone"):
        RecordManualInvoicePaymentCommand(
            amount_minor=100,
            method="cash",
            paid_at=datetime(2026, 7, 28, 12),
            reference="receipt",
            reason="Recorded at school.",
            expected_version=1,
        )


def test_payme_accepts_an_open_invoice_for_an_active_current_student(monkeypatch):
    monkeypatch.setattr(
        payme_repository,
        "get_payable_invoice_row",
        lambda *_args, **_kwargs: {
            "id": 51,
            "admission_id": None,
            "student_id": 315,
            "student_status": "active",
            "total_minor": 200_000_000,
            "paid_minor": 0,
            "status": "issued",
        },
    )

    assert _merchant().check_perform_transaction(
        {
            "amount": 200_000_000,
            "account": {"invoice_id": 51},
        }
    ) == {"allow": True}


def test_payme_rejects_a_current_student_invoice_after_archival(monkeypatch):
    monkeypatch.setattr(
        payme_repository,
        "get_payable_invoice_row",
        lambda *_args, **_kwargs: {
            "id": 51,
            "admission_id": None,
            "student_id": 315,
            "student_status": "archived",
            "total_minor": 200_000_000,
            "paid_minor": 0,
            "status": "issued",
        },
    )

    with pytest.raises(PaymeRpcError) as caught:
        _merchant().check_perform_transaction(
            {
                "amount": 200_000_000,
                "account": {"invoice_id": 51},
            }
        )
    assert caught.value.code == -31008


def test_unified_billing_migration_is_additive_and_preserves_legacy_rows():
    source = Path(
        "database/alembic/versions/0047_unified_student_billing.py"
    ).read_text(encoding="utf-8")
    upgrade = source.split("def downgrade()", 1)[0]

    assert "DELETE FROM" not in upgrade.upper()
    assert "TRUNCATE " not in upgrade.upper()
    assert "legacy_payment_id" in upgrade
    assert "origin" in upgrade
    assert "student_billing_profiles" in upgrade
    assert "student_billing_items" in upgrade
    assert "INSERT INTO msi_v2.invoices" in upgrade
    assert "'legacy_migration'" in upgrade
    assert "'finance.generate_invoices'" in upgrade


def test_legacy_payment_mutation_no_longer_exposes_hard_delete():
    repository_source = Path(
        "backend/modules/domains/finance/repository.py"
    ).read_text(encoding="utf-8")
    service_source = Path(
        "backend/modules/domains/finance/service.py"
    ).read_text(encoding="utf-8")

    assert "delete_student_payment_row" not in repository_source
    assert "delete_student_payment" not in service_source
    assert "DELETE FROM msi_v2.payments" not in repository_source


def test_parent_payme_checkout_is_registered_without_exposing_a_merchant_key():
    source = Path(
        "backend/modules/people/parent/workspace/api.py"
    ).read_text(encoding="utf-8")

    assert '"/payments/{invoice_id}/checkout"' in source
    assert "settings.merchant_id" in source
    assert "settings.key" not in source


def test_current_student_payment_ui_uses_canonical_invoice_commands():
    source = Path(
        "frontend/src/features/customer-support/students/StudentsPage.tsx"
    ).read_text(encoding="utf-8")

    assert "/payments/students/${detail.profile.id}/" in source
    assert "paid-invoices" in source
    assert "/students/${detail.profile.id}/payments" not in source
    assert "Mark unpaid" not in source
