"""Top-level worker functions for the runtime tests; spawned processes import them by name."""

import logging
import os
import sys
import time

from aero_kernel.errors import ErrorCategory, FormulaError
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


def raise_formula() -> WorkerOutcome[int]:
    """Raise ``FormulaError`` the forbidden way: it does not survive pickling."""
    raise FormulaError(
        ErrorCategory.INVALID_INPUT, "missing_input", "worker lacks an input", "pass it"
    )


class UnpicklableError(Exception):
    """An exception that pickles but cannot be unpickled (``__init__`` needs two arguments)."""

    def __init__(self, first: str, second: str) -> None:
        """Keep only ``first`` in ``args``, so unpickling fails."""
        super().__init__(first)
        self.second = second


def raise_unpicklable() -> WorkerOutcome[int]:
    """Raise an exception that would break the result channel."""
    raise UnpicklableError("odd", "worker")


def parent_test_module_is_loaded() -> WorkerOutcome[bool]:
    """Report whether the worker inherited the parent's modules (true under fork).

    A spawned worker imports only what it unpickles, so the test module itself is absent; the
    parent's ``__main__`` re-import pulls in pytest even under spawn, so pytest proves nothing.
    """
    loaded = "aero_kernel.tests.test_runtime" in sys.modules
    return WorkerOutcome(value=loaded, diagnostics=WorkerDiagnostics(duration_s=0.0))


def logging_is_disabled() -> WorkerOutcome[bool]:
    """Report whether logging is switched off in the worker process."""
    disabled = not logging.getLogger("aero_kernel.worker_probe").isEnabledFor(logging.CRITICAL)
    return WorkerOutcome(value=disabled, diagnostics=WorkerDiagnostics(duration_s=0.0))
