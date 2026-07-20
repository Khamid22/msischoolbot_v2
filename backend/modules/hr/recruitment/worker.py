"""Dedicated Recruitment notification worker process."""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Callable

from backend.modules.hr.recruitment.notifications import process_due_notifications


LOGGER = logging.getLogger("msi.recruitment.worker")


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(str(os.environ.get(name, "") or "").strip() or default)
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def poll_seconds() -> int:
    return _env_int(
        "RECRUITMENT_NOTIFICATION_POLL_SECONDS",
        60,
        minimum=5,
        maximum=3600,
    )


def batch_limit() -> int:
    return _env_int(
        "RECRUITMENT_NOTIFICATION_BATCH_LIMIT",
        25,
        minimum=1,
        maximum=250,
    )


def run_once(
    *,
    processor: Callable[..., int] | None = None,
    limit: int | None = None,
) -> int:
    deliver = processor or process_due_notifications
    return int(deliver(limit=int(limit or batch_limit())) or 0)


def run_forever(
    *,
    stop_event: threading.Event | None = None,
    processor: Callable[..., int] | None = None,
) -> None:
    """Process due rows until the process receives a shutdown signal."""

    stopping = stop_event or threading.Event()
    interval = poll_seconds()
    limit = batch_limit()
    LOGGER.info(
        "Recruitment notification worker started poll_seconds=%s batch_limit=%s",
        interval,
        limit,
    )
    while not stopping.is_set():
        try:
            delivered = run_once(processor=processor, limit=limit)
            if delivered:
                LOGGER.info(
                    "Recruitment notifications delivered count=%s",
                    delivered,
                )
        except Exception:
            LOGGER.exception("Recruitment notification delivery cycle failed")
        stopping.wait(interval)
    LOGGER.info("Recruitment notification worker stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    stop_event = threading.Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    for signal_name in ("SIGTERM", "SIGINT"):
        process_signal = getattr(signal, signal_name, None)
        if process_signal is not None:
            signal.signal(process_signal, request_stop)
    run_forever(stop_event=stop_event)


if __name__ == "__main__":
    main()


__all__ = ["batch_limit", "main", "poll_seconds", "run_forever", "run_once"]
