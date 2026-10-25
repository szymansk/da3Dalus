"""The Opti adapter: optimisation problems over AeroBuildup (ARCHITECTURE ch. 8.8).

The canon procedure for stall speed (``stall-speed``, K32 / O3) and best glide
(``minimum-drag-speed-from-polar``): an alpha sweep brackets the first C_L extremum, IPOPT
(``asb.Opti``) then minimises V (stall) or D (best glide) on the branch before it. The stall adds one
more sweep at the resulting V_S, the published polar at the Reynolds number of the stall. There is
no fixed point on V; the bracketing sweep is made once at a speed refined from a first estimate. An
active bound at the optimum, a missing extremum or a failed solve is an error, never a value
(ADR 0020). Each problem is one pool job (a picklable worker).
"""

import logging
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, ClassVar, cast

import numpy as np
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import KernelWarning, Polar
from aero_kernel.solvers.aerobuildup import sweep_polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.solvers.base import SolverAdapter, regime_by_wing
from aero_kernel.solvers.devices import (
    refuse_deflected_devices,
    roll_hinge_warnings,
    roll_segments,
)
from aero_kernel.solvers.roll_math import (
    EFFECTIVENESS_EXPONENT,
    alpha_for_lift_coefficient,
    body_rates,
    control_effectiveness,
    stability_rolling_moment,
)
from aero_kernel.solvers.stall_math import first_extremum_from_zero
from pydantic import BaseModel, ConfigDict, JsonValue

logger = logging.getLogger(__name__)

__all__ = [
    "BestGlide",
    "BestGlideSolution",
    "DeflectionDiagnostics",
    "MinSink",
    "MinSinkSolution",
    "OptiAdapter",
    "RollRequest",
    "RollSolution",
    "Stall",
    "StallRequest",
    "StallSolution",
    "SteadyRoll",
    "SweepRequest",
    "best_glide_worker",
    "min_sink_worker",
    "stall_worker",
    "steady_roll_worker",
    "sweep_worker",
]

# The sweep range of the canon: "the default sweep starts at -15 deg" (stall-speed.md, inverted
# application); the upper end leaves room past the stall for stall-break (D4).
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
    """What the worker needs for one Opti problem (stall or best glide); plain data, picklable.

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


class SweepRequest(BaseModel):
    """What the worker needs for one alpha sweep; plain data, picklable.

    Attributes:
        airplane: The geometry as evaluated (devices as configured).
        air: The air state.
        v_ms: True airspeed in m/s, > 0.
        alphas_deg: Angles of attack in degrees, strictly rising.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    airplane: AirplaneGeometry
    air: AirState
    v_ms: float
    alphas_deg: tuple[float, ...]


class BestGlideSolution(BaseModel):
    """The solution of the best-glide problem (canon ``minimum-drag-speed-from-polar``).

    Attributes:
        v_md: Minimum-drag speed in m/s.
        e_max: The lift-to-drag ratio there, ``n m g / D``.
        alpha_md: The angle of attack at the optimum in degrees.
        cl_md: The lift coefficient at the optimum.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    v_md: float
    e_max: float
    alpha_md: float
    cl_md: float


class BestGlide(BaseModel):
    """A best-glide solution and the caveats of its operating point.

    Attributes:
        solution: The solved problem.
        warnings: Regime warnings (ADR 0028), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    solution: BestGlideSolution
    warnings: tuple[KernelWarning, ...]


class MinSinkSolution(BaseModel):
    """The solution of the minimum-sink problem (canon ``minimum-sink-speed-from-polar``).

    Attributes:
        v_mp: Minimum-sink speed in m/s.
        alpha_mp: The angle of attack at the optimum in degrees.
        cl_mp: The lift coefficient at the optimum.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    v_mp: float
    alpha_mp: float
    cl_mp: float


class MinSink(BaseModel):
    """A minimum-sink solution and the caveats of its operating point.

    Attributes:
        solution: The solved problem.
        warnings: Regime warnings (ADR 0028), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    solution: MinSinkSolution
    warnings: tuple[KernelWarning, ...]


class Stall(BaseModel):
    """A solution and the caveats of its operating point.

    Attributes:
        solution: The solved stall problem.
        warnings: Regime warnings (ADR 0028), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    solution: StallSolution
    warnings: tuple[KernelWarning, ...]


class RollRequest(BaseModel):
    """What the worker needs for the steady-roll problem; plain data, picklable.

    Attributes:
        airplane: The geometry as evaluated (devices at rest, ch. 8.11).
        mass_kg: Aircraft mass in kg, > 0.
        gravity: Gravity in m/s^2, > 0.
        air: The air state.
        v_ms: True airspeed in m/s, > 0.
        delta_deg: The aileron command in degrees (positive = right roll, ch. 8.8).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    airplane: AirplaneGeometry
    mass_kg: float
    gravity: float
    air: AirState
    v_ms: float
    delta_deg: float


class DeflectionDiagnostics(BaseModel):
    """What the deflected evaluation tells about NeuralFoil's validity (M1, ch. 8.8).

    Recorded over every section of every wing, not just the ailerons'.

    Attributes:
        min_confidence: The lowest ``analysis_confidence`` of any section call.
        min_confidence_wing: The wing key of that section.
        max_effective_alpha_deg: The highest angle ``alpha + sum(tau * delta)`` any section saw:
            the shift before NeuralFoil's 360-degree blend, which uses the unshifted angle for its
            post-stall weight and is no part of tau.
        max_effective_alpha_wing: The wing key of that section.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_confidence: float
    min_confidence_wing: str
    max_effective_alpha_deg: float
    max_effective_alpha_wing: str


class RollSolution(BaseModel):
    """The solution of the steady-roll problem.

    Attributes:
        p_rad_s: The roll rate about the stability x axis in rad/s (positive = right roll).
        alpha_deg: The angle of attack at the optimum in degrees.
        diagnostics: The deflected evaluation's diagnostics; ``None`` for a zero command.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    p_rad_s: float
    alpha_deg: float
    diagnostics: DeflectionDiagnostics | None


class SteadyRoll(BaseModel):
    """A steady roll and the caveats of its operating point.

    Attributes:
        p_rad_s: The roll rate about the stability x axis in rad/s (positive = right roll).
        alpha_deg: The angle of attack at the solution in degrees.
        warnings: The caveats (averaged hinge, deflection model, regime), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    p_rad_s: float
    alpha_deg: float
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


def _bracketed(request: StallRequest, *, peak_margin_deg: float = ALPHA_STEP_DEG) -> _Bracketed:
    """Locate the first C_L extremum and the bounds of the problem (canon K32).

    The first extremum moves with the Reynolds number, so the bracketing sweep is made at the speed
    a first estimate implies (one refinement, not a loop); the window of alpha then reaches
    ``peak_margin_deg`` beyond that extremum, and an optimum on its edge is an error.

    Args:
        request: The problem.
        peak_margin_deg: How far the window of alpha reaches past the first extremum. The stall and
            the best glide take one sweep step, which keeps an optimum at the extremum itself
            interior; a problem whose optimum must lie strictly before the stall takes 0.

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
        low, high = ALPHA_MIN_DEG, alpha_peak + peak_margin_deg
    else:
        low, high = alpha_peak - peak_margin_deg, ALPHA_MAX_DEG
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


# What the caller can do when IPOPT fails, per problem.
SPEED_HINT = "check mass, wing area and the sampled angles of attack"
ROLL_HINT = (
    "check mass and speed, or give a smaller aileron deflection: the roll equilibrium may not "
    "exist, or the solver may not reach it, at this command"
)


def _ipopt(opti: Any, what: str, hint: str) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """Run IPOPT on a problem; the solution is read with ``solved(variable_or_expression)``.

    Args:
        opti: The problem.
        what: The problem's name in the message.
        hint: What the caller can do, specific to the problem.

    Raises:
        FormulaError: ``not_converged`` if IPOPT fails.
    """
    try:
        return opti.solve(verbose=False, max_iter=MAX_ITERATIONS)
    except RuntimeError as error:  # CasADi reports a failed IPOPT solve as a RuntimeError
        raise _not_converged(
            f"the {what} problem did not converge: {error}",
            hint,
            solver_error=str(error)[:200],
        ) from error


def _reject_active_bound(name: str, value: float, bounds: tuple[float, float], what: str) -> None:
    """Refuse an optimum that lies on the bound of a variable (ADR 0020).

    Raises:
        FormulaError: ``not_converged`` naming the variable.
    """
    lower, upper = bounds
    margin = ACTIVE_BOUND_FRACTION * (upper - lower)
    if value - lower < margin or upper - value < margin:
        raise _not_converged(
            f"the optimum of the {what} problem lies on the bound of {name}",
            "the problem has no interior solution; a value on a bound is no optimum",
            variable=name,
            value=value,
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
    solved = _ipopt(opti, what, SPEED_HINT)
    v_opt, alpha_opt = float(solved(speed)), float(solved(alpha))
    _reject_active_bound("V", v_opt, (problem.v_low, problem.v_high), what)
    _reject_active_bound("alpha", alpha_opt, (problem.low, problem.high), what)
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
    diagnostics = _diagnostics(
        started,
        (f"bracketed at {problem.alpha_peak} deg with a sweep at {problem.v_bracket:.3f} m/s",),
    )
    return WorkerOutcome(value=solution, diagnostics=diagnostics)


def sweep_worker(request: SweepRequest) -> WorkerOutcome[Polar]:
    """Run AeroBuildup over the angles of one request in the pool worker (canon ``stall-break``).

    Args:
        request: The airplane, air state, speed and angles.

    Returns:
        The polar at that speed, with the worker's diagnostics.
    """
    started = time.perf_counter()
    polar = sweep_polar(
        to_asb_airplane(request.airplane),
        request.air,
        request.v_ms,
        request.alphas_deg,
        NEURALFOIL_MODEL_SIZE,
    )
    diagnostics = WorkerDiagnostics(duration_s=time.perf_counter() - started)
    return WorkerOutcome(value=polar, diagnostics=diagnostics)


# The first guess of the best-glide solve: V_md lies above the stall speed (1.48 times it for the
# BRYAN of the prototype); IPOPT only needs to start on the pre-stall branch.
GLIDE_SPEED_FACTOR = 1.4
# Start value of alpha for that solve, as a fraction of the first C_L peak's angle: a start only, not a
# result or a bound; the optimum is wherever IPOPT finds it inside the window. 0.4 made IPOPT report
# 'Infeasible_Problem_Detected' for BRYAN at exactly its mass (reference S_ref +0.06 %, gh-1262) while
# its neighbours 0.1 % either side converged; 0.3, 0.5 and 0.6 converged on all nine masses
# 0.99 ... 1.01 of both fleet members.
GLIDE_ALPHA_FRACTION = 0.5


def best_glide_worker(request: StallRequest) -> WorkerOutcome[BestGlideSolution]:
    """Solve the best-glide problem in the pool worker (canon ``minimum-drag-speed-from-polar``).

    The same bracketing as the stall (the window of alpha ends one sweep step past the first
    C_L peak), then IPOPT minimises ``D`` subject to ``L = n m g``. At fixed lift the minimum drag is
    the maximum lift-to-drag ratio. A bound active at the optimum is an error.

    Args:
        request: The problem; ``n_load`` must be positive.

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
        lambda _speed, aero: aero["D"],
        (GLIDE_SPEED_FACTOR * problem.v_bracket, GLIDE_ALPHA_FRACTION * problem.alpha_peak),
        "best-glide",
    )
    drag = optimum.value(optimum.aero["D"])
    solution = BestGlideSolution(
        v_md=optimum.speed,
        e_max=abs(problem.lift) / drag,
        alpha_md=optimum.alpha,
        cl_md=optimum.value(optimum.aero["CL"]),
    )
    diagnostics = _diagnostics(started)
    return WorkerOutcome(value=solution, diagnostics=diagnostics)


# The first guess of the minimum-sink solve: for a parabolic polar V_mp = V_md / 3^(1/4) = 0.76 V_md,
# so it lies between the stall speed and the best-glide start; IPOPT only needs to start on the
# pre-stall branch. Start values only, not results or bounds.
SINK_SPEED_FACTOR = 1.15
SINK_ALPHA_FRACTION = 0.6


def min_sink_worker(request: StallRequest) -> WorkerOutcome[MinSinkSolution]:
    """Solve the minimum-sink problem in the pool worker (canon ``minimum-sink-speed-from-polar``).

    The same bracketing as the stall, but the window of alpha ends at the first C_L peak itself,
    then IPOPT minimises ``D V`` subject to ``L = n m g``. At fixed weight ``D V`` is proportional
    to the sink rate, and AeroBuildup forms the Reynolds number from ``V`` inside the constraint.
    The peak is the end of the pre-stall branch: a polar whose sink rate is still falling there has
    its minimum limited by the stall, not at an interior optimum, and that optimum sits on the bound
    of alpha. A bound active at the optimum is an error, never a value (no stall-limited
    substitute, ADR 0020).

    Args:
        request: The problem; ``n_load`` must be positive.

    Returns:
        The solution with the worker's diagnostics.

    Raises:
        FormulaError: ``not_converged`` if the sweep has no extremum, the solve fails or ends on
            a bound.
    """
    started = time.perf_counter()
    problem = _bracketed(request, peak_margin_deg=0.0)
    optimum = _solve(
        problem,
        request.air,
        lambda speed, aero: aero["D"] * speed,
        (SINK_SPEED_FACTOR * problem.v_bracket, SINK_ALPHA_FRACTION * problem.alpha_peak),
        "minimum-sink",
    )
    solution = MinSinkSolution(
        v_mp=optimum.speed,
        alpha_mp=optimum.alpha,
        cl_mp=optimum.value(optimum.aero["CL"]),
    )
    diagnostics = _diagnostics(started)
    return WorkerOutcome(value=solution, diagnostics=diagnostics)


@dataclass(frozen=True)
class _Seen:
    """What one section call of the recording pass saw (a wing key, a confidence, an angle)."""

    wing: str
    confidence: float
    effective_alpha: float


def _recording_airfoil(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    base: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    wing: str,
    seen: list[_Seen],
) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
    """An airfoil that behaves as ``base`` and records every NeuralFoil call (M1).

    AeroBuildup calls ``get_aero_from_neuralfoil`` on the airfoil of each section with the
    section's control surfaces (``aero_buildup.py:797-806``). The call returns the net's
    ``analysis_confidence`` (``kulfan_airfoil.py:446``); the effective angle is the one the net is
    given: ``alpha + sum(tau * delta)`` (``kulfan_airfoil.py:216-246``).
    """

    class Recording(asb.Airfoil):  # pyright: ignore[reportUntypedBaseClass]  # untyped aerosandbox
        """The recording subclass."""

        def get_aero_from_neuralfoil(self, **kwargs: object) -> dict[str, object]:
            # the untyped base class: its result is the net's dict of arrays
            result = cast(
                "dict[str, object]",
                super().get_aero_from_neuralfoil(**kwargs),  # pyright: ignore[reportUnknownMemberType]  # untyped base
            )
            # AeroBuildup passes a list of ``asb.ControlSurface`` (untyped boundary)
            surfaces = cast("Sequence[Any]", kwargs.get("control_surfaces") or [])
            shift = sum(
                control_effectiveness(float(surface.hinge_point)) * float(surface.deflection)
                for surface in surfaces
            )
            seen.append(
                _Seen(
                    wing=wing,
                    confidence=float(np.min(np.asarray(result["analysis_confidence"]))),
                    effective_alpha=float(np.max(np.asarray(kwargs["alpha"]))) + shift,
                )
            )
            return result

    return Recording(name=base.name, coordinates=base.coordinates)


def _deflection_diagnostics(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    request: RollRequest,
    airplane: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    solution: tuple[float, float],
) -> DeflectionDiagnostics:
    """One numeric AeroBuildup run at the optimum with every section's airfoil recording (M1).

    Args:
        asb: The ``aerosandbox`` module.
        request: The problem.
        airplane: The ``asb.Airplane`` the problem was solved on; its airfoils are replaced here.
        solution: The optimal stability-axis roll rate in rad/s and angle of attack in degrees.
    """
    seen: list[_Seen] = []
    keys = list((request.airplane.wings or {}).keys())
    for key, wing in zip(keys, airplane.wings, strict=True):
        for xsec in wing.xsecs:
            xsec.airfoil = _recording_airfoil(asb, xsec.airfoil, key, seen)
    p_s, alpha = solution
    p_body, r_body = body_rates(p_s, alpha, asb.numpy)
    asb.AeroBuildup(
        airplane,
        asb.OperatingPoint(
            atmosphere=FixedAtmosphere(request.air),
            velocity=request.v_ms,
            alpha=alpha,
            p=p_body,
            r=r_body,
        ),
        model_size=NEURALFOIL_MODEL_SIZE,
    ).run()
    lowest = min(seen, key=lambda record: record.confidence)
    highest = max(seen, key=lambda record: record.effective_alpha)
    return DeflectionDiagnostics(
        min_confidence=lowest.confidence,
        min_confidence_wing=lowest.wing,
        max_effective_alpha_deg=highest.effective_alpha,
        max_effective_alpha_wing=highest.wing,
    )


def _roll_window(request: RollRequest) -> tuple[float, float, float]:
    """The window of alpha on the pre-stall branch and the start value that carries the weight.

    One sweep at V on the clean airplane (D9): the window ends one step past the first C_L peak,
    the start is where the sweep reaches the C_L that carries ``m g``. The sweep is not made on
    the rolled airplane: with the deflection the curve has kinks (the down-going section's
    NeuralFoil curve is shifted by tau * delta) and its first local maximum lies far below the
    stall (measured: C_L 0.364 at 1 deg against a clean peak of 1.233 at 16 deg), so it brackets
    nothing. The window only keeps IPOPT on the physical branch; local stall under the deflection
    is reported by the diagnostics of the deflected evaluation (M1).

    Raises:
        FormulaError: ``not_converged`` if the sweep has no peak or never carries the weight
            before it.
    """
    air = request.air
    clean = to_asb_airplane(request.airplane)
    polar = sweep_polar(clean, air, request.v_ms, _grid(), NEURALFOIL_MODEL_SIZE)
    peak = _bracket(polar, upright=True)
    area = float(clean.s_ref)
    cl_needed = request.mass_kg * request.gravity / (0.5 * air.density * request.v_ms**2 * area)
    start = alpha_for_lift_coefficient(polar.alpha_deg, polar.cl, peak, cl_needed)
    if start is None:
        raise _not_converged(
            f"the airplane cannot carry its weight at {request.v_ms} m/s before the lift "
            f"coefficient peaks (C_L {cl_needed:.3f} needed, peak {polar.cl[peak]:.3f})",
            "the speed is below the stall speed; give a higher speed or a lighter airplane",
            cl_needed=cl_needed,
            cl_peak=polar.cl[peak],
        )
    return ALPHA_MIN_DEG, polar.alpha_deg[peak] + ALPHA_STEP_DEG, start


# Start value of the roll rate as a fraction of its window, used only if the secant estimate of the
# start below is degenerate: a start only, not a result.
ROLL_START_FRACTION = 0.1
# The probe of the secant estimate of the start: this fraction of the window of the roll rate.
ROLL_PROBE_FRACTION = 0.25
# The start never lies closer to the bound of the window than this fraction of it.
ROLL_START_LIMIT_FRACTION = 0.9


def _roll_start(
    asb: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    request: RollRequest,
    airplane: Any,  # noqa: ANN401  # untyped aerosandbox boundary
    alpha_start: float,
    p_limit: float,
) -> float:
    """The start of the stability-axis roll rate: the zero of the rolling moment at ``alpha_start``.

    Two numeric AeroBuildup runs at the start angle of attack, without roll and at a probe rate,
    give the stability-axis rolling moment at both; the secant through them has its zero at the
    start. IPOPT started from a fixed fraction of the window failed on BRYAN at 20 deg although the
    equilibrium exists and a start fraction of 0.2 to 0.5 reaches it (fractions 0.1 and 0.25 failed on
    other cases): the feasibility problem is start-dependent. The start is no result and changes
    none; if the secant is degenerate (no damping), the fixed fraction is the start.

    Args:
        asb: The ``aerosandbox`` module.
        request: The problem.
        airplane: The ``asb.Airplane`` with the deflection.
        alpha_start: The angle of attack that carries the weight on the clean sweep, in degrees.
        p_limit: The window of the roll rate in rad/s.

    Returns:
        The start of the stability-axis roll rate in rad/s, with the sign of the command.
    """
    sign = math.copysign(1.0, request.delta_deg)
    fallback = sign * ROLL_START_FRACTION * p_limit
    if abs(request.delta_deg) <= 0.0:  # no command (exactly zero): the rest, nothing to estimate
        return fallback
    probe = sign * ROLL_PROBE_FRACTION * p_limit

    def moment(p_stability: float) -> float:
        p_body, r_body = body_rates(p_stability, alpha_start, asb.numpy)
        result = asb.AeroBuildup(
            airplane,
            asb.OperatingPoint(
                atmosphere=FixedAtmosphere(request.air),
                velocity=request.v_ms,
                alpha=alpha_start,
                p=p_body,
                r=r_body,
            ),
            model_size=NEURALFOIL_MODEL_SIZE,
        ).run()
        return float(
            np.ravel(stability_rolling_moment(result["Cl"], result["Cn"], alpha_start, asb.numpy))[
                0
            ]
        )

    at_zero, at_probe = moment(0.0), moment(probe)
    slope = (at_probe - at_zero) / probe
    if not (math.isfinite(slope) and slope < 0.0):
        return fallback
    start = -at_zero / slope
    limit = ROLL_START_LIMIT_FRACTION * p_limit
    return sign * min(abs(start), limit) if start * sign > 0.0 else fallback


def steady_roll_worker(request: RollRequest) -> WorkerOutcome[RollSolution]:
    """Solve the steady roll in the pool worker (canon ``roll-rate``).

    1. One sweep at V on the clean airplane brackets the first C_L peak (D9, see
       :func:`_roll_window`).
    2. IPOPT finds alpha and the stability-axis roll rate ``p`` with ``L = m g`` and the
       stability-axis rolling moment ``Cl cos(alpha) + Cn sin(alpha) = 0`` (AVL's ``RM``,
       ``aoper.f:1120``); the body rates are ``p cos(alpha)`` and ``p sin(alpha)``; beta, q and the
       stability-axis yaw rate are zero. ``|p b / 2V| <= 1`` is a solver window, no physical claim.
    3. An optimum on a bound is an error (ADR 0020).
    4. For a non-zero command, one numeric run records the diagnostics of the deflection (M1).

    Args:
        request: The problem.

    Returns:
        The solution with the worker's diagnostics.

    Raises:
        FormulaError: ``not_converged`` if the sweep has no peak, the weight cannot be carried
            before it, the solve fails or ends on a bound.
    """
    started = time.perf_counter()
    asb = load_aerosandbox()
    airplane = to_asb_airplane(request.airplane, request.delta_deg)
    low, high, alpha_start = _roll_window(request)
    p_limit = 2.0 * request.v_ms / float(airplane.b_ref)
    opti = asb.Opti()
    alpha = opti.variable(init_guess=alpha_start, lower_bound=low, upper_bound=high)
    p_stability = opti.variable(
        init_guess=_roll_start(asb, request, airplane, alpha_start, p_limit),
        lower_bound=-p_limit,
        upper_bound=p_limit,
    )
    p_body, r_body = body_rates(p_stability, alpha, asb.numpy)
    aero = asb.AeroBuildup(
        airplane,
        asb.OperatingPoint(
            atmosphere=FixedAtmosphere(request.air),
            velocity=request.v_ms,
            alpha=alpha,
            p=p_body,
            r=r_body,
        ),
        model_size=NEURALFOIL_MODEL_SIZE,
    ).run()
    opti.subject_to(aero["L"] == request.mass_kg * request.gravity)
    opti.subject_to(stability_rolling_moment(aero["Cl"], aero["Cn"], alpha, asb.numpy) == 0)
    solved = _ipopt(opti, "steady-roll", ROLL_HINT)
    p_opt, alpha_opt = float(solved(p_stability)), float(solved(alpha))
    _reject_active_bound("p", p_opt, (-p_limit, p_limit), "steady-roll")
    _reject_active_bound("alpha", alpha_opt, (low, high), "steady-roll")
    recorded = (
        _deflection_diagnostics(asb, request, airplane, (p_opt, alpha_opt))
        if abs(request.delta_deg) > 0.0
        else None
    )
    solution = RollSolution(p_rad_s=p_opt, alpha_deg=alpha_opt, diagnostics=recorded)
    diagnostics = _diagnostics(
        started, (f"alpha window {low}..{high} deg, |p| window {p_limit:.3f} rad/s",)
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


def _admissible_or_zero(value: float, *, positive: bool) -> bool:
    """Whether a value is finite and > 0 (``positive``) or merely finite (a signed command)."""
    return math.isfinite(value) and (value > 0.0 if positive else True)


def _fit_range_warning(found: DeflectionDiagnostics) -> KernelWarning:
    """The declared caveat of the deflection model (ch. 8.8): its fit range is unknown."""
    return KernelWarning.of(
        "control_surface_fit_range_unknown",
        "AeroBuildup models the deflection as tau * delta added to the angle of attack of the "
        "clean airfoil, with a Hoerner drag factor; the delta range of the tau fit is unknown and "
        "flow separation is not modelled",
        detail={
            "min_confidence": found.min_confidence,
            "min_confidence_wing": found.min_confidence_wing,
            "max_effective_alpha_deg": found.max_effective_alpha_deg,
            "max_effective_alpha_wing": found.max_effective_alpha_wing,
        },
    )


def _regime_warnings(airplane: AirplaneGeometry, v_ms: float, air: AirState) -> list[KernelWarning]:
    """The regime warnings (ADR 0028) of every wing of the airplane at a speed."""
    chords = {key: [s.chord for s in wing.x_secs] for key, wing in (airplane.wings or {}).items()}
    return regime_by_wing(chords, v_ms, air.speed_of_sound, air.kinematic_viscosity)


def _diagnostics(started: float, notes: tuple[str, ...] = ()) -> WorkerDiagnostics:
    """The diagnostics of a worker whose IPOPT run succeeded."""
    return WorkerDiagnostics(
        duration_s=time.perf_counter() - started, solver_status="Solve_Succeeded", notes=notes
    )


class OptiAdapter(SolverAdapter):
    """The stall, best-glide and minimum-sink problems solved with IPOPT over AeroBuildup, in the process pool.

    ``stall`` minimises V, ``best_glide`` minimises D and ``min_sink`` minimises D V subject to the
    lift balance, all on the pre-stall branch bracketed by an alpha sweep (canon ``stall-speed``,
    ``minimum-drag-speed-from-polar`` and ``minimum-sink-speed-from-polar``).

    Attributes:
        tool: ``OPT``.
        requirements: AeroSandbox and NeuralFoil, the model AeroBuildup evaluates its sections with.
    """

    tool: ClassVar[str] = "OPT"
    requirements: ClassVar[Mapping[str, str]] = {
        "aerosandbox": "aerosandbox",
        "neuralfoil": "neuralfoil",
    }

    def settings(self) -> dict[str, JsonValue]:
        """Every constant that shapes an optimisation result: model size, alpha sweep, bounds, limits.

        The keys of this adapter's own constants carry the ``opt_`` prefix: the settings of all tools of a call
        share one dictionary. ``neuralfoil_model_size`` keeps its name, it is NeuralFoil's.
        The start values of the solves (``GLIDE_*``, ``ROLL_START_*``, ``ROLL_PROBE_*``) are not
        settings: they are starts only and not a result or a bound.
        """
        return {
            "neuralfoil_model_size": NEURALFOIL_MODEL_SIZE,
            "opt_alpha_min_deg": ALPHA_MIN_DEG,
            "opt_alpha_max_deg": ALPHA_MAX_DEG,
            "opt_alpha_step_deg": ALPHA_STEP_DEG,
            "opt_bracket_cl": BRACKET_CL,
            "opt_v_min_ms": V_MIN_MS,
            "opt_v_max_mach": V_MAX_MACH,
            "opt_max_iterations": MAX_ITERATIONS,
            "opt_active_bound_fraction": ACTIVE_BOUND_FRACTION,
            "opt_effectiveness_exponent": EFFECTIVENESS_EXPONENT,
        }

    def _request(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
        *,
        upright_only: bool = False,
    ) -> StallRequest:
        """Check the tool and the inputs of an Opti problem and build the worker's request.

        Raises:
            FormulaError: ``tool_unavailable``; ``unsupported_configuration`` for a deflected
                control surface; ``invalid_input`` for an inadmissible mass, gravity or load factor
                (``upright_only``: the load factor must be positive).
        """
        self.require_available()
        refuse_deflected_devices(airplane, "AeroBuildup")
        for name, value, positive in (
            ("m", mass_kg, True),
            ("g", gravity, True),
            ("n_load", n_load, upright_only),
        ):
            if not _admissible(value, positive=positive):
                raise _invalid(f"{name} = {value} is not admissible", f"give a valid {name}", name)
        return StallRequest(
            airplane=airplane, mass_kg=mass_kg, gravity=gravity, n_load=n_load, air=air
        )

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
        request = self._request(airplane, mass_kg, gravity, n_load, air)
        solution = await self.runtime.run_cpu(stall_worker, request)
        warnings = _regime_warnings(airplane, solution.v_s, air)
        logger.debug("stall speed %.4f m/s at %.2f deg", solution.v_s, solution.alpha_s)
        return Stall(solution=solution, warnings=tuple(warnings))

    async def best_glide(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> BestGlide:
        """Solve ``min D s.t. L(V, alpha) = n m g`` on the branch before the first C_L peak.

        Args:
            airplane: The geometry with its devices as they are to be evaluated.
            mass_kg: Mass in kg, > 0.
            gravity: Gravity in m/s^2, > 0.
            n_load: Load factor, > 0 (the problem lives on the upright branch).
            air: The air state.

        Returns:
            The solution and the regime warnings of its speed.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing; ``invalid_input`` for
                an inadmissible input; ``unsupported_configuration`` for a deflected control
                surface; ``not_converged`` as :func:`best_glide_worker`.
        """
        request = self._request(airplane, mass_kg, gravity, n_load, air, upright_only=True)
        solution = await self.runtime.run_cpu(best_glide_worker, request)
        warnings = _regime_warnings(airplane, solution.v_md, air)
        logger.debug("minimum-drag speed %.4f m/s at %.2f deg", solution.v_md, solution.alpha_md)
        return BestGlide(solution=solution, warnings=tuple(warnings))

    async def sweep(
        self,
        airplane: AirplaneGeometry,
        air: AirState,
        v_ms: float,
        alphas_deg: Sequence[float],
    ) -> Polar:
        """Run AeroBuildup over the given angles of attack at a fixed speed.

        Args:
            airplane: The geometry with its devices as they are to be evaluated.
            air: The air state.
            v_ms: True airspeed in m/s, > 0.
            alphas_deg: Angles of attack in degrees, finite and strictly rising.

        Returns:
            The polar at that speed (the solver's own values).

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing; ``invalid_input`` for an
                inadmissible speed or angle series; ``unsupported_configuration`` for a deflected
                control surface.
        """
        self.require_available()
        refuse_deflected_devices(airplane, "AeroBuildup")
        if not _admissible(v_ms, positive=True):
            raise _invalid(f"V = {v_ms} is not admissible", "give a finite speed above 0", "v_s")
        angles = tuple(alphas_deg)
        rising = all(b > a for a, b in pairwise(angles))
        if not angles or not rising or not all(math.isfinite(a) for a in angles):
            raise _invalid(
                "the angles of attack must be finite and strictly rising",
                "give at least one angle, rising",
                "alphas_deg",
            )
        request = SweepRequest(airplane=airplane, air=air, v_ms=v_ms, alphas_deg=angles)
        polar = await self.runtime.run_cpu(sweep_worker, request)
        logger.debug("sweep of %d angles at %.4f m/s", len(angles), v_ms)
        return polar

    async def min_sink(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> MinSink:
        """Solve ``min D V s.t. L(V, alpha) = n m g`` on the branch before the first C_L peak.

        Args:
            airplane: The geometry with its devices as they are to be evaluated.
            mass_kg: Mass in kg, > 0.
            gravity: Gravity in m/s^2, > 0.
            n_load: Load factor, > 0 (the problem lives on the upright branch).
            air: The air state.

        Returns:
            The solution and the regime warnings of its speed.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing; ``invalid_input`` for
                an inadmissible input; ``unsupported_configuration`` for a deflected control
                surface; ``not_converged`` as :func:`min_sink_worker`.
        """
        request = self._request(airplane, mass_kg, gravity, n_load, air, upright_only=True)
        solution = await self.runtime.run_cpu(min_sink_worker, request)
        warnings = _regime_warnings(airplane, solution.v_mp, air)
        logger.debug("minimum-sink speed %.4f m/s at %.2f deg", solution.v_mp, solution.alpha_mp)
        return MinSink(solution=solution, warnings=tuple(warnings))

    async def steady_roll(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        air: AirState,
        v_ms: float,
        delta_a_deg: float,
    ) -> SteadyRoll:
        """Solve the steady roll at the aileron command ``delta_a_deg`` (canon ``roll-rate``).

        Args:
            airplane: The geometry with its devices at rest (a deflected state is refused).
            mass_kg: Mass in kg, > 0.
            gravity: Gravity in m/s^2, > 0.
            air: The air state.
            v_ms: True airspeed in m/s, > 0.
            delta_a_deg: The aileron command in degrees, positive = roll to the right.

        Returns:
            The roll rate and the caveats: the averaged hinge, the deflection model's unknown fit
            range for a non-zero command, and the regime at V.

        Raises:
            FormulaError: ``tool_unavailable``; ``invalid_input`` for an inadmissible input or a
                roll device without a hinge; ``unsupported_configuration`` for a deflected
                geometry state or a roll device on an unmirrored wing; ``not_converged`` as
                :func:`steady_roll_worker`.
            ValueError: If a non-zero command is given to an airplane without a roll device (a
                defect of the caller; the canon's ``has_aileron`` condition prevents it).
        """
        self.require_available()
        refuse_deflected_devices(airplane, "AeroBuildup")
        for name, value, positive in (
            ("m", mass_kg, True),
            ("g", gravity, True),
            ("v", v_ms, True),
            ("delta_a", delta_a_deg, False),
        ):
            if not _admissible_or_zero(value, positive=positive):
                raise _invalid(f"{name} = {value} is not admissible", f"give a valid {name}", name)
        driven = roll_segments(airplane) if abs(delta_a_deg) > 0.0 else []
        if abs(delta_a_deg) > 0.0 and not driven:
            msg = "a non-zero aileron command needs a device acting as aileron"
            raise ValueError(msg)
        request = RollRequest(
            airplane=airplane,
            mass_kg=mass_kg,
            gravity=gravity,
            air=air,
            v_ms=v_ms,
            delta_deg=delta_a_deg,
        )
        solution = await self.runtime.run_cpu(steady_roll_worker, request)
        warnings = [*roll_hinge_warnings(driven)]
        if solution.diagnostics is not None:
            warnings.append(_fit_range_warning(solution.diagnostics))
        warnings += _regime_warnings(airplane, v_ms, air)
        logger.debug("steady roll %.4f rad/s at %.2f deg", solution.p_rad_s, solution.alpha_deg)
        return SteadyRoll(
            p_rad_s=solution.p_rad_s, alpha_deg=solution.alpha_deg, warnings=tuple(warnings)
        )
