"""The AeroBuildup adapter: an alpha sweep of the whole airplane (ARCHITECTURE ch. 8.8, 8.10).

AeroBuildup runs in the runtime's process pool (CasADi and numpy do not release the GIL); the
worker is a module-level function over plain data. Regime warnings (ADR 0028) are raised here,
where the operating point is known; they carry no origin, the engine sets it.
"""

import logging
import math
import time
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import ClassVar

import numpy as np
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import KernelWarning, Polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.solvers.base import SolverAdapter, regime
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = ["AeroBuildupAdapter", "Sweep", "SweepRequest", "sweep_polar", "sweep_worker"]


class SweepRequest(BaseModel):
    """What the worker needs for one sweep; plain data, picklable.

    Attributes:
        airplane: The geometry (devices as they are to be evaluated).
        velocity_ms: True airspeed in m/s.
        alphas_deg: Angles of attack in degrees, strictly rising.
        air: The air the airplane flies in.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    airplane: AirplaneGeometry
    velocity_ms: float
    alphas_deg: tuple[float, ...]
    air: AirState


class Sweep(BaseModel):
    """A sweep and the caveats of its operating point.

    Attributes:
        polar: The sampled polar (the solver's own CL, CD, Cm).
        warnings: Regime warnings (ADR 0028), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    polar: Polar
    warnings: tuple[KernelWarning, ...]


def sweep_polar(
    asb_airplane: object, air: AirState, velocity_ms: float, alphas_deg: Sequence[float]
) -> Polar:
    """Run AeroBuildup over the angles of attack on an already converted airplane.

    The one place that evaluates AeroBuildup in a fixed air state, shared by the sweep and the
    stall worker (ADR 0022). Runs in a pool worker.

    Args:
        asb_airplane: The ``asb.Airplane`` (from :func:`to_asb_airplane`).
        air: The air state.
        velocity_ms: True airspeed in m/s.
        alphas_deg: Angles of attack in degrees, strictly rising.

    Returns:
        The polar (CL, CD, Cm as AeroBuildup computes them).
    """
    asb = load_aerosandbox()
    alphas = np.asarray(alphas_deg, dtype=float)
    result = asb.AeroBuildup(
        asb_airplane,
        asb.OperatingPoint(
            atmosphere=FixedAtmosphere(air),
            velocity=np.full_like(alphas, velocity_ms),
            alpha=alphas,
        ),
    ).run()
    return Polar(
        alpha_deg=tuple(float(a) for a in alphas_deg),
        cl=tuple(float(v) for v in result["CL"]),
        cd=tuple(float(v) for v in result["CD"]),
        cm=tuple(float(v) for v in result["Cm"]),
    )


def sweep_worker(request: SweepRequest) -> WorkerOutcome[Polar]:
    """Run AeroBuildup over the angles of attack in the pool worker.

    Args:
        request: The sweep.

    Returns:
        The polar, with the worker's diagnostics.
    """
    started = time.perf_counter()
    polar = sweep_polar(
        to_asb_airplane(request.airplane), request.air, request.velocity_ms, request.alphas_deg
    )
    diagnostics = WorkerDiagnostics(duration_s=time.perf_counter() - started)
    return WorkerOutcome(value=polar, diagnostics=diagnostics)


def _invalid(message: str, hint: str, parameter: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.INVALID_INPUT, "invalid_input", message, hint, parameter=parameter
    )


class AeroBuildupAdapter(SolverAdapter):
    """AeroBuildup over angle of attack, in the process pool.

    Attributes:
        tool: ``AB``.
        requirements: AeroSandbox.
    """

    tool: ClassVar[str] = "AB"
    requirements: ClassVar[Mapping[str, str]] = {"aerosandbox": "aerosandbox"}

    async def sweep(
        self,
        airplane: AirplaneGeometry,
        velocity_ms: float,
        alphas_deg: Sequence[float],
        air: AirState,
    ) -> Sweep:
        """Evaluate the airplane at one speed over a range of angles of attack.

        Args:
            airplane: The geometry with its devices as they are to be evaluated.
            velocity_ms: True airspeed in m/s, > 0.
            alphas_deg: Angles of attack in degrees, at least two, strictly rising.
            air: The air state.

        Returns:
            The polar and the regime warnings of the operating point.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing; ``invalid_input`` for
                an inadmissible speed or angle range.
        """
        self.require_available()
        if not math.isfinite(velocity_ms) or velocity_ms <= 0.0:
            raise _invalid(
                f"the airspeed {velocity_ms} m/s is not > 0", "give a positive speed", "v"
            )
        alphas = tuple(float(a) for a in alphas_deg)
        if len(alphas) < 2 or any(not math.isfinite(a) for a in alphas):
            raise _invalid(
                "a sweep needs at least two finite angles", "give two or more angles", "alpha"
            )
        if any(b <= a for a, b in pairwise(alphas)):
            raise _invalid("the angles of a sweep must rise strictly", "sort the angles", "alpha")
        request = SweepRequest(
            airplane=airplane, velocity_ms=velocity_ms, alphas_deg=alphas, air=air
        )
        polar = await self.runtime.run_cpu(sweep_worker, request)
        chords = [s.chord for wing in (airplane.wings or {}).values() for s in wing.x_secs]
        warnings = regime(chords, velocity_ms, air.speed_of_sound, air.kinematic_viscosity)
        logger.debug("sweep at %s m/s over %d angles", velocity_ms, len(alphas))
        return Sweep(polar=polar, warnings=tuple(warnings))
