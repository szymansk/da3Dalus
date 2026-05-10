"""In-memory background job tracker with asyncio debounce for auto-retrim."""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Awaitable, Callable, Coroutine

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    DEBOUNCING = "DEBOUNCING"
    COMPUTING = "COMPUTING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class RetrimJob:
    aeroplane_id: int
    status: JobStatus = JobStatus.DEBOUNCING
    dirty_op_ids: list[int] = field(default_factory=list)
    completed_op_ids: list[int] = field(default_factory=list)
    failed_op_ids: list[int] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


@dataclass
class RecomputeAssumptionsJob:
    aeroplane_id: int
    status: JobStatus = JobStatus.DEBOUNCING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class JobTracker:
    def __init__(self, debounce_seconds: float = 2.0) -> None:
        self.debounce_seconds = debounce_seconds
        self._jobs: dict[int, RetrimJob] = {}
        self._debounce_tasks: dict[int, asyncio.Task] = {}
        self._trim_function: Callable[[int], Awaitable[None]] | None = None
        self._recompute_jobs: dict[int, RecomputeAssumptionsJob] = {}
        self._recompute_debounce_tasks: dict[int, asyncio.Task] = {}
        self._recompute_function: Callable[[int], Awaitable[None]] | None = None
        # Reference to the FastAPI event loop, captured at startup. Lets
        # us schedule from worker threads (asyncio.to_thread inside the
        # recompute pipeline) instead of silently failing with
        # "no running event loop".
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture the application's main event loop. Call from lifespan."""
        self._main_loop = loop

    def _create_task_safe(self, coro: Coroutine[None, None, None]) -> asyncio.Task | None:
        """Create a task on the main loop regardless of caller thread.

        Returns None when no loop is bound and we're not running inside
        one — in that case the schedule is silently dropped (matching
        previous behaviour for non-server contexts like unit tests).
        """
        try:
            running = asyncio.get_running_loop()
            return running.create_task(coro)
        except RuntimeError:
            pass
        if self._main_loop is None:
            logger.debug("No bound event loop — skipping schedule")
            return None
        # asyncio.run_coroutine_threadsafe returns a concurrent.futures.Future.
        # We don't track it here because cancellation of cross-thread
        # tasks is awkward; the debounce-cancel path uses asyncio.Task,
        # so we only accept proper Task creation for tracking.
        # Workaround: schedule via call_soon_threadsafe so the actual
        # create_task happens on the main thread, returning a real Task
        # via a small wrapper.
        result: dict[str, asyncio.Task | None] = {"task": None}
        ready = threading.Event()

        def _make_task() -> None:
            try:
                result["task"] = self._main_loop.create_task(coro)  # type: ignore[union-attr]
            finally:
                ready.set()

        self._main_loop.call_soon_threadsafe(_make_task)
        ready.wait(timeout=2.0)
        return result["task"]

    def set_trim_function(self, fn: Callable[[int], Awaitable[None]]) -> None:
        self._trim_function = fn

    def schedule_retrim(self, aeroplane_id: int) -> None:
        existing_job = self._jobs.get(aeroplane_id)
        if existing_job and existing_job.status == JobStatus.COMPUTING:
            logger.debug(
                "Retrim already computing for aeroplane %d — will re-check after completion",
                aeroplane_id,
            )
            return

        existing_task = self._debounce_tasks.get(aeroplane_id)

        # Try to create the new task FIRST. Only cancel the existing
        # task and overwrite the job if creation succeeded — otherwise
        # we'd leave the job in DEBOUNCING with no task to fire it.
        new_task = self._create_task_safe(self._debounced_retrim(aeroplane_id))
        if new_task is None:
            logger.debug(
                "Cannot schedule retrim for aeroplane %d — no event loop available",
                aeroplane_id,
            )
            return

        if existing_task and not existing_task.done():
            existing_task.cancel()
        self._jobs[aeroplane_id] = RetrimJob(aeroplane_id=aeroplane_id)
        self._debounce_tasks[aeroplane_id] = new_task

    async def _debounced_retrim(self, aeroplane_id: int) -> None:
        try:
            await asyncio.sleep(self.debounce_seconds)
        except asyncio.CancelledError:
            return

        if self._trim_function is None:
            logger.warning("No trim function registered — cannot retrim aeroplane %d", aeroplane_id)
            return

        job = self._jobs.get(aeroplane_id)
        if job is None:
            return

        job.status = JobStatus.COMPUTING
        job.started_at = datetime.now(timezone.utc)

        try:
            await self._trim_function(aeroplane_id)
            job.status = JobStatus.DONE
        except Exception as exc:
            logger.exception("Retrim failed for aeroplane %d", aeroplane_id)
            job.status = JobStatus.FAILED
            job.error = str(exc)
        finally:
            job.finished_at = datetime.now(timezone.utc)
            self._debounce_tasks.pop(aeroplane_id, None)

    def set_recompute_function(self, fn: Callable[[int], Awaitable[None]]) -> None:
        self._recompute_function = fn

    def schedule_recompute_assumptions(self, aeroplane_id: int) -> None:
        existing_task = self._recompute_debounce_tasks.get(aeroplane_id)

        # Same atomic-create pattern as schedule_retrim: build the task
        # before clobbering existing state. Otherwise a worker-thread
        # caller (no event loop) would cancel the in-flight debounce
        # and leave the job stuck in DEBOUNCING forever.
        new_task = self._create_task_safe(self._debounced_recompute(aeroplane_id))
        if new_task is None:
            logger.debug(
                "Cannot schedule recompute for aeroplane %d — no event loop available",
                aeroplane_id,
            )
            return

        if existing_task and not existing_task.done():
            existing_task.cancel()
        self._recompute_jobs[aeroplane_id] = RecomputeAssumptionsJob(aeroplane_id=aeroplane_id)
        self._recompute_debounce_tasks[aeroplane_id] = new_task

    async def _debounced_recompute(self, aeroplane_id: int) -> None:
        try:
            await asyncio.sleep(self.debounce_seconds)
        except asyncio.CancelledError:
            return

        if self._recompute_function is None:
            logger.warning(
                "No recompute function registered — cannot recompute for aeroplane %d",
                aeroplane_id,
            )
            return

        job = self._recompute_jobs.get(aeroplane_id)
        if job is None:
            return

        job.status = JobStatus.COMPUTING
        job.started_at = datetime.now(timezone.utc)

        try:
            await self._recompute_function(aeroplane_id)
            job.status = JobStatus.DONE
        except Exception as exc:
            logger.exception("Recompute assumptions failed for aeroplane %d", aeroplane_id)
            job.status = JobStatus.FAILED
            job.error = str(exc)
        finally:
            job.finished_at = datetime.now(timezone.utc)
            self._recompute_debounce_tasks.pop(aeroplane_id, None)

    def get_job(self, aeroplane_id: int) -> RetrimJob | None:
        return self._jobs.get(aeroplane_id)

    def is_active(self, aeroplane_id: int) -> bool:
        job = self._jobs.get(aeroplane_id)
        if job is None:
            return False
        return job.status in (JobStatus.DEBOUNCING, JobStatus.COMPUTING)

    def is_debouncing(self, aeroplane_id: int) -> bool:
        job = self._jobs.get(aeroplane_id)
        if job is None:
            return False
        return job.status == JobStatus.DEBOUNCING

    def get_recompute_job(self, aeroplane_id: int) -> RecomputeAssumptionsJob | None:
        return self._recompute_jobs.get(aeroplane_id)

    def is_recompute_active(self, aeroplane_id: int) -> bool:
        """True while a recompute is debouncing or running."""
        job = self._recompute_jobs.get(aeroplane_id)
        if job is None:
            return False
        return job.status in (JobStatus.DEBOUNCING, JobStatus.COMPUTING)

    async def shutdown(self) -> None:
        for task in self._debounce_tasks.values():
            if not task.done():
                task.cancel()
        if self._debounce_tasks:
            await asyncio.gather(*self._debounce_tasks.values(), return_exceptions=True)
        self._debounce_tasks.clear()
        for job in self._jobs.values():
            if job.status == JobStatus.COMPUTING:
                job.status = JobStatus.FAILED
                job.error = "Server shutdown"

        for task in self._recompute_debounce_tasks.values():
            if not task.done():
                task.cancel()
        if self._recompute_debounce_tasks:
            await asyncio.gather(*self._recompute_debounce_tasks.values(), return_exceptions=True)
        self._recompute_debounce_tasks.clear()
        for job in self._recompute_jobs.values():
            if job.status == JobStatus.COMPUTING:
                job.status = JobStatus.FAILED
                job.error = "Server shutdown"


# Module-level singleton
job_tracker = JobTracker()
