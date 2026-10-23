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
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

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
# The NeuralFoil model AeroBuildup evaluates its sections with: "xlarge", the author's default, at the
# knee of speed versus accuracy (Sharpe 2024, PhD thesis ch. 7, Table 7.1; maintainer decision
# 2026-10-22). The airfoil scoring (#821) uses "xxxlarge" on purpose: it is precomputed, so its
# cost does not matter. The size is a named constant recorded in Provenance.solver_settings; a
# caller-selectable accuracy level comes only when a caller needs it.
NEURALFOIL_MODEL_SIZE = "xlarge"
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


@dataclass(frozen=True)
class _Bracketed:
    """The airplane and the alpha window of a problem that lives on the pre-stall branch.

    Attributes:
        airplane: The ``asb.Airplane`` with the kernel's reference values.
        lift: The signed lift the balance asks for, ``n m g`` in N.
        v_bracket: The speed of the bracketing sweep in m/s.
        alpha_peak: The first C_L extremum of that sweep in degrees.
        low: Lower bound of alpha in degrees.
        high: Upper bound of alpha in degrees.
        v_low: Lower bound of the speed in m/s.
        v_high: Upper bound of the speed in m/s.
    """

    airplane: Any
    lift: float
    v_bracket: float
    alpha_peak: float
    low: float
    high: float
    v_low: float
    v_high: float


@dataclass(frozen=True)
class _Solved:
    """The optimum of one IPOPT run.

    Attributes:
        speed: The optimal speed in m/s.
        alpha: The optimal angle of attack in degrees.
        aero: The AeroBuildup result expressions, to be read at the optimum with :meth:`value`.
        value: Reads an expression of the problem at the optimum.
    """

    speed: float
    alpha: float
    aero: Any
    value: Callable[[Any], float]


def _bracketed(request: StallRequest) -> _Bracketed:
    """Locate the first C_L extremum and the bounds of the problem (canon K32).

    The first extremum moves with the Reynolds number, so the bracketing sweep is made at the speed
    a first estimate implies (one refinement, not a loop); the window of alpha is then one sweep
    step wide beyond that extremum, and an optimum on its edge is an error.

    Raises:
        FormulaError: ``not_converged`` if the sweep has no extremum.
    """
    air, upright = request.air, request.n_load > 0.0
    airplane = to_asb_airplane(request.airplane)
    lift = request.n_load * request.mass_kg * request.gravity
    grid = _grid()
    area = float(airplane.s_ref)
    v_first = math.sqrt(2.0 * abs(lift) / (air.density * area * BRACKET_CL))
    first = sweep_polar(airplane, air, v_first, grid, NEURALFOIL_MODEL_SIZE)
    cl_first = abs(first.cl[_bracket(first, upright)])
    v_bracket = math.sqrt(2.0 * abs(lift) / (air.density * area * cl_first))
    bracket = sweep_polar(airplane, air, v_bracket, grid, NEURALFOIL_MODEL_SIZE)
    alpha_peak = bracket.alpha_deg[_bracket(bracket, upright)]
    if upright:
        low, high = ALPHA_MIN_DEG, alpha_peak + ALPHA_STEP_DEG
    else:
        low, high = alpha_peak - ALPHA_STEP_DEG, ALPHA_MAX_DEG
    return _Bracketed(
        airplane=airplane,
        lift=lift,
        v_bracket=v_bracket,
        alpha_peak=alpha_peak,
        low=low,
        high=high,
        v_low=V_MIN_MS,
        v_high=V_MAX_MACH * air.speed_of_sound,
    )


def _solve(
    problem: _Bracketed,
    air: AirState,
    objective: Callable[[Any, Any], Any],
    init: tuple[float, float],
    what: str,
) -> _Solved:
    """Minimise ``objective(speed, aero)`` subject to ``L = lift`` on the bracketed window.

    Args:
        problem: The bracketed problem.
        air: The air state.
        objective: The expression to minimise, from the speed variable and the AeroBuildup result.
        init: The initial speed in m/s and angle of attack in degrees.
        what: The name of the problem, for the error messages.

    Raises:
        FormulaError: ``not_converged`` if IPOPT fails or the optimum lies on a bound.
    """
    asb = load_aerosandbox()
    opti = asb.Opti()
    speed = opti.variable(
        init_guess=min(max(init[0], problem.v_low), problem.v_high),
        lower_bound=problem.v_low,
        upper_bound=problem.v_high,
    )
    alpha = opti.variable(init_guess=init[1], lower_bound=problem.low, upper_bound=problem.high)
    aero = asb.AeroBuildup(
        problem.airplane,
        asb.OperatingPoint(atmosphere=FixedAtmosphere(air), velocity=speed, alpha=alpha),
        model_size=NEURALFOIL_MODEL_SIZE,
    ).run()
    opti.subject_to(aero["L"] == problem.lift)
    opti.minimize(objective(speed, aero))
    try:
        solved = opti.solve(verbose=False, max_iter=MAX_ITERATIONS)
    except RuntimeError as error:  # CasADi reports a failed IPOPT solve as a RuntimeError
        raise _not_converged(
            f"the {what} problem did not converge: {error}",
            "check mass, wing area and the sampled angles of attack",
            solver_error=str(error)[:200],
        ) from error
    v_opt, alpha_opt = float(solved(speed)), float(solved(alpha))
    bounds = (
        ("V", v_opt, (problem.v_low, problem.v_high)),
        ("alpha", alpha_opt, (problem.low, problem.high)),
    )
    for name, value, (lower, upper) in bounds:
        margin = ACTIVE_BOUND_FRACTION * (upper - lower)
        if value - lower < margin or upper - value < margin:
            raise _not_converged(
                f"the optimum of the {what} problem lies on the bound of {name}",
                "the problem has no interior solution; a value on a bound is no optimum",
                variable=name,
                value=value,
            )
    return _Solved(speed=v_opt, alpha=alpha_opt, aero=aero, value=lambda e: float(solved(e)))


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
    problem = _bracketed(request)
    optimum = _solve(
        problem,
        request.air,
        lambda speed, _aero: speed,
        (problem.v_bracket, problem.alpha_peak),
        "stall",
    )
    angles = sorted({*_grid(), optimum.alpha})
    polar = sweep_polar(problem.airplane, request.air, optimum.speed, angles, NEURALFOIL_MODEL_SIZE)
    cl_max = polar.cl[polar.alpha_deg.index(optimum.alpha)]
    solution = StallSolution(v_s=optimum.speed, cl_max=cl_max, alpha_s=optimum.alpha, polar=polar)
    diagnostics = WorkerDiagnostics(
        duration_s=time.perf_counter() - started,
        solver_status="Solve_Succeeded",
        notes=(
            f"bracketed at {problem.alpha_peak} deg with a sweep at {problem.v_bracket:.3f} m/s",
        ),
    )
    return WorkerOutcome(value=solution, diagnostics=diagnostics)


def _admissible(value: float, *, positive: bool) -> bool:
    """Whether a finite value is > 0 (``positive``) or merely not zero (a signed load factor)."""
    if not math.isfinite(value):
        return False
    return value > 0.0 if positive else abs(value) > 0.0


def _invalid(message: str, hint: str, parameter: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.INVALID_INPUT, "invalid_input", message, hint, parameter=parameter
    )


def _refuse_deflected_devices(airplane: AirplaneGeometry) -> None:
    """Refuse an airplane with a control device off its rest position.

    The conversion does not pass devices to AeroBuildup yet (it comes with the roll-rate step, where
    ailerons need it), so a deflected airplane would silently be evaluated as the clean one. Both
    state fields the conversion drops are checked: the device's ``deflection_deg`` and the
    aerodynamic view's ``control_surface.deflection``.

    Raises:
        FormulaError: ``unsupported_configuration`` naming the first deflected device and its role.
    """
    for key, wing in (airplane.wings or {}).items():
        for index, section in enumerate(wing.x_secs):
            device, surface = section.trailing_edge_device, section.control_surface
            if device is not None and device.deflection_deg:
                label, role, angle = (
                    device.name or f"device {index}",
                    device.role,
                    device.deflection_deg,
                )
            elif surface is not None and surface.deflection:
                label, role, angle = surface.name, "control_surface", surface.deflection
            else:
                continue
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "unsupported_configuration",
                f"deflected control surfaces are not yet passed to AeroBuildup: {label!r} "
                f"(role {role}) of the wing {key!r} is at {angle} deg",
                "no value is computed for a deflected configuration rather than the clean one",
                detail={"wing": key, "device": label, "role": role},
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
            if not _admissible(value, positive=positive):
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
