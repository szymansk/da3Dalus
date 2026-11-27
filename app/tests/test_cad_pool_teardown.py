"""gh-1475: a CAD worker that is still busy must not outlive its test."""

from __future__ import annotations

import time

from app.services import cad_service
from app.tests.conftest import terminate_cad_pool_workers


def _busy(seconds: float) -> float:
    time.sleep(seconds)
    return seconds


def test_busy_worker_is_killed_by_teardown():
    pool = cad_service._get_executor()
    future = pool.submit(_busy, 600.0)
    deadline = time.monotonic() + 60.0
    while not getattr(pool, "_processes", None) and time.monotonic() < deadline:
        time.sleep(0.1)
    workers = list(pool._processes.values())
    assert workers, "the pool did not start a worker"
    assert all(w.is_alive() for w in workers)

    # The TestClient's lifespan shutdown drops the pool reference before the autouse
    # fixture tears down, so the helper must not depend on ``cad_service._executor``.
    cad_service.shutdown_executor()
    terminate_cad_pool_workers()

    assert not any(w.is_alive() for w in workers)
    assert cad_service._executor is None
