"""Payme runtime configuration safety tests."""

from __future__ import annotations

from backend.core.runtime.config import _payme_settings


def _set_test_merchant(monkeypatch) -> None:
    monkeypatch.setenv("PAYME_ENVIRONMENT", "test")
    monkeypatch.setenv("PAYME_MERCHANT_ID", "sandbox-merchant")
    monkeypatch.setenv("PAYME_MERCHANT_LOGIN", "Paycom")
    monkeypatch.setenv("PAYME_MERCHANT_KEY", "sandbox-key")


def test_test_payme_is_disabled_in_production_by_default(monkeypatch):
    _set_test_merchant(monkeypatch)
    monkeypatch.delenv("PAYME_ALLOW_TEST_IN_PRODUCTION", raising=False)

    settings = _payme_settings("production")

    assert settings.environment == "test"
    assert not settings.is_configured


def test_test_payme_requires_explicit_production_override(monkeypatch):
    _set_test_merchant(monkeypatch)
    monkeypatch.setenv("PAYME_ALLOW_TEST_IN_PRODUCTION", "true")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://portal.example")

    settings = _payme_settings("production")

    assert settings.is_configured
    assert settings.merchant_id == "sandbox-merchant"
    assert settings.login == "Paycom"
    assert settings.key == "sandbox-key"
    assert settings.checkout_url == "https://test.paycom.uz/"
    assert settings.callback_base_url == "https://portal.example"
