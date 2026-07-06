def test_account_auth_flag_has_been_removed_from_core_config():
    import backend.core.config as config

    assert "account_auth_v2_enabled" not in config.__all__
    assert not hasattr(config, "account_auth_v2_enabled")


def test_account_auth_module_does_not_export_legacy_flag():
    import backend.identity.account_auth_v2 as account_auth

    assert "account_auth_v2_enabled" not in account_auth.__all__
    assert not hasattr(account_auth, "account_auth_v2_enabled")
