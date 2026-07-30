"""Core runtime configuration helpers for MSI LMS Portal."""

from __future__ import annotations

from dataclasses import dataclass, field
from os import environ, getenv

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
    asset_version: str = ""


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = field(repr=False)
    pool_enabled: bool
    pool_min: int
    pool_max: int
    pool_timeout_seconds: float
    pool_max_idle_seconds: int
    slow_wait_ms: float


@dataclass(frozen=True)
class SessionSettings:
    secret_key: str = field(repr=False)
    cookie_name: str
    max_age_seconds: int
    same_site: str
    https_only: bool


@dataclass(frozen=True)
class WorkerSettings:
    worker_id: str
    batch_size: int
    poll_interval_seconds: float
    lease_seconds: int
    default_max_attempts: int
    retry_base_seconds: int
    retry_max_seconds: int
    allowed_topics: tuple[str, ...]


@dataclass(frozen=True)
class RedisSettings:
    url: str = field(repr=False)
    default_ttl_seconds: int


@dataclass(frozen=True)
class StorageSettings:
    bucket: str
    upload_max_bytes: int
    signed_url_ttl_seconds: int
    connect_timeout_seconds: int
    read_timeout_seconds: int


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str = field(repr=False)
    mini_app_url: str
    api_timeout_seconds: float
    init_data_ttl_seconds: int
    academy_channel_chat_id: str = field(repr=False)
    academy_subject_chat_ids: tuple[tuple[str, str], ...] = field(repr=False)


@dataclass(frozen=True)
class PaymeSettings:
    environment: str
    merchant_id: str
    login: str
    key: str = field(repr=False)
    checkout_url: str
    callback_base_url: str
    request_body_max_bytes: int
    transaction_timeout_seconds: int

    @property
    def is_configured(self) -> bool:
        return bool(self.merchant_id and self.login and self.key)


@dataclass(frozen=True)
class PlatformSettings:
    """Deprecated aggregate retained for compatibility with older callers."""

    redis_url: str = field(repr=False)
    storage_bucket: str
    telegram_bot_token: str = field(repr=False)


@dataclass(frozen=True)
class ObservabilitySettings:
    sentry_dsn: str = field(repr=False)
    slow_request_ms: float


@dataclass(frozen=True)
class AppSettings:
    environment: str
    web: WebSettings
    database: DatabaseSettings
    session: SessionSettings
    worker: WorkerSettings
    redis: RedisSettings
    storage: StorageSettings
    telegram: TelegramSettings
    payme: PaymeSettings
    observability: ObservabilitySettings

    @property
    def platform(self) -> PlatformSettings:
        return PlatformSettings(
            redis_url=self.redis.url,
            storage_bucket=self.storage.bucket,
            telegram_bot_token=self.telegram.bot_token,
        )


def _int_env(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    return int(value)


def _float_env(name: str, default: float) -> float:
    value = getenv(name)
    if value is None or not value.strip():
        return default
    return float(value)


def _bool_env(name: str, default: bool = False) -> bool:
    value = getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().casefold() not in {"0", "false", "no", "off"}


def _csv_env(name: str) -> tuple[str, ...]:
    values = {item.strip() for item in getenv(name, "").split(",") if item.strip()}
    return tuple(sorted(values))


def _session_secret(environment: str) -> str:
    secret_key = getenv("APP_SECRET_KEY", getenv("FLASK_SECRET_KEY", "")).strip()
    if secret_key:
        return secret_key
    if environment in {"dev", "development", "local", "test"}:
        return "dev-only-insecure-key-do-not-use-in-prod"
    raise RuntimeError(
        "APP_SECRET_KEY must be set. Generate one with: "
        'python -c "import secrets; print(secrets.token_hex(32))"'
    )


def get_web_settings() -> WebSettings:
    web_port = _int_env("PORT", _int_env("WEB_PORT", _int_env("FLASK_PORT", 8080)))
    return WebSettings(
        web_host=getenv("WEB_HOST", getenv("FLASK_HOST", "0.0.0.0")),
        web_port=web_port,
        asset_version=getenv("ASSET_VERSION", "").strip(),
    )


def _database_settings() -> DatabaseSettings:
    pool_max = max(1, _int_env("DB_POOL_MAX", 5))
    pool_min = min(max(0, _int_env("DB_POOL_MIN", 2)), pool_max)
    return DatabaseSettings(
        url=(getenv("DATABASE_URL", "").strip() or getenv("POSTGRES_URL", "").strip()),
        pool_enabled=not _bool_env("DB_POOL_DISABLE"),
        pool_min=pool_min,
        pool_max=pool_max,
        pool_timeout_seconds=max(1.0, _float_env("DB_POOL_TIMEOUT", 10.0)),
        pool_max_idle_seconds=max(1, _int_env("DB_POOL_MAX_IDLE_SECONDS", 300)),
        slow_wait_ms=max(0.0, _float_env("DB_POOL_SLOW_WAIT_MS", 25.0)),
    )


def _session_settings(environment: str) -> SessionSettings:
    return SessionSettings(
        secret_key=_session_secret(environment),
        cookie_name=getenv("SESSION_COOKIE_NAME", "session").strip() or "session",
        max_age_seconds=max(60, _int_env("SESSION_MAX_AGE_SECONDS", 30 * 24 * 3600)),
        same_site=getenv("SESSION_COOKIE_SAMESITE", "lax").strip().lower() or "lax",
        https_only=_bool_env("SESSION_COOKIE_SECURE"),
    )


def _worker_settings() -> WorkerSettings:
    return WorkerSettings(
        worker_id=getenv("WORKER_ID", "").strip(),
        batch_size=max(1, _int_env("WORKER_BATCH_SIZE", 25)),
        poll_interval_seconds=max(0.1, _float_env("WORKER_POLL_INTERVAL_SECONDS", 1.0)),
        lease_seconds=max(30, _int_env("WORKER_LEASE_SECONDS", 300)),
        default_max_attempts=max(1, _int_env("WORKER_MAX_ATTEMPTS", 5)),
        retry_base_seconds=max(1, _int_env("WORKER_RETRY_BASE_SECONDS", 15)),
        retry_max_seconds=max(1, _int_env("WORKER_RETRY_MAX_SECONDS", 3600)),
        allowed_topics=_csv_env("WORKER_ALLOWED_TOPICS"),
    )


def _storage_settings() -> StorageSettings:
    storage_bucket = getenv("R2_BUCKET_NAME", "").strip() or getenv("S3_BUCKET_NAME", "").strip()
    return StorageSettings(
        bucket=storage_bucket,
        upload_max_bytes=max(1, _int_env("RESOURCE_UPLOAD_MAX_MB", 1024)) * 1024 * 1024,
        signed_url_ttl_seconds=max(60, _int_env("R2_SIGNED_URL_TTL_SECONDS", 21600)),
        connect_timeout_seconds=max(1, _int_env("R2_CONNECT_TIMEOUT_SECONDS", 10)),
        read_timeout_seconds=max(1, _int_env("R2_READ_TIMEOUT_SECONDS", 300)),
    )


def _telegram_settings() -> TelegramSettings:
    return TelegramSettings(
        bot_token=getenv("BOT_TOKEN", "").strip(),
        mini_app_url=getenv("MINI_APP_URL", "").strip(),
        api_timeout_seconds=max(0.1, _float_env("TELEGRAM_API_TIMEOUT_SECONDS", 5.0)),
        init_data_ttl_seconds=max(60, _int_env("WEBAPP_INIT_DATA_TTL", 3600)),
        academy_channel_chat_id=getenv("TEACHER_ACADEMY_CHANNEL_CHAT_ID", "").strip(),
        academy_subject_chat_ids=tuple(
            sorted(
                (name, str(value).strip())
                for name, value in environ.items()
                if name.startswith("TEACHER_ACADEMY_")
                and name.endswith("_CHAT_ID")
                and name != "TEACHER_ACADEMY_CHANNEL_CHAT_ID"
                and str(value).strip()
            )
        ),
    )


def _payme_settings(environment: str) -> PaymeSettings:
    payme_environment = getenv("PAYME_ENVIRONMENT", "test").strip().casefold() or "test"
    if payme_environment not in {"test", "production"}:
        raise RuntimeError("PAYME_ENVIRONMENT must be either 'test' or 'production'.")
    if environment == "production" and payme_environment == "test":
        merchant_id = ""
        login = ""
        key = ""
    else:
        merchant_id = getenv("PAYME_MERCHANT_ID", "").strip()
        login = getenv("PAYME_MERCHANT_LOGIN", "").strip()
        key = getenv("PAYME_MERCHANT_KEY", "").strip()
    default_checkout = (
        "https://checkout.paycom.uz/"
        if payme_environment == "production"
        else "https://test.paycom.uz/"
    )
    return PaymeSettings(
        environment=payme_environment,
        merchant_id=merchant_id,
        login=login,
        key=key,
        checkout_url=getenv("PAYME_CHECKOUT_URL", default_checkout).strip() or default_checkout,
        callback_base_url=getenv("PUBLIC_BASE_URL", "").strip().rstrip("/"),
        request_body_max_bytes=max(1024, _int_env("PAYME_REQUEST_BODY_MAX_BYTES", 65536)),
        transaction_timeout_seconds=max(
            60,
            _int_env("PAYME_TRANSACTION_TIMEOUT_SECONDS", 43200),
        ),
    )


def get_app_settings() -> AppSettings:
    """Read and validate the typed settings shared by web and worker processes."""

    environment = getenv("APP_ENV", "").strip().casefold() or "production"
    return AppSettings(
        environment=environment,
        web=get_web_settings(),
        database=_database_settings(),
        session=_session_settings(environment),
        worker=_worker_settings(),
        redis=RedisSettings(
            url=getenv("REDIS_URL", "").strip(),
            default_ttl_seconds=max(1, _int_env("CACHE_DEFAULT_TTL_SECONDS", 300)),
        ),
        storage=_storage_settings(),
        telegram=_telegram_settings(),
        payme=_payme_settings(environment),
        observability=ObservabilitySettings(
            sentry_dsn=getenv("SENTRY_DSN", "").strip(),
            slow_request_ms=max(0.0, _float_env("HTTP_SLOW_REQUEST_MS", 500.0)),
        ),
    )


def get_settings() -> Settings:
    app_settings = get_app_settings()
    bot_token = app_settings.telegram.bot_token
    mini_app_url = app_settings.telegram.mini_app_url

    if not bot_token:
        raise ValueError("BOT_TOKEN is required")
    if not mini_app_url:
        raise ValueError("MINI_APP_URL is required")

    return Settings(
        bot_token=bot_token,
        mini_app_url=mini_app_url,
        web_host=app_settings.web.web_host,
        web_port=app_settings.web.web_port,
        webapp_init_data_ttl=app_settings.telegram.init_data_ttl_seconds,
    )


__all__ = [
    "AppSettings",
    "DatabaseSettings",
    "ObservabilitySettings",
    "PaymeSettings",
    "PlatformSettings",
    "RedisSettings",
    "SessionSettings",
    "Settings",
    "StorageSettings",
    "TelegramSettings",
    "WebSettings",
    "WorkerSettings",
    "get_app_settings",
    "get_settings",
    "get_web_settings",
]
