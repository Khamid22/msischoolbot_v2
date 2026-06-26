"""Validation of Telegram WebApp ``initData`` signatures.

Telegram signs the ``initData`` string it injects into a Mini App with an
HMAC-SHA256 keyed by the bot token. Trusting the unsigned ``initDataUnsafe``
object (or a bare ``tg_user_id`` query parameter) lets anyone impersonate a
linked student, because Telegram user IDs are not secret. Every server-side
trust decision about "who is this Telegram user" must go through
:func:`telegram_user_id_from_init_data`.
"""

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

# Per Telegram's spec the data-check-string excludes the ``hash`` field (the
# HMAC we verify) and the ``signature`` field (a separate Ed25519 signature for
# third-party validation that is not part of the bot-token HMAC).
_EXCLUDED_FIELDS = ("hash", "signature")


def _bot_token():
    return str(os.environ.get("BOT_TOKEN", "") or "").strip()


def _default_max_age_seconds():
    raw_value = str(os.environ.get("WEBAPP_INIT_DATA_TTL", "3600") or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return 3600
    return parsed if parsed >= 0 else 3600


def verify_telegram_init_data(init_data, bot_token=None, max_age_seconds=None):
    """Return the parsed, *verified* initData fields, or ``None`` if invalid.

    ``init_data`` is the raw ``window.Telegram.WebApp.initData`` query string.
    The HMAC is recomputed from the bot token and compared in constant time. A
    positive ``max_age_seconds`` also rejects payloads whose ``auth_date`` is
    older than the window (replay protection); pass ``0`` to skip the age check.
    """
    init_data = str(init_data or "").strip()
    token = str(bot_token if bot_token is not None else _bot_token()).strip()
    if not init_data or not token:
        return None

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None

    fields = dict(pairs)
    received_hash = fields.get("hash", "")
    if not received_hash:
        return None

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(fields.items())
        if key not in _EXCLUDED_FIELDS
    )

    secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    effective_max_age = (
        _default_max_age_seconds() if max_age_seconds is None else int(max_age_seconds)
    )
    if effective_max_age > 0:
        try:
            auth_date = int(fields.get("auth_date", "0"))
        except ValueError:
            return None
        if auth_date <= 0 or (time.time() - auth_date) > effective_max_age:
            return None

    return fields


def telegram_user_id_from_init_data(init_data, bot_token=None, max_age_seconds=None):
    """Return the verified Telegram user id from ``init_data``, or ``None``.

    Only returns an id when the HMAC signature (and optional age window) checks
    out, so callers can safely treat the result as the authenticated identity.
    """
    fields = verify_telegram_init_data(init_data, bot_token, max_age_seconds)
    if not fields:
        return None

    try:
        user = json.loads(fields.get("user", ""))
    except (TypeError, ValueError):
        return None

    if not isinstance(user, dict):
        return None
    try:
        user_id = int(user.get("id"))
    except (TypeError, ValueError):
        return None
    return user_id if user_id > 0 else None


def telegram_user_from_init_data(init_data, bot_token=None, max_age_seconds=None):
    """Return the verified Telegram WebApp user object, or ``None``."""
    fields = verify_telegram_init_data(init_data, bot_token, max_age_seconds)
    if not fields:
        return None

    try:
        user = json.loads(fields.get("user", ""))
    except (TypeError, ValueError):
        return None

    if not isinstance(user, dict):
        return None
    try:
        user_id = int(user.get("id"))
    except (TypeError, ValueError):
        return None
    if user_id <= 0:
        return None
    user["id"] = user_id
    return user


__all__ = [
    "verify_telegram_init_data",
    "telegram_user_id_from_init_data",
    "telegram_user_from_init_data",
]
