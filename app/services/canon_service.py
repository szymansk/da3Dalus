"""Expert View backend (gh-1282, ADR 0030): compute canon quantities of an aircraft with the kernel.

The aircraft is one of the kernel's reference fleet or a stored aeroplane in its current state;
``canon_aeroplane_input`` is the one seam that turns a stored aeroplane into the kernel's input.

The kernel's values are shown beside the app's own in this view only (ADR 0030); nothing computed
here is written back. Only the kernel's public API is used: ``compute``, ``CachedKernel``,
``schema``, ``evaluation`` and the reference fleet.

A compute goes through one process-wide :class:`CachedKernel` (gh-1332), so a node whose inputs did
not change is served from the kernel's cache; ``fresh`` requests the stateless ``compute`` instead.
The kernel keeps its solver worker processes for its lifetime (gh-1336); :func:`close_kernel`
stops them on application shutdown.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

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
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.kernel_log_capture import capture_kernel_logs
from app.schemas.canon import (
    CanonAeroplaneEntry,
    CanonAeroplaneRef,
    CanonAircraftList,
    CanonComputeRequest,
    CanonComputeResponse,
    CanonFleetEntry,
)
from app.services.aeroplane_version_service import list_main_branch_heads
from app.services.canon_aeroplane_input import effective_mass_kg, stored_aircraft_input


# Nodes the process-wide kernel cache keeps (gh-1332). An entry is a node's outputs, warnings and
# thresholds as JSON text: about 1 KB for a scalar node, at most about 14 KB for a node that also
# returns its stall polar (161 angles of attack with C_L and C_D; measured while it still carried C_m,
# removed in #1347). 4096 entries are at most about 56 MB if
# every one held a polar, a few MB in practice (one polar per stall application, the rest scalars),
# and hold several hundred full Expert View computations.
KERNEL_CACHE_ENTRIES = 4096

# AeroBuildup model functions each kernel worker process keeps (gh-1336): about 280 MB RSS each
# (BRYAN and CHEKKER, NeuralFoil xlarge), so the kernel's model memory is at most
# KERNEL_WORKERS x 2 x ~280 MB. Two hold the clean and the configured airplane of one aircraft.
KERNEL_MODELS_PER_WORKER = 2

# Kernel worker processes, and concurrent solver calls, for the cached and the fresh compute alike
# (maintainer 2026-11-01: four, so the machine stays responsive): the model functions then take at
# most 4 x 2 x ~280 MB, about 2.2 GB, plus the solves in flight.
KERNEL_WORKERS = 4


def _new_kernel() -> CachedKernel:
    """The process-wide kernel, with every setting passed explicitly."""
    return CachedKernel(
        max_entries=KERNEL_CACHE_ENTRIES,
        max_models_per_worker=KERNEL_MODELS_PER_WORKER,
        max_workers=KERNEL_WORKERS,
        max_concurrency=KERNEL_WORKERS,
    )


KERNEL = _new_kernel()

_T = TypeVar("_T")


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

    def started(self) -> bool:
        """Whether the kernel loop has been started (by a first cached compute)."""
        with self._lock:
            return self._loop is not None

    async def run(self, coroutine: Coroutine[Any, Any, _T]) -> _T:
        """Run a kernel coroutine on the kernel loop, in the caller's context, and await it."""
        loop = self._running()
        context = contextvars.copy_context()
        done: concurrent.futures.Future[_T] = concurrent.futures.Future()

        def start() -> None:
            task = loop.create_task(coroutine, context=context)
            task.add_done_callback(lambda finished: _settle(done, finished))

        loop.call_soon_threadsafe(start)
        return await asyncio.wrap_future(done)


def _settle(done: concurrent.futures.Future[_T], finished: asyncio.Task[_T]) -> None:
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


async def close_kernel() -> None:
    """Close the process-wide kernel on application shutdown (gh-1336).

    The kernel's runtime and its worker processes belong to the kernel loop, so it is closed
    there; a kernel that never computed has nothing running and is closed directly. A fresh kernel
    takes its place, so a process that runs the application again (the test suite) still has one.
    """
    global KERNEL
    closing, KERNEL = KERNEL, _new_kernel()
    if _KERNEL_LOOP.started():
        await _KERNEL_LOOP.run(closing.aclose())
    else:
        await closing.aclose()


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


def list_aircraft(db: Session) -> CanonAircraftList:
    """The aircraft the Expert View can load: the reference fleet and the stored aeroplanes.

    A stored aeroplane is listed once, in its current state (the head of its main branch), with
    the mass the kernel gets for it.
    """
    return CanonAircraftList(
        fleet=list_fleet(),
        aeroplanes=[
            CanonAeroplaneEntry(
                id=aeroplane.uuid, name=aeroplane.name, mass_kg=effective_mass_kg(db, aeroplane)
            )
            for aeroplane in list_main_branch_heads(db)
        ],
    )


def _aircraft_input(request: CanonComputeRequest, db: Session) -> AircraftInput:
    """The kernel input of the requested aircraft, with the caller's values over its own."""
    if isinstance(request.aircraft, CanonAeroplaneRef):
        return stored_aircraft_input(db, request.aircraft.aeroplane, request.values)
    member = FleetMember.from_fleet_id(request.aircraft.fleet)
    if member is None:
        raise NotFoundError(entity="Fleet aircraft", resource_id=request.aircraft.fleet)
    return aircraft_input(member, request.values)


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
    return asyncio.run(
        compute(aircraft, request, max_workers=KERNEL_WORKERS, max_concurrency=KERNEL_WORKERS)
    )


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


async def compute_canon(request: CanonComputeRequest, db: Session) -> CanonComputeResponse:
    """Compute the requested quantities of a fleet aircraft or a stored aeroplane with the kernel.

    The kernel never runs on the application's event loop, so a long computation does not block
    it. By default the request goes through the shared :class:`CachedKernel` on its own loop, and
    every node whose inputs did not change is served from the cache. With ``fresh`` the
    stateless ``compute`` recomputes everything in a worker thread.

    Args:
        request: The aircraft, the quantities, the caller's input values, the long-run flag and
            whether to bypass the cache.
        db: The session a stored aeroplane is read from.

    Returns:
        The kernel's results, Drela's verdicts for the requested quantities, the quantities that
        wait for a confirmation and the kernel's log records of this request.

    Raises:
        NotFoundError: If the fleet or the database has no such aircraft.
        ValidationError: If the quantities cannot form a kernel request, or a stored aeroplane
            does not convert (its ``input_errors`` name each item by its input path).
    """
    aircraft = _aircraft_input(request, db)
    kernel_request = _kernel_request(request)
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
