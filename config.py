from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    mini_app_url: str
    flask_host: str
    flask_port: int
    webapp_init_data_ttl: int


@dataclass(frozen=True)
class WebSettings:
    flask_host: str
    flask_port: int


def _int_env(name, default):
    # Read integer environment variables with fallback support.
    value = getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    return int(value)


def get_web_settings():
    # Shared Flask host/port config used by both root main.py and web/app.py.
    flask_port = _int_env("PORT", _int_env("FLASK_PORT", 8080))
    return WebSettings(
        flask_host=getenv("FLASK_HOST", "0.0.0.0"),
        flask_port=flask_port,
    )


def get_settings():
    # Full config used by the Telegram bot.
    bot_token = getenv("BOT_TOKEN", "").strip()
    mini_app_url = getenv("MINI_APP_URL", "").strip()

    if not bot_token:
        raise ValueError("BOT_TOKEN is required")
    if not mini_app_url:
        raise ValueError("MINI_APP_URL is required")

    web_settings = get_web_settings()

    return Settings(
        bot_token=bot_token,
        mini_app_url=mini_app_url,
        flask_host=web_settings.flask_host,
        flask_port=web_settings.flask_port,
        webapp_init_data_ttl=_int_env("WEBAPP_INIT_DATA_TTL", 3600),
    )
