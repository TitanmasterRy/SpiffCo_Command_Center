"""Asyncio-based periodic task scheduler.

Deliberately broker-free: for a self-hosted single-process app, asyncio tasks
are simpler to operate than Celery/APScheduler and sufficient for polling FRM,
sampling history, and housekeeping. Jobs run in the event loop, so they must be
async and non-blocking.

A failing job is logged and retried on the next tick — one bad job never kills
the scheduler or other jobs.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

JobFunc = Callable[[], Awaitable[None]]


@dataclass
class Job:
    """A named periodic job."""

    name: str
    func: JobFunc
    interval_seconds: float
    run_count: int = 0
    error_count: int = 0
    _task: asyncio.Task[None] | None = field(default=None, repr=False)


class Scheduler:
    """Runs registered jobs on fixed intervals until stopped."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._running = False

    def add_job(self, name: str, func: JobFunc, interval_seconds: float) -> Job:
        """Register a periodic job; must be called before :meth:`start`.

        Raises:
            ValueError: if a job with *name* already exists or the interval
                is not positive.
        """
        if name in self._jobs:
            raise ValueError(f"job {name!r} already registered")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        job = Job(name=name, func=func, interval_seconds=interval_seconds)
        self._jobs[name] = job
        return job

    async def start(self) -> None:
        """Start one runner task per registered job."""
        if self._running:
            return
        self._running = True
        for job in self._jobs.values():
            job._task = asyncio.create_task(self._run_job(job), name=f"job:{job.name}")
        logger.info("Scheduler started with %d job(s)", len(self._jobs))

    async def stop(self) -> None:
        """Cancel all runner tasks and wait for them to finish."""
        self._running = False
        tasks = [job._task for job in self._jobs.values() if job._task is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for job in self._jobs.values():
            job._task = None
        logger.info("Scheduler stopped")

    async def _run_job(self, job: Job) -> None:
        """Run *job* every ``interval_seconds`` until cancelled."""
        while self._running:
            try:
                await job.func()
                job.run_count += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                job.error_count += 1
                logger.exception("Job %r failed (error #%d)", job.name, job.error_count)
            await asyncio.sleep(job.interval_seconds)

    @property
    def jobs(self) -> list[Job]:
        """Snapshot of registered jobs (for health/metrics endpoints)."""
        return list(self._jobs.values())
