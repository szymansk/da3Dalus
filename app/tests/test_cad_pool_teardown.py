"""gh-1475: a CAD worker that is still busy must not outlive the pool's shutdown."""

from __future__ import annotations

import time

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
    pool.submit(_busy, BUSY_S)
    deadline = time.monotonic() + 20.0
    while not getattr(pool, "_processes", None) and time.monotonic() < deadline:
        time.sleep(0.1)
    workers = list(pool._processes.values())
    assert workers, "the pool did not start a worker"
    assert all(w.is_alive() for w in workers)

    cad_service.shutdown_executor()

    assert not any(w.is_alive() for w in workers)
    assert cad_service._executor is None
