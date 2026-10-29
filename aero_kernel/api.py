"""The public entry points of the kernel (ARCHITECTURE ch. 8.4): ``compute`` and ``CachedKernel``.

``compute`` is stateless; ``CachedKernel`` is the stateful facade with the node cache. Both run the
same engine.
"""

import logging
import secrets
import time

from aero_kernel.build import shipped_build
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
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.solvers.opti import OptiAdapter

logger = logging.getLogger(__name__)

__all__ = ["CachedKernel", "compute"]


async def compute(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
    """Compute the requested quantities of an aircraft.

    Stateless: nothing is kept between calls except the immutable shipped build; no cache and no
    deduplication, so two calls with the same input compute twice and ``from_cache`` is always
    false. It never raises for a computational failure; everything is in the result.

    Args:
        aircraft: The geometry and the input and target values, in canon units.
        request: The canon quantity slugs to compute.

    Returns:
        One result per requested slug in request order, or ``input_errors`` and nothing computed.
        If the shipped canon model cannot be loaded, every quantity is ``internal`` and escalates.
    """
    return await _compute(aircraft, request, None)


class CachedKernel:
    """The stateful facade (ch. 8.4): the same ``compute``, with a node-level cache.

    It owns one in-memory LRU cache and the in-flight deduplication (:class:`DedupedCache`) and
    passes them into the same engine as the stateless :func:`compute`; caching happens per graph
    node, so a changed input expires only its subtree (A1). The values are those of a
    recomputation, bit for bit; a quantity served from the cache says so (``from_cache``) and
    reports the run time measured when it was computed. There is no ``refresh``: every reason to
    recompute is in the key, and a forced recomputation is the stateless :func:`compute`.

    One facade serves one event loop at a time (the in-flight runs are ``asyncio`` futures).
    """

    def __init__(self, *, max_entries: int) -> None:
        """Create the facade with an empty cache.

        Args:
            max_entries: Nodes kept; the least recently used one is evicted. Passed here, never
                read from the environment.

        Raises:
            ValueError: If the limit is below 1.
        """
        self._cache = DedupedCache(MemoryCache(max_entries=max_entries))

    async def compute(self, aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
        """Compute the requested quantities of an aircraft, reading and writing the cache.

        Args:
            aircraft: The geometry and the input and target values, in canon units.
            request: The canon quantity slugs to compute.

        Returns:
            As :func:`compute`, with ``from_cache`` set on every quantity whose producing node was
            served from the cache.

        Raises:
            RuntimeError: If the facade is called from a second event loop while a run it
                deduplicates is in flight on the first.
        """
        return await _compute(aircraft, request, self._cache)


async def _compute(
    aircraft: AircraftInput, request: ComputeRequest, cache: NodeCache | None
) -> ComputeResult:
    """One call on the shipped build, with the facade's cache or none."""
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
    # Resources are never global (ch. 8.10): this call owns its runtime and releases it before
    # returning, also on cancellation. The rule parameters are the call's too.
    rules = Rules(build.model)
    async with SolverRuntime() as runtime:
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
