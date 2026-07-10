def test_account_auth_flag_has_been_removed_from_core_config():
    import backend.core.config as config

    assert "account_auth_enabled" not in config.__all__
    assert not hasattr(config, "account_auth_enabled")


def test_core_config_owns_runtime_settings_and_root_config_is_wrapper():
    from pathlib import Path

    core_source = Path("backend/core/config.py").read_text()
    root_source = Path("config.py").read_text()

    assert "class Settings" in core_source
    assert "def get_settings" in core_source
    assert "from config import" not in core_source
    assert "from backend.core.config import" in root_source
    assert "Temporary compatibility wrapper. Delete after" in root_source


def test_account_auth_module_does_not_export_legacy_flag():
    import backend.services.identity.accounts as account_auth

    assert "account_auth_enabled" not in account_auth.__all__
    assert not hasattr(account_auth, "account_auth_enabled")
