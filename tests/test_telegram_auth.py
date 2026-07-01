import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from backend.utils.telegram_auth import telegram_user_from_init_data


def _signed_init_data(bot_token, fields):
    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(fields.items())
        if key != "hash"
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload = dict(fields)
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def test_telegram_init_data_accepts_standard_hash(monkeypatch):
    bot_token = "123456:test-token"
    monkeypatch.setenv("BOT_TOKEN", bot_token)
    init_data = _signed_init_data(
        bot_token,
        {
            "auth_date": str(int(time.time())),
            "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
            "user": json.dumps({"id": 42, "first_name": "Parent"}, separators=(",", ":")),
        },
    )

    user = telegram_user_from_init_data(init_data)

    assert user
    assert user["id"] == 42


def test_telegram_init_data_keeps_signature_field_in_hash(monkeypatch):
    bot_token = "123456:test-token"
    monkeypatch.setenv("BOT_TOKEN", bot_token)
    init_data = _signed_init_data(
        bot_token,
        {
            "auth_date": str(int(time.time())),
            "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
            "signature": "new-client-ed25519-signature",
            "user": json.dumps({"id": 43, "first_name": "Parent"}, separators=(",", ":")),
        },
    )

    user = telegram_user_from_init_data(init_data)

    assert user
    assert user["id"] == 43
