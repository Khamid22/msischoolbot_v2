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


def test_old_import_path_still_exports_public_helpers():
    from backend.utils.telegram_auth import (
        telegram_user_from_init_data,
        telegram_user_id_from_init_data,
        verify_telegram_init_data,
    )

    assert callable(verify_telegram_init_data)
    assert callable(telegram_user_id_from_init_data)
    assert callable(telegram_user_from_init_data)


def test_new_import_path_exports_public_helpers():
    from backend.integrations.telegram.init_data import (
        telegram_user_from_init_data,
        telegram_user_id_from_init_data,
        verify_telegram_init_data,
    )

    assert callable(verify_telegram_init_data)
    assert callable(telegram_user_id_from_init_data)
    assert callable(telegram_user_from_init_data)


def test_old_and_new_paths_share_same_public_functions():
    import backend.integrations.telegram.init_data as new_path
    import backend.utils.telegram_auth as old_path

    assert old_path.__all__ == new_path.__all__
    assert old_path.verify_telegram_init_data is new_path.verify_telegram_init_data
    assert old_path.telegram_user_id_from_init_data is new_path.telegram_user_id_from_init_data
    assert old_path.telegram_user_from_init_data is new_path.telegram_user_from_init_data


def test_old_and_new_paths_verify_valid_init_data_the_same_way():
    import backend.integrations.telegram.init_data as new_path
    import backend.utils.telegram_auth as old_path

    init_data = _signed_init_data()

    old_fields = old_path.verify_telegram_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    )
    new_fields = new_path.verify_telegram_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    )

    assert old_fields == new_fields
    assert old_path.telegram_user_id_from_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    ) == 42
    assert new_path.telegram_user_from_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        max_age_seconds=0,
    )["id"] == 42


def test_invalid_init_data_returns_none_from_old_and_new_paths():
    import backend.integrations.telegram.init_data as new_path
    import backend.utils.telegram_auth as old_path

    invalid_init_data = "auth_date=1&user=%7B%7D&hash=bad"

    assert old_path.verify_telegram_init_data(invalid_init_data, bot_token=BOT_TOKEN) is None
    assert new_path.verify_telegram_init_data(invalid_init_data, bot_token=BOT_TOKEN) is None
    assert old_path.telegram_user_id_from_init_data(invalid_init_data, bot_token=BOT_TOKEN) is None
    assert new_path.telegram_user_from_init_data(invalid_init_data, bot_token=BOT_TOKEN) is None

