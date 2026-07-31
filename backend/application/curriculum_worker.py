"""LMS-owned durable processing for curriculum presentation conversions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from threading import Event, Thread

from backend.application.container import AppContainer
from backend.application.worker import default_worker_id, run_worker
from backend.core.runtime.config import AppSettings
from backend.modules.domains.academics.subject_curriculum.job_handlers import (
    CONVERT_PRESENTATION_HANDLER,
)
from backend.modules.domains.academics.subject_curriculum.media import (
    CONVERT_PRESENTATION_TOPIC,
)
from backend.modules.jobs.handlers import JobHandlerRegistry

LOGGER = logging.getLogger("msi.curriculum")


@dataclass(frozen=True)
class CurriculumWorkerHandle:
    stop_event: Event
    thread: Thread

    def close(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            LOGGER.warning("Embedded curriculum processing did not stop within 10 seconds.")


def _curriculum_worker_container(settings: AppSettings) -> AppContainer:
    worker_settings = replace(
        settings.worker,
        worker_id=f"lms-curriculum:{default_worker_id()}",
        allowed_topics=(CONVERT_PRESENTATION_TOPIC,),
    )
    return AppContainer.build(replace(settings, worker=worker_settings))


def _curriculum_handler_registry() -> JobHandlerRegistry:
    registry = JobHandlerRegistry()
    registry.register(CONVERT_PRESENTATION_HANDLER)
    return registry


def start_curriculum_worker(settings: AppSettings) -> CurriculumWorkerHandle:
    """Start the curriculum worker inside the LMS web process."""

    stop_event = Event()
    thread = Thread(
        target=run_worker,
        kwargs={
            "container": _curriculum_worker_container(settings),
            "registry": _curriculum_handler_registry(),
            "stop_event": stop_event,
        },
        daemon=True,
        name="lms-curriculum-worker",
    )
    thread.start()
    LOGGER.info("Embedded curriculum processing started inside MSI-LMS-Portal.")
    return CurriculumWorkerHandle(stop_event=stop_event, thread=thread)


__all__ = ["CurriculumWorkerHandle", "start_curriculum_worker"]
