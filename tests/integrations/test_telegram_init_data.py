import hashlib
import hmac
import json
from urllib.parse import urlencode


BOT_TOKEN = "123456:test-token"


def _signed_init_data(*, user_id=42, auth_date=1, bot_token=BOT_TOKEN):
    fields = {
        "auth_date": str(auth_date),
        "user": json.dumps(
            {
                "id": user_id,
                "first_name": "Example",
                "last_name": "User",
                "username": "example_user",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    fields["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(fields)


def test_import_path_exports_public_helpers():
    from backend.integrations.telegram.init_data import (
        telegram_user_from_init_data,
        telegram_user_id_from_init_data,
        verify_telegram_init_data,
    )

    assert callable(verify_telegram_init_data)
    assert callable(telegram_user_id_from_init_data)
    assert callable(telegram_user_from_init_data)


def test_import_path_verifies_valid_init_data():
    import backend.integrations.telegram.init_data as init_data_module

    init_data = _signed_init_data()

    fields = init_data_module.verify_telegram_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    )

    assert fields
    assert init_data_module.telegram_user_id_from_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    ) == 42
    assert init_data_module.telegram_user_from_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    )["id"] == 42


def test_invalid_init_data_returns_none():
    import backend.integrations.telegram.init_data as init_data_module

    invalid_init_data = "auth_date=1&user=%7B%7D&hash=bad"

    assert init_data_module.verify_telegram_init_data(invalid_init_data, bot_token=BOT_TOKEN) is None
    assert (
        init_data_module.telegram_user_id_from_init_data(
            invalid_init_data,
            bot_token=BOT_TOKEN,
        )
        is None
    )
    assert (
        init_data_module.telegram_user_from_init_data(
            invalid_init_data,
            bot_token=BOT_TOKEN,
        )
        is None
    )
