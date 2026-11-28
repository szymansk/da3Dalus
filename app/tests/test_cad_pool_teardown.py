"""gh-1475: a CAD worker that is still busy must not outlive the pool's shutdown."""

from __future__ import annotations

import time
from concurrent.futures.process import BrokenProcessPool

import pytest

from app.core import process_pool
from app.services import cad_service

BUSY_S = 30.0  # long against the test, short enough that a leftover worker ends by itself


def _busy(seconds: float) -> float:
    time.sleep(seconds)
    return seconds


def test_shutdown_ends_a_worker_that_is_still_busy():
    """``shutdown(wait=False)`` alone leaves a running worker alive; at interpreter exit
    ``concurrent.futures`` then joins the pool's manager thread, which waits for that worker,
    and the process does not end (the nightly test run, and a server asked to stop)."""
    pool = cad_service._get_executor()
    call = pool.submit(_busy, BUSY_S)
    # Only a call that was handed to a worker is the case in question; one still
    # waiting in the pool is merely cancelled by the shutdown.
    deadline = time.monotonic() + 20.0
    while not call.running() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert call.running(), "the call was not handed to a worker"
    workers = list(pool._processes.values())
    assert workers, "the pool did not start a worker"
    assert all(w.is_alive() for w in workers)

    cad_service.shutdown_executor()

    assert not any(w.is_alive() for w in workers)
    assert cad_service._executor is None
    with pytest.raises(BrokenProcessPool):
        call.result(timeout=10.0)


class _StubbornWorker:
    """A worker process that ignores ``terminate`` and ends only on ``kill``."""

    pid = 4711

    def __init__(self) -> None:
        self.alive = True
        self.calls: list[str] = []

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.calls.append("terminate")

    def kill(self) -> None:
        self.calls.append("kill")
        self.alive = False

    def join(self, timeout: float | None = None) -> None:
        self.calls.append("join")


def test_a_worker_that_ignores_terminate_is_killed(monkeypatch, caplog):
    monkeypatch.setattr(process_pool, "WORKER_GRACE_S", 0.0)
    worker = _StubbornWorker()
    with caplog.at_level("WARNING", logger=process_pool.logger.name):
        process_pool.end_workers([worker], pool_name="CAD")
    assert worker.calls == ["terminate", "join", "kill", "join"]
    assert not worker.is_alive()
    assert "did not end on terminate" in caplog.text
    assert "still alive after kill" not in caplog.text


def test_a_worker_that_survives_kill_is_reported(monkeypatch, caplog):
    monkeypatch.setattr(process_pool, "WORKER_GRACE_S", 0.0)
    worker = _StubbornWorker()
    worker.kill = lambda: worker.calls.append("kill")  # stays alive
    with caplog.at_level("WARNING", logger=process_pool.logger.name):
        process_pool.end_workers([worker], pool_name="CAD")
    assert "still alive after kill" in caplog.text


def test_a_worker_that_has_already_ended_is_left_alone():
    worker = _StubbornWorker()
    worker.alive = False
    process_pool.end_workers([worker], pool_name="CAD")
    assert worker.calls == ["join"]
