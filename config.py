from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    mini_app_url: str
    web_host: str
    web_port: int
    webapp_init_data_ttl: int


@dataclass(frozen=True)
class WebSettings:
    web_host: str
    web_port: int


def _int_env(name, default):
    value = getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    return int(value)


def get_web_settings():
    web_port = _int_env("PORT", _int_env("WEB_PORT", _int_env("FLASK_PORT", 8080)))
    return WebSettings(
        web_host=getenv("WEB_HOST", getenv("FLASK_HOST", "0.0.0.0")),
        web_port=web_port,
    )


def get_settings():
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
        web_host=web_settings.web_host,
        web_port=web_settings.web_port,
        webapp_init_data_ttl=_int_env("WEBAPP_INIT_DATA_TTL", 3600),
    )
