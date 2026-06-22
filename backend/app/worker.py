"""Scan worker entry point.

Runs as a separate process (`python -m app.worker`) from the API. It blocks on
the Redis scan queue and processes jobs one at a time. The actual scan logic
(crawler + checks) arrives in later phases; for now the worker validates the
hand-off path and marks scan lifecycle transitions.
"""

from __future__ import annotations

import signal
import sys
from types import FrameType

from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.queue import ScanJob, ScanQueue

logger = get_logger("webhawk.worker")

_running = True


def _handle_signal(signum: int, _frame: FrameType | None) -> None:
    global _running
    logger.info("worker received signal %s, shutting down after current job", signum)
    _running = False


def process_job(job: ScanJob) -> None:
    """Process a single scan job.

    Placeholder for the scan pipeline (Phases 2–4). Kept side-effect-light so
    the worker loop is testable; real implementations will load the Target,
    enforce scope/authorization, run checks, and persist Findings.
    """
    logger.info("processing scan id=%s target=%s", job.scan_id, job.target_id)


def run(queue: ScanQueue | None = None, *, max_jobs: int | None = None) -> int:
    """Run the worker loop.

    :param queue: queue to consume (defaults to a Redis-backed one).
    :param max_jobs: stop after this many jobs (used by tests); None = forever.
    :returns: number of jobs processed.
    """
    settings = get_settings()
    configure_logging(debug=settings.debug)
    queue = queue or ScanQueue()

    logger.info("worker started (env=%s)", settings.environment)
    processed = 0
    while _running and (max_jobs is None or processed < max_jobs):
        job = queue.dequeue(timeout=5)
        if job is None:
            continue
        try:
            process_job(job)
            processed += 1
        except Exception:  # noqa: BLE001 - worker must survive any single job
            logger.exception("scan job failed id=%s", job.scan_id)
    logger.info("worker stopped after %d job(s)", processed)
    return processed


def main() -> int:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    return run()


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
