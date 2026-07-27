"""Clock port used by commands and deterministic tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.core.time import utc_now


class Clock(Protocol):
    def now(self) -> datetime:
        """Return a timezone-aware instant."""


@dataclass(frozen=True)
class SystemClock:
    def now(self) -> datetime:
        return utc_now()


@dataclass(frozen=True)
class FixedClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


__all__ = ["Clock", "FixedClock", "SystemClock"]
