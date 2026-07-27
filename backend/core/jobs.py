"""Typed vocabulary shared by durable-job producers and workers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, JsonValue


class DurableJobCommand(Protocol):
    topic: str
    payload: Mapping[str, JsonValue]
    idempotency_key: str
    available_at: datetime | None
    max_attempts: int


@dataclass(frozen=True)
class JobExecutionContext:
    job_id: int
    attempt: int
    worker_id: str


class JobHandler[PayloadT: BaseModel](Protocol):
    def __call__(
        self,
        payload: PayloadT,
        context: JobExecutionContext,
    ) -> None: ...


@dataclass(frozen=True)
class JobHandlerSpec[PayloadT: BaseModel]:
    topic: str
    payload_model: type[PayloadT]
    handler: JobHandler[PayloadT]

    def handle(
        self,
        payload: Mapping[str, JsonValue],
        context: JobExecutionContext,
    ) -> None:
        self.handler(self.payload_model.model_validate(dict(payload)), context)


__all__ = [
    "DurableJobCommand",
    "JobExecutionContext",
    "JobHandler",
    "JobHandlerSpec",
]
