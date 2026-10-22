"""The Opti adapter: the stall speed as an optimisation over AeroBuildup (ARCHITECTURE ch. 8.8).

The canon procedure (``stall-speed``, K32 / O3) and nothing else: an alpha sweep brackets the
first C_L extremum, IPOPT (``asb.Opti``) then minimises V on the branch before it, and one more
sweep at the resulting V_S gives the published polar at the Reynolds number of the stall. There is
no fixed point on V; the bracketing sweep is made once at a speed refined from a first estimate. An active bound at the optimum, a missing extremum or a failed solve is an
error, never a value (ADR 0020). The whole procedure is one pool job (a picklable worker).
"""

import logging
import math
import time
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import KernelWarning, Polar
from aero_kernel.solvers.aerobuildup import sweep_polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.solvers.base import SolverAdapter, regime_by_wing
from aero_kernel.solvers.stall_math import first_extremum_from_zero
from pydantic import BaseModel, ConfigDict, JsonValue

logger = logging.getLogger(__name__)

__all__ = ["OptiAdapter", "Stall", "StallRequest", "StallSolution", "stall_worker"]

# The sweep range of the canon: "the default sweep starts at -15 deg" (stall-speed.md, inverted
# application); the upper end leaves room past the stall for stall-onset-detection (D4).
ALPHA_MIN_DEG = -15.0
ALPHA_MAX_DEG = 25.0
# Sample spacing of the sweep (the prototype's 0.25 deg, scripts/canon_checks/*).
ALPHA_STEP_DEG = 0.25
# The lift coefficient assumed to choose the speed of the first bracketing sweep. It only fixes the
# Reynolds number at which the C_L extremum is first located; the sweep is repeated once at the speed
# that extremum implies, and the result is re-evaluated at V_S (postcondition
# ``optimum_at_first_cl_peak`` compares the two).
BRACKET_CL = 1.0
# Speed bounds of the solve: above Mach 0.6 AeroBuildup is beyond its validity (regime table,
# ADR 0028); the lower bound is far below any RC stall. A bound active at the optimum is an error.
V_MIN_MS = 1.0
V_MAX_MACH = 0.6
# IPOPT: iteration limit as in the survey scripts; the default convergence tolerance (1e-8).
MAX_ITERATIONS = 300
# The NeuralFoil model AeroBuildup evaluates its sections with. ASB's default is "small", the size
# the goldens were computed with; ARCHITECTURE 8.4 names the largest. The size is a maintainer
# decision (pending), recorded in Provenance.solver_settings so a changed size is visible.
NEURALFOIL_MODEL_SIZE = "small"
# A bound counts as active when the optimum lies within this fraction of the variable's range.
ACTIVE_BOUND_FRACTION = 1e-6


class StallRequest(BaseModel):
    """What the worker needs for one stall computation; plain data, picklable.

    Attributes:
        airplane: The geometry as evaluated (devices as configured).
        mass_kg: Aircraft mass in kg, > 0.
        gravity: Gravity in m/s^2, > 0.
        n_load: Load factor; the lift balance is ``L = n m g`` (negative: inverted flight).
        air: The air state.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    airplane: AirplaneGeometry
    mass_kg: float
    gravity: float
    n_load: float
    air: AirState


class StallSolution(BaseModel):
    """The solution of the stall problem.

    Attributes:
        v_s: Stall speed in m/s.
        cl_max: The lift coefficient at the optimum: C_L,max (n > 0) or C_L,min (n < 0).
        alpha_s: The angle of attack at the optimum in degrees.
        polar: The sweep at ``v_s``, with ``alpha_s`` among its samples.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    v_s: float
    cl_max: float
    alpha_s: float
    polar: Polar


class Stall(BaseModel):
    """A solution and the caveats of its operating point.

    Attributes:
        solution: The solved stall problem.
        warnings: Regime warnings (ADR 0028), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    solution: StallSolution
    warnings: tuple[KernelWarning, ...]


def _not_converged(message: str, hint: str, **detail: float | str) -> FormulaError:
    return FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", message, hint, detail=dict(detail)
    )


def _grid() -> list[float]:
    """The sweep angles: ALPHA_MIN_DEG to ALPHA_MAX_DEG in steps of ALPHA_STEP_DEG."""
    count = round((ALPHA_MAX_DEG - ALPHA_MIN_DEG) / ALPHA_STEP_DEG)
    return [ALPHA_MIN_DEG + k * ALPHA_STEP_DEG for k in range(count + 1)]


def _bracket(polar: Polar, upright: bool) -> int:
    """The sample index of the first C_L peak (upright) or trough (inverted) from alpha = 0.

    Raises:
        FormulaError: ``not_converged`` if the series does not turn inside the sampled range.
    """
    index = first_extremum_from_zero(polar.alpha_deg, polar.cl, upright=upright)
    if index is None:
        what = "peak" if upright else "trough"
        raise _not_converged(
            f"the lift coefficient has no {what} inside {ALPHA_MIN_DEG}..{ALPHA_MAX_DEG} deg",
            "the airplane does not stall inside the sampled angles of attack",
            alpha_min_deg=ALPHA_MIN_DEG,
            alpha_max_deg=ALPHA_MAX_DEG,
        )
    return index


def stall_worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
    """Solve the stall problem in the pool worker (canon ``stall-speed``).

    1. Sweep alpha at the bracketing speed and find the first C_L peak (n > 0) or trough (n < 0)
       from alpha = 0.
    2. Minimise V with IPOPT subject to ``L = n m g``, alpha restricted to the branch up to that
       extremum plus one sweep step.
    3. Refuse the solution if a bound is active at the optimum.
    4. Sweep again at V_S, with alpha_S among the samples: the published polar.

    Args:
        request: The problem.

    Returns:
        The solution with the worker's diagnostics.

    Raises:
        FormulaError: ``not_converged`` if the sweep has no extremum, the solve fails or ends on
            a bound.
    """
    started = time.perf_counter()
    asb = load_aerosandbox()
    air, upright = request.air, request.n_load > 0.0
    airplane = to_asb_airplane(request.airplane)
    lift = request.n_load * request.mass_kg * request.gravity
    grid = _grid()

    reference_area = float(airplane.s_ref)
    # The first C_L extremum moves with the Reynolds number, so the bracketing sweep is made at the
    # speed a first estimate implies (one refinement, not a loop); IPOPT's window is then one sweep
    # step wide around that extremum, and an optimum on its edge is an error.
    v_first = math.sqrt(2.0 * abs(lift) / (air.density * reference_area * BRACKET_CL))
    first = sweep_polar(airplane, air, v_first, grid, NEURALFOIL_MODEL_SIZE)
    cl_first = abs(first.cl[_bracket(first, upright)])
    v_bracket = math.sqrt(2.0 * abs(lift) / (air.density * reference_area * cl_first))
    bracket = sweep_polar(airplane, air, v_bracket, grid, NEURALFOIL_MODEL_SIZE)
    peak = _bracket(bracket, upright)
    alpha_peak = bracket.alpha_deg[peak]
    low, high = (
        (ALPHA_MIN_DEG, alpha_peak + ALPHA_STEP_DEG)
        if upright
        else (
            alpha_peak - ALPHA_STEP_DEG,
            ALPHA_MAX_DEG,
        )
    )
    v_low, v_high = V_MIN_MS, V_MAX_MACH * air.speed_of_sound

    opti = asb.Opti()
    speed = opti.variable(
        init_guess=min(max(v_bracket, v_low), v_high), lower_bound=v_low, upper_bound=v_high
    )
    alpha = opti.variable(init_guess=alpha_peak, lower_bound=low, upper_bound=high)
    aero = asb.AeroBuildup(
        airplane,
        asb.OperatingPoint(atmosphere=FixedAtmosphere(air), velocity=speed, alpha=alpha),
        model_size=NEURALFOIL_MODEL_SIZE,
    ).run()
    opti.subject_to(aero["L"] == lift)
    opti.minimize(speed)
    try:
        solved = opti.solve(verbose=False, max_iter=MAX_ITERATIONS)
    except RuntimeError as error:  # CasADi reports a failed IPOPT solve as a RuntimeError
        raise _not_converged(
            f"the stall problem did not converge: {error}",
            "check mass, wing area and the sampled angles of attack",
            solver_error=str(error)[:200],
        ) from error
    v_s, alpha_s = float(solved(speed)), float(solved(alpha))
    for name, value, bounds in (("V", v_s, (v_low, v_high)), ("alpha", alpha_s, (low, high))):
        margin = ACTIVE_BOUND_FRACTION * (bounds[1] - bounds[0])
        if value - bounds[0] < margin or bounds[1] - value < margin:
            raise _not_converged(
                f"the optimum of the stall problem lies on the bound of {name}",
                "the problem has no interior solution; a value on a bound is no stall speed",
                variable=name,
                value=value,
            )

    angles = sorted({*grid, alpha_s})
    polar = sweep_polar(airplane, air, v_s, angles, NEURALFOIL_MODEL_SIZE)
    cl_max = polar.cl[polar.alpha_deg.index(alpha_s)]
    solution = StallSolution(v_s=v_s, cl_max=cl_max, alpha_s=alpha_s, polar=polar)
    diagnostics = WorkerDiagnostics(
        duration_s=time.perf_counter() - started,
        solver_status="Solve_Succeeded",
        notes=(f"bracketed at {alpha_peak} deg with a sweep at {v_bracket:.3f} m/s",),
    )
    return WorkerOutcome(value=solution, diagnostics=diagnostics)


def _invalid(message: str, hint: str, parameter: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.INVALID_INPUT, "invalid_input", message, hint, parameter=parameter
    )


def _refuse_deflected_devices(airplane: AirplaneGeometry) -> None:
    """Refuse an airplane with a control device off its rest position.

    The conversion does not pass devices to AeroBuildup yet (it comes with the roll-rate step, where
    ailerons need it), so a deflected airplane would silently be evaluated as the clean one.

    Raises:
        FormulaError: ``unsupported_configuration`` naming the first deflected device and its role.
    """
    for key, wing in (airplane.wings or {}).items():
        for index, section in enumerate(wing.x_secs):
            device = section.trailing_edge_device
            if device is not None and device.deflection_deg:
                label = device.name or f"device {index}"
                raise FormulaError(
                    ErrorCategory.UNSUPPORTED_CONFIGURATION,
                    "unsupported_configuration",
                    f"deflected control surfaces are not yet passed to AeroBuildup: {label!r} "
                    f"(role {device.role}) of the wing {key!r} is at {device.deflection_deg} deg",
                    "no value is computed for a deflected configuration rather than the clean one",
                    detail={"wing": key, "device": label, "role": device.role},
                    parameter="airplane",
                )


class OptiAdapter(SolverAdapter):
    """The stall problem solved with IPOPT over AeroBuildup, in the process pool.

    Attributes:
        tool: ``OPT``.
        requirements: AeroSandbox.
    """

    tool: ClassVar[str] = "OPT"
    requirements: ClassVar[Mapping[str, str]] = {
        "aerosandbox": "aerosandbox",
        "neuralfoil": "neuralfoil",
    }

    def settings(self) -> dict[str, JsonValue]:
        """The NeuralFoil model size AeroBuildup is evaluated with."""
        return {"neuralfoil_model_size": NEURALFOIL_MODEL_SIZE}

    async def stall(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> Stall:
        """Solve ``min V s.t. L(V, alpha) = n m g`` on the branch before the first C_L extremum.

        Args:
            airplane: The geometry with its devices as they are to be evaluated.
            mass_kg: Mass in kg, > 0.
            gravity: Gravity in m/s^2, > 0.
            n_load: Load factor, finite and not 0 (negative for inverted flight).
            air: The air state.

        Returns:
            The solution and the regime warnings of its stall speed.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing; ``invalid_input`` for
                an inadmissible input; ``not_converged`` as :func:`stall_worker`.
        """
        self.require_available()
        _refuse_deflected_devices(airplane)
        for name, value, positive in (
            ("m", mass_kg, True),
            ("g", gravity, True),
            ("n_load", n_load, False),
        ):
            if not math.isfinite(value) or (value <= 0.0 if positive else value == 0.0):
                raise _invalid(f"{name} = {value} is not admissible", f"give a valid {name}", name)
        request = StallRequest(
            airplane=airplane, mass_kg=mass_kg, gravity=gravity, n_load=n_load, air=air
        )
        solution = await self.runtime.run_cpu(stall_worker, request)
        chords = {
            key: [s.chord for s in wing.x_secs] for key, wing in (airplane.wings or {}).items()
        }
        warnings = regime_by_wing(chords, solution.v_s, air.speed_of_sound, air.kinematic_viscosity)
        logger.debug("stall speed %.4f m/s at %.2f deg", solution.v_s, solution.alpha_s)
        return Stall(solution=solution, warnings=tuple(warnings))
