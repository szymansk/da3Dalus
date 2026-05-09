"""Tests for app/core/background_jobs.py — background job tracker with debounce."""

from __future__ import annotations

import asyncio

from app.core.background_jobs import JobStatus, JobTracker, RetrimJob, job_tracker


def _run(coro):
    """Run an async coroutine in a new event loop (no pytest-asyncio needed)."""
    return asyncio.run(coro)


class TestRetrimJobDataclass:
    def test_defaults(self):
        job = RetrimJob(aeroplane_id=1)
        assert job.aeroplane_id == 1
        assert job.status == JobStatus.DEBOUNCING
        assert job.dirty_op_ids == []
        assert job.completed_op_ids == []
        assert job.failed_op_ids == []
        assert job.started_at is None
        assert job.finished_at is None
        assert job.error is None


class TestJobTrackerSchedule:
    """Test scheduling and debounce behavior."""

    def test_schedule_creates_debouncing_job(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 0.05
            tracker.schedule_retrim(42)

            job = tracker.get_job(42)
            assert job is not None
            assert job.status == JobStatus.DEBOUNCING
            assert tracker.is_active(42)
            assert tracker.is_debouncing(42)

            await tracker.shutdown()

        _run(_test())

    def test_debounce_resets_on_reschedule(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 0.1

            call_count = 0

            async def mock_trim(aeroplane_id: int) -> None:
                nonlocal call_count
                call_count += 1

            tracker.set_trim_function(mock_trim)
            tracker.schedule_retrim(1)
            await asyncio.sleep(0.05)
            # Reschedule — should cancel the first debounce
            tracker.schedule_retrim(1)
            await asyncio.sleep(0.15)

            # Trim function should only have been called once (the second schedule)
            assert call_count == 1

            await tracker.shutdown()

        _run(_test())

    def test_job_lifecycle_debouncing_to_done(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 0.05

            async def mock_trim(aeroplane_id: int) -> None:
                pass

            tracker.set_trim_function(mock_trim)
            tracker.schedule_retrim(1)

            # Wait for debounce + execution
            await asyncio.sleep(0.2)

            job = tracker.get_job(1)
            assert job is not None
            assert job.status == JobStatus.DONE
            assert job.started_at is not None
            assert job.finished_at is not None
            assert not tracker.is_active(1)

            await tracker.shutdown()

        _run(_test())

    def test_job_lifecycle_failed(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 0.05

            async def failing_trim(aeroplane_id: int) -> None:
                raise RuntimeError("Trim computation failed")

            tracker.set_trim_function(failing_trim)
            tracker.schedule_retrim(1)

            await asyncio.sleep(0.2)

            job = tracker.get_job(1)
            assert job is not None
            assert job.status == JobStatus.FAILED
            assert job.error == "Trim computation failed"
            assert not tracker.is_active(1)

            await tracker.shutdown()

        _run(_test())


class TestJobTrackerStateQueries:
    """Test is_active / is_debouncing state queries."""

    def test_is_active_false_for_unknown(self):
        tracker = JobTracker()
        assert not tracker.is_active(999)

    def test_is_debouncing_false_for_unknown(self):
        tracker = JobTracker()
        assert not tracker.is_debouncing(999)

    def test_get_job_none_for_unknown(self):
        tracker = JobTracker()
        assert tracker.get_job(999) is None

    def test_is_active_false_after_done(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 0.05

            async def mock_trim(aeroplane_id: int) -> None:
                pass

            tracker.set_trim_function(mock_trim)
            tracker.schedule_retrim(1)
            await asyncio.sleep(0.2)

            assert not tracker.is_active(1)
            assert not tracker.is_debouncing(1)

            await tracker.shutdown()

        _run(_test())


class TestJobTrackerShutdown:
    """Test shutdown behavior."""

    def test_shutdown_cancels_debouncing_tasks(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 10.0  # long debounce — will be cancelled

            tracker.schedule_retrim(1)
            assert tracker.is_active(1)

            await tracker.shutdown()
            # Debounce tasks dict should be cleared
            assert len(tracker._debounce_tasks) == 0

        _run(_test())

    def test_shutdown_marks_computing_jobs_failed(self):
        async def _test():
            tracker = JobTracker()
            # Manually set a job to COMPUTING to test shutdown behavior
            tracker._jobs[1] = RetrimJob(aeroplane_id=1, status=JobStatus.COMPUTING)

            await tracker.shutdown()

            job = tracker.get_job(1)
            assert job.status == JobStatus.FAILED
            assert job.error == "Server shutdown"

        _run(_test())


class TestConcurrentAeroplanes:
    """Test that independent aeroplanes have independent jobs."""

    def test_independent_aeroplanes(self):
        async def _test():
            tracker = JobTracker()
            tracker.debounce_seconds = 0.05

            results = {}

            async def mock_trim(aeroplane_id: int) -> None:
                results[aeroplane_id] = True

            tracker.set_trim_function(mock_trim)
            tracker.schedule_retrim(1)
            tracker.schedule_retrim(2)

            await asyncio.sleep(0.2)

            assert results.get(1) is True
            assert results.get(2) is True
            assert tracker.get_job(1).status == JobStatus.DONE
            assert tracker.get_job(2).status == JobStatus.DONE

            await tracker.shutdown()

        _run(_test())


class TestRetrimJobTracking:
    """Test that RetrimJob tracking lists work correctly."""

    def test_tracking_lists_are_lists(self):
        job = RetrimJob(aeroplane_id=1)
        job.dirty_op_ids = [10, 20, 30]
        job.completed_op_ids = [10, 20]
        job.failed_op_ids = [30]
        assert len(job.dirty_op_ids) == 3
        assert len(job.completed_op_ids) == 2
        assert len(job.failed_op_ids) == 1

    def test_tracking_lists_independent_per_job(self):
        job_a = RetrimJob(aeroplane_id=1)
        job_b = RetrimJob(aeroplane_id=2)
        job_a.dirty_op_ids = [10, 20]
        assert job_b.dirty_op_ids == []


class TestModuleLevelSingleton:
    def test_job_tracker_is_instance(self):
        assert isinstance(job_tracker, JobTracker)
