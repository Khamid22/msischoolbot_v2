"""Typed commands and records for durable jobs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from backend.modules.jobs.domain_types import JobStatus


class JobModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EnqueueJobCommand(JobModel):
    topic: str = Field(min_length=1, max_length=160)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=240)
    available_at: datetime | None = None
    max_attempts: int = Field(default=5, ge=1, le=100)


class JobRecord(JobModel):
    job_id: int
    topic: str
    payload: dict[str, JsonValue]
    idempotency_key: str
    status: JobStatus
    attempts: int
    max_attempts: int
    available_at: datetime
    lease_owner: str = ""
    lease_expires_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_error: str = ""


__all__ = ["EnqueueJobCommand", "JobModel", "JobRecord"]
