"""Top-level worker functions for the runtime tests; spawned processes import them by name."""

import os
import time

from aero_kernel.errors import ErrorCategory
from aero_kernel.runtime import WorkerDiagnostics, WorkerFailure, WorkerOutcome


def square(x: int) -> WorkerOutcome[int]:
    """Return ``x * x`` with diagnostics."""
    diagnostics = WorkerDiagnostics(
        duration_s=0.25, solver_status="ok", iterations=3, notes=("first", "second")
    )
    return WorkerOutcome(value=x * x, diagnostics=diagnostics)


def nap(seconds: float) -> WorkerOutcome[tuple[float, float]]:
    """Sleep without the GIL mattering; return the wall-clock start and end."""
    start = time.time()
    time.sleep(seconds)
    return WorkerOutcome(
        value=(start, time.time()), diagnostics=WorkerDiagnostics(duration_s=seconds)
    )


def expected_failure() -> WorkerFailure:
    """Report an expected failure the way a worker must (never raise ``FormulaError``)."""
    return WorkerFailure(
        category=ErrorCategory.NOT_CONVERGED,
        code="not_converged",
        message="the fake solver did not converge",
        hint="relax the tolerance",
        detail={"iterations": 50},
        diagnostics=WorkerDiagnostics(duration_s=0.1, solver_status="max_iter", iterations=50),
    )


def plain(x: int) -> int:
    """Violate the contract: return a bare value."""
    return x


def boom() -> WorkerOutcome[int]:
    """Raise an unexpected exception."""
    msg = "worker exploded"
    raise ValueError(msg)


def die() -> WorkerOutcome[int]:
    """Kill the worker process without cleanup."""
    os._exit(1)
