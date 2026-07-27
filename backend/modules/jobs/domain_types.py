"""Stable outbox job vocabulary."""

from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRY = "retry"
    COMPLETED = "completed"
    DEAD = "dead"


__all__ = ["JobStatus"]
