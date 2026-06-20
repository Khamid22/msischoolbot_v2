import os

from flask import Flask
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect


def _limiter_storage_uri() -> str:
    # Use Redis when available so limits are shared across web processes/instances;
    # fall back to in-process memory for single-process/local runs.
    return (os.environ.get("REDIS_URL", "") or "").strip() or "memory://"


login_manager: LoginManager = LoginManager()
csrf: CSRFProtect = CSRFProtect()
limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_limiter_storage_uri(),
    # Availability over strictness: if the limiter storage is down, let requests
    # through rather than failing logins.
    swallow_errors=True,
)


def init_extensions(app: Flask) -> None:
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)


__all__ = ["login_manager", "csrf", "limiter", "init_extensions"]
