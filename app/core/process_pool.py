"""Ending the worker processes of a ``ProcessPoolExecutor`` at shutdown.

``shutdown(wait=False, cancel_futures=True)`` only stops a pool from taking new
work: a worker that is inside a call keeps running, and at interpreter exit
``concurrent.futures`` joins the pool's manager thread, which waits for that
worker. One call that never returns therefore keeps the whole process alive
(gh-1475). A pool is shut down because nobody will read its results any more,
so a call still running is ended; its future fails with ``BrokenProcessPool``.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing.process import BaseProcess

logger = logging.getLogger(__name__)

# Seconds a terminated worker gets before it is killed.
WORKER_GRACE_S = 5.0


def worker_table(executor: ProcessPoolExecutor) -> dict[int, BaseProcess]:
    """Return the pool's own pid -> process mapping; take it before ``shutdown``.

    ``shutdown`` drops the executor's reference to the mapping, so it has to be
    taken first. It is the live mapping, not a copy: a ``submit`` that races the
    shutdown can still start a worker, and that worker is in it once ``shutdown``
    has returned. There is no public accessor before Python 3.14
    (``terminate_workers``).
    """
    return getattr(executor, "_processes", None) or {}


def end_workers(workers: list[BaseProcess], *, pool_name: str) -> None:
    """Terminate the workers, and kill those that do not end within the grace time."""
    for worker in workers:
        if worker.is_alive():
            worker.terminate()
    for worker in workers:
        worker.join(timeout=WORKER_GRACE_S)
        if worker.is_alive():
            logger.warning(
                "%s worker %s did not end on terminate; killing it", pool_name, worker.pid
            )
            worker.kill()
            worker.join(timeout=WORKER_GRACE_S)
            if worker.is_alive():
                logger.error("%s worker %s is still alive after kill", pool_name, worker.pid)
