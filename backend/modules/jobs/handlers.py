"""Typed worker-handler registry."""

from __future__ import annotations

from backend.core.jobs import JobHandlerSpec


class JobHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, JobHandlerSpec] = {}

    def register(self, handler_spec: JobHandlerSpec) -> None:
        normalized_topic = str(handler_spec.topic or "").strip()
        if not normalized_topic:
            raise ValueError("Job handler topic is required.")
        if normalized_topic in self._handlers:
            raise ValueError(f"A handler is already registered for {normalized_topic}.")
        self._handlers[normalized_topic] = handler_spec

    def handler_for(self, topic: str) -> JobHandlerSpec | None:
        return self._handlers.get(str(topic or "").strip())

    @property
    def topics(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))


__all__ = ["JobHandlerRegistry"]
