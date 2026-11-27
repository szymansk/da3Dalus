"""gh-1475: an OP-generation worker that is still busy must not outlive the pool's shutdown.

The counterpart of ``test_cad_pool_teardown.py`` for the second process pool of the app.
"""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor

from app.services import operating_point_generator_service as opg

BUSY_S = 30.0  # long against the test, short enough that a leftover worker ends by itself


def _busy(seconds: float) -> float:
    time.sleep(seconds)
    return seconds


def test_shutdown_ends_a_worker_that_is_still_busy(monkeypatch):
    monkeypatch.setattr(opg, "_opg_worker_count", lambda: 1)
    opg.shutdown_opg_executor()
    pool = opg._get_opg_executor()  # spawns its workers eagerly
    assert isinstance(pool, ProcessPoolExecutor)
    pool.submit(_busy, BUSY_S)
    workers = list(pool._processes.values())
    assert workers, "the pool did not start a worker"
    assert all(w.is_alive() for w in workers)

    opg.shutdown_opg_executor()

    assert not any(w.is_alive() for w in workers)
    assert opg._opg_executor is None
