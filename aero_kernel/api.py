"""The public entry point of the kernel: stateless ``compute`` (ARCHITECTURE ch. 8.4)."""

import logging
import secrets
import time

from aero_kernel.build import shipped_build
from aero_kernel.cache import build_digest
from aero_kernel.canon.load import CanonLoadError
from aero_kernel.context import Solvers
from aero_kernel.engine import evaluate, log_call
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

logger = logging.getLogger(__name__)

__all__ = ["compute"]


async def compute(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
    """Compute the requested quantities of an aircraft.

    Stateless: nothing is kept between calls except the immutable shipped build. It never raises
    for a computational failure; everything is in the result.

    Args:
        aircraft: The geometry and the input and target values, in canon units.
        request: The canon quantity slugs to compute.

    Returns:
        One result per requested slug in request order, or ``input_errors`` and nothing computed.
        If the shipped canon model cannot be loaded, every quantity is ``internal`` and escalates.
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
    # Resources are never global (ch. 8.10): this call owns its runtime and releases it before
    # returning, also on cancellation.
    async with SolverRuntime() as runtime:
        return await evaluate(
            build, aircraft, request, solvers=Solvers(atmosphere=AtmosphereAdapter(runtime))
        )
