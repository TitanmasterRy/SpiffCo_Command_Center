"""Tests for the periodic task scheduler."""

from __future__ import annotations

import asyncio

import pytest

from app.workers.scheduler import Scheduler


async def test_job_runs_periodically() -> None:
    scheduler = Scheduler()
    ran = asyncio.Event()

    async def job() -> None:
        ran.set()

    scheduler.add_job("tick", job, interval_seconds=0.01)
    await scheduler.start()
    try:
        await asyncio.wait_for(ran.wait(), timeout=1)
    finally:
        await scheduler.stop()
    assert scheduler.jobs[0].run_count >= 1


async def test_failing_job_keeps_running() -> None:
    scheduler = Scheduler()
    calls = 0

    async def flaky() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    scheduler.add_job("flaky", flaky, interval_seconds=0.01)
    await scheduler.start()
    try:
        for _ in range(100):
            if calls >= 2:
                break
            await asyncio.sleep(0.01)
    finally:
        await scheduler.stop()

    job = scheduler.jobs[0]
    assert calls >= 2, "job should be retried after failure"
    assert job.error_count >= 2
    assert job.run_count == 0


async def test_duplicate_and_invalid_jobs_rejected() -> None:
    scheduler = Scheduler()

    async def noop() -> None: ...

    scheduler.add_job("a", noop, interval_seconds=1)
    with pytest.raises(ValueError):
        scheduler.add_job("a", noop, interval_seconds=1)
    with pytest.raises(ValueError):
        scheduler.add_job("b", noop, interval_seconds=0)
