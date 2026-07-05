import pytest


FALSE_VALUES = [None, "", "0", "false", "no", "off"]
TRUE_VALUES = ["1", "true", "yes", "on"]


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("ACCOUNT_AUTH_V2_ENABLED", raising=False)
        return
    monkeypatch.setenv("ACCOUNT_AUTH_V2_ENABLED", value)


def test_account_auth_v2_enabled_new_import_path_works(monkeypatch):
    from backend.core.config import account_auth_v2_enabled

    monkeypatch.setenv("ACCOUNT_AUTH_V2_ENABLED", "1")

    assert account_auth_v2_enabled() is True


def test_account_auth_v2_enabled_old_import_path_still_works(monkeypatch):
    from backend.identity.account_auth_v2 import account_auth_v2_enabled

    monkeypatch.setenv("ACCOUNT_AUTH_V2_ENABLED", "1")

    assert account_auth_v2_enabled() is True


@pytest.mark.parametrize("value", FALSE_VALUES)
def test_account_auth_v2_enabled_false_values_match(monkeypatch, value):
    from backend.core.config import account_auth_v2_enabled as new_path_enabled
    from backend.identity.account_auth_v2 import account_auth_v2_enabled as old_path_enabled

    _set_flag(monkeypatch, value)

    assert new_path_enabled() is False
    assert old_path_enabled() is False


@pytest.mark.parametrize("value", TRUE_VALUES)
def test_account_auth_v2_enabled_true_values_match(monkeypatch, value):
    from backend.core.config import account_auth_v2_enabled as new_path_enabled
    from backend.identity.account_auth_v2 import account_auth_v2_enabled as old_path_enabled

    _set_flag(monkeypatch, value)

    assert new_path_enabled() is True
    assert old_path_enabled() is True

