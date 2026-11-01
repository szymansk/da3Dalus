"""The public entry points of the kernel (ARCHITECTURE ch. 8.4): ``compute`` and ``CachedKernel``.

``compute`` is stateless; ``CachedKernel`` is the stateful facade with the node cache. Both run the
same engine.
"""

import logging
import secrets
import time
from typing import Self

from aero_kernel.build import Build, shipped_build
from aero_kernel.cache import DedupedCache, MemoryCache, NodeCache, build_digest
from aero_kernel.canon.load import CanonLoadError
from aero_kernel.context import Solvers
from aero_kernel.engine import evaluate, log_call
from aero_kernel.rules import Rules
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    Provenance,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.solvers.aero_model import MAX_MODELS_PER_WORKER
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.solvers.opti import OptiAdapter

logger = logging.getLogger(__name__)

__all__ = ["CachedKernel", "compute"]


async def compute(
    aircraft: AircraftInput,
    request: ComputeRequest,
    *,
    max_workers: int | None = None,
    max_concurrency: int | None = None,
) -> ComputeResult:
    """Compute the requested quantities of an aircraft.

    Stateless: nothing is kept between calls except the immutable shipped build; no cache and no
    deduplication, so two calls with the same input compute twice and ``from_cache`` is always
    false. It never raises for a computational failure; everything is in the result. The call
    owns its solver runtime and releases it before returning (ch. 8.10).

    Args:
        aircraft: The geometry and the input and target values, in canon units.
        request: The canon quantity slugs to compute.
        max_workers: Worker processes of the call's runtime; default ``os.cpu_count()``.
        max_concurrency: Concurrent solver calls; default ``os.cpu_count()``.

    Returns:
        One result per requested slug in request order, or ``input_errors`` and nothing computed.
        If the shipped canon model cannot be loaded, every quantity is ``internal`` and escalates.

    Raises:
        ValueError: If a limit is below 1.
    """
    _check_limits(max_workers=max_workers, max_concurrency=max_concurrency)
    return await _compute(
        aircraft,
        request,
        None,
        None,
        limits=(max_workers, max_concurrency),
    )


def _check_limits(**limits: int | None) -> None:
    """Refuse a resource limit below 1, before anything starts.

    Raises:
        ValueError: Naming the first limit below 1.
    """
    for name, value in limits.items():
        if value is not None and value < 1:
            msg = f"{name} must be >= 1, got {value}"
            raise ValueError(msg)


class CachedKernel:
    """The stateful facade (ch. 8.4): the same ``compute``, with a node-level cache.

    It owns one in-memory LRU cache and the in-flight deduplication (:class:`DedupedCache`) and
    passes them into the same engine as the stateless :func:`compute`; caching happens per graph
    node, so a changed input expires only its subtree (A1). The values are those of a
    recomputation, bit for bit; a quantity served from the cache says so (``from_cache``) and
    reports the run time measured when it was computed. There is no ``refresh``: every reason to
    recompute is in the key, and a forced recomputation is the stateless :func:`compute`.

    It also owns one :class:`SolverRuntime` for its lifetime (ch. 8.10): the worker processes,
    each with its cache of AeroBuildup model functions, and the concurrency limit. The runtime is
    created on the first compute and closed by :meth:`aclose` or ``async with``; a closed facade
    refuses work. Resources are not results: they never change a value.

    One facade serves one event loop at a time (the in-flight runs are ``asyncio`` futures, and
    the runtime's limits are bound to the loop of its first call).
    """

    def __init__(
        self,
        *,
        max_entries: int,
        max_models_per_worker: int = MAX_MODELS_PER_WORKER,
        max_workers: int | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        """Create the facade with an empty cache; no worker starts yet.

        All settings are passed here, never read from the environment.

        Args:
            max_entries: Nodes kept; the least recently used one is evicted.
            max_models_per_worker: AeroBuildup model functions each worker process keeps (about
                280 MB each, ``aero_model.MAX_MODELS_PER_WORKER``).
            max_workers: Worker processes; default ``os.cpu_count()``.
            max_concurrency: Concurrent solver calls; default ``os.cpu_count()``.

        Raises:
            ValueError: If a limit is below 1.
        """
        self._cache = DedupedCache(MemoryCache(max_entries=max_entries))
        _check_limits(
            max_models_per_worker=max_models_per_worker,
            max_workers=max_workers,
            max_concurrency=max_concurrency,
        )
        self._max_models_per_worker = max_models_per_worker
        self._max_workers = max_workers
        self._max_concurrency = max_concurrency
        self._runtime: SolverRuntime | None = None
        self._closed = False

    async def __aenter__(self) -> Self:
        """Enter the ``async with`` block."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the facade when the block ends."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the facade's runtime: wait for its running calls, then stop its workers; idempotent.

        Afterwards the facade refuses work (``RuntimeError``); its cache is dropped with it.
        """
        self._closed = True
        runtime, self._runtime = self._runtime, None
        if runtime is not None:
            await runtime.aclose()

    def _runtime_for_call(self) -> SolverRuntime:
        """The facade's runtime, created on the first compute; never after closing."""
        if self._closed:
            msg = "the cached kernel is closed"
            raise RuntimeError(msg)
        if self._runtime is None:
            self._runtime = SolverRuntime(
                max_workers=self._max_workers,
                max_concurrency=self._max_concurrency,
                max_models_per_worker=self._max_models_per_worker,
            )
        return self._runtime

    async def compute(self, aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        """Compute the requested quantities of an aircraft, reading and writing the cache.

        Args:
            aircraft: The geometry and the input and target values, in canon units.
            request: The canon quantity slugs to compute.

        Returns:
            As :func:`compute`, with ``from_cache`` set on every quantity whose producing node was
            served from the cache.

        Raises:
            RuntimeError: If the facade is closed, or called from a second event loop while a run
                it deduplicates is in flight on the first.
        """
        return await _compute(aircraft, request, self._cache, self._runtime_for_call())


async def _compute(
    aircraft: AircraftInput,
    request: ComputeRequest,
    cache: NodeCache | None,
    runtime: SolverRuntime | None,
    *,
    limits: tuple[int | None, int | None] = (None, None),
) -> ComputeResult:
    """One call on the shipped build, with the facade's cache and runtime, or none of either.

    Without a runtime the call owns one with ``limits`` (``max_workers``, ``max_concurrency``)
    and releases it before returning (the stateless ``compute``); the facade's runtime outlives
    the call.
    """
    started = time.perf_counter()
    try:
        build = shipped_build()
    except CanonLoadError as exc:
        call_id = secrets.token_hex(4)
        logger.error(
            "the shipped canon model is not loaded; re-import it with `python -m aero_kernel.importer` "
            "or reinstall the package",
            exc_info=exc,
            extra={"call_id": call_id},
        )
        quantities = tuple(
            QuantityResult(
                slug=slug,
                status=QuantityStatus.ERROR,
                error=exc.error.model_copy(update={"quantity": slug}),
            )
            for slug in request.quantities
        )
        result = ComputeResult(
            quantities=quantities, provenance=Provenance(build_digest=build_digest())
        )
        log_call(call_id, request, result, started, "the shipped canon model is not loaded")
        return result
    if runtime is not None:
        return await _evaluate(build, aircraft, request, cache, runtime)
    # Resources are never global (ch. 8.10): the stateless call owns its runtime and releases it
    # before returning, also on cancellation.
    max_workers, max_concurrency = limits
    async with SolverRuntime(max_workers=max_workers, max_concurrency=max_concurrency) as own:
        return await _evaluate(build, aircraft, request, cache, own)


async def _evaluate(
    build: Build,
    aircraft: AircraftInput,
    request: ComputeRequest,
    cache: NodeCache | None,
    runtime: SolverRuntime,
) -> ComputeResult:
    """Run the engine with adapters on ``runtime``; the rule parameters are the call's own."""
    rules = Rules(build.model)
    return await evaluate(
        build,
        aircraft,
        request,
        solvers=Solvers(
            atmosphere=AtmosphereAdapter(runtime),
            opti=OptiAdapter(runtime),
            avl=AvlAdapter(runtime, rules),
            geometry=GeometryAdapter(runtime),
            rules=rules,
        ),
        cache=cache,
    )
