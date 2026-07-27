"""Application-owned dependencies shared by entrypoints."""

from __future__ import annotations

from dataclasses import dataclass

from slowapi import Limiter

from backend.core.clock import Clock, SystemClock
from backend.core.database import close_idle_pool_connections
from backend.core.runtime.config import AppSettings, get_app_settings
from backend.core.runtime.rate_limit import create_limiter
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.jobs.contracts import enqueue_on_connection


@dataclass(frozen=True)
class AppContainer:
    settings: AppSettings
    unit_of_work_factory: UnitOfWorkFactory
    clock: Clock
    limiter: Limiter
    cache: object | None = None
    storage: object | None = None
    telemetry: object | None = None

    @classmethod
    def build(cls, settings: AppSettings | None = None) -> AppContainer:
        app_settings = settings or get_app_settings()
        return cls(
            settings=app_settings,
            unit_of_work_factory=UnitOfWorkFactory(job_enqueuer=enqueue_on_connection),
            clock=SystemClock(),
            limiter=create_limiter(app_settings.redis.url),
        )

    def close(self) -> None:
        """Release application-owned pools and optional external clients."""

        close_idle_pool_connections()
        for dependency in (self.cache, self.storage, self.telemetry):
            close = getattr(dependency, "close", None)
            if callable(close):
                close()


__all__ = ["AppContainer"]
