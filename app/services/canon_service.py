"""Expert View backend (gh-1282, ADR 0030): compute canon quantities of a reference-fleet aircraft.

The kernel's values are shown beside the app's own in this view only (ADR 0030); nothing computed
here is written back. Only the kernel's public API is used: ``compute``, ``CachedKernel``,
``schema``, ``evaluation`` and the reference fleet.

A compute goes through one process-wide :class:`CachedKernel` (gh-1332), so a node whose inputs did
not change is served from the kernel's cache; ``fresh`` requests the stateless ``compute`` instead.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import threading
from collections.abc import Coroutine
from typing import Any

from aero_kernel import CachedKernel, compute
from aero_kernel.evaluation import judge_result
from aero_kernel.reference_fleet import FleetMember, aircraft_input, flap_values
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityStatus,
    ReasonCode,
)
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import NotFoundError, ValidationError
from app.core.kernel_log_capture import capture_kernel_logs
from app.schemas.canon import CanonComputeRequest, CanonComputeResponse, CanonFleetEntry


# Nodes the process-wide kernel cache keeps (gh-1332). An entry is a node's outputs, warnings and
# thresholds as JSON text: about 1 KB for a scalar node, about 14 KB for a node that also returns
# its stall polar (161 angles of attack x 4 coefficients). 4096 entries are at most about 56 MB if
# every one held a polar, a few MB in practice (one polar per stall application, the rest scalars),
# and hold several hundred full Expert View computations.
KERNEL_CACHE_ENTRIES = 4096

KERNEL = CachedKernel(max_entries=KERNEL_CACHE_ENTRIES)


class _KernelLoop:
    """The one event loop the shared kernel runs on, in a daemon thread started on first use.

    ``CachedKernel`` deduplicates in-flight nodes with ``asyncio`` futures, which belong to one
    event loop, so every cached compute of the process runs on this loop. It is not the
    application's loop, so a long computation does not block request handling. The caller's
    context (the request's log sink) is carried into the kernel's task.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def _running(self) -> asyncio.AbstractEventLoop:
        """The kernel loop, started if it is not running yet."""
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name="aero-kernel", daemon=True).start()
                self._loop = loop
            return self._loop

    async def run(self, coroutine: Coroutine[Any, Any, ComputeResult]) -> ComputeResult:
        """Run a kernel coroutine on the kernel loop, in the caller's context, and await it."""
        loop = self._running()
        context = contextvars.copy_context()
        done: concurrent.futures.Future[ComputeResult] = concurrent.futures.Future()

        def start() -> None:
            task = loop.create_task(coroutine, context=context)
            task.add_done_callback(lambda finished: _settle(done, finished))

        loop.call_soon_threadsafe(start)
        return await asyncio.wrap_future(done)


def _settle(
    done: concurrent.futures.Future[ComputeResult], finished: asyncio.Task[ComputeResult]
) -> None:
    """Pass the outcome of the kernel task on to the caller's future, unless the caller left."""
    if done.cancelled():
        return
    if finished.cancelled():
        done.cancel()
    elif (error := finished.exception()) is not None:
        done.set_exception(error)
    else:
        done.set_result(finished.result())


_KERNEL_LOOP = _KernelLoop()


def list_fleet() -> list[CanonFleetEntry]:
    """The reference-fleet aircraft the Expert View can load."""
    return [
        CanonFleetEntry(
            id=member.fleet_id,
            name=member.display_name,
            mass_kg=member.mass_kg,
            flap_deflections=flap_values(member),
        )
        for member in FleetMember
    ]


def _kernel_request(request: CanonComputeRequest) -> ComputeRequest:
    """The kernel request, or a validation error for what the kernel refuses to build."""
    try:
        return ComputeRequest(
            quantities=tuple(request.quantities), include_long_runs=request.include_long_runs
        )
    except PydanticValidationError as exc:
        raise ValidationError(
            "Invalid compute request",
            {"errors": exc.errors(include_url=False, include_context=False)},
        ) from exc


def _run_fresh(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
    """Run the stateless kernel to completion on its own event loop, in the worker thread."""
    return asyncio.run(compute(aircraft, request))


async def _run_kernel(
    aircraft: AircraftInput, request: ComputeRequest, *, fresh: bool
) -> ComputeResult:
    """The kernel's result: recomputed by the stateless ``compute``, or through the shared cache."""
    if fresh:
        return await asyncio.to_thread(_run_fresh, aircraft, request)
    return await _KERNEL_LOOP.run(KERNEL.compute(aircraft, request))


def _needs_confirmation(result: ComputeResult) -> list[str]:
    """The requested quantities the kernel skipped because they take minutes."""
    return [
        q.slug
        for q in result.quantities
        if q.status is QuantityStatus.SKIPPED
        and q.reason is not None
        and q.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED
    ]


async def compute_canon(request: CanonComputeRequest) -> CanonComputeResponse:
    """Compute the requested quantities of a fleet aircraft with the kernel.

    The kernel never runs on the application's event loop, so a long computation does not block
    it. By default the request goes through the shared :class:`CachedKernel` on its own loop, and
    every node whose inputs did not change is served from the cache. With ``fresh`` the
    stateless ``compute`` recomputes everything in a worker thread.

    Args:
        request: The aircraft, the quantities, the caller's input values, the long-run flag and
            whether to bypass the cache.

    Returns:
        The kernel's results, Drela's verdicts for the requested quantities, the quantities that
        wait for a confirmation and the kernel's log records of this request.

    Raises:
        NotFoundError: If the fleet has no such aircraft.
        ValidationError: If the quantities cannot form a kernel request.
    """
    member = FleetMember.from_fleet_id(request.aircraft.fleet)
    if member is None:
        raise NotFoundError(entity="Fleet aircraft", resource_id=request.aircraft.fleet)
    kernel_request = _kernel_request(request)
    aircraft = aircraft_input(member, request.values)
    with capture_kernel_logs() as logs:
        result = await _run_kernel(aircraft, kernel_request, fresh=request.fresh)
        verdicts = judge_result(result, aircraft.airplane)
    requested = set(kernel_request.quantities)
    return CanonComputeResponse(
        quantities=list(result.quantities),
        input_errors=list(result.input_errors),
        provenance=result.provenance,
        verdicts=[v for v in verdicts if v.quantity in requested],
        needs_confirmation=_needs_confirmation(result),
        logs=list(logs),
    )
