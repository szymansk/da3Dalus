"""Canon formula ``stall-speed``: the stall problem and its checks (ARCHITECTURE ch. 8.5, 8.12).

The formula passes the airplane, the mass, the load factor and the ISA air state to the OPT adapter,
which runs the sweep, IPOPT and the re-sweep in the process pool (canon K32).

The postconditions read the polar the formula returns (the sweep at ``V_S``, with ``alpha_S`` among
its samples), so they need no solver access. Tolerances are numeric consistency of the solve (A10:
they decide whether the solver's own answer is self-consistent, not whether the aircraft is good).
"""

import math
from collections.abc import Mapping

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane, forward_warnings, number
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.registry import CheckResult, formula, postcondition
from aero_kernel.schema import Polar
from aero_kernel.solvers.opti import ALPHA_STEP_DEG
from aero_kernel.solvers.stall_math import first_extremum_from_zero

__all__ = [
    "alpha_range_past_inverted_stall",
    "cl_max_at_stall_reynolds_number",
    "optimum_at_first_cl_peak",
    "optimum_at_first_cl_trough",
    "stall_speed",
]

# Relative disagreement allowed between V_S and the closed form with the polar's C_L at alpha_S
# (the Probe of the canon entry). IPOPT's default convergence tolerance is 1e-8 on the scaled
# constraint, so 1e-6 leaves two decades for the scaling and the sweep's float rounding.
PROBE_TOLERANCE = 1e-6
# C_L,max may fall short of the sampled first peak by this much (absolute). alpha_S is itself a
# sample of the sweep at V_S, so the comparison is between two samples of one curve: the tolerance
# only absorbs numerical noise.
PEAK_TOLERANCE = 1e-6


@formula("stall-speed")
async def stall_speed(x: Inputs, ctx: Context) -> dict[str, float | Polar]:
    """The smallest speed at which the airplane still carries ``n m g``, and where it stalls.

    Args:
        x: ``airplane`` the geometry as configured for the application, ``m`` the mass in kg,
            ``g`` the gravity in m/s^2, ``n_load`` the load factor, and the ISA air state
            ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in m/s.
        ctx: The formula context; ``ctx.solvers.opti`` solves the problem.

    Returns:
        ``v_s`` in m/s, ``cl_max`` the lift coefficient at the optimum, ``alpha_s`` the optimum
        angle of attack in degrees and ``polar`` the sweep at ``v_s`` (the application exposes
        only what the canon binds).

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``not_converged``).
    """
    stall = await ctx.solvers.opti.stall(
        airplane(x), number(x, "m"), number(x, "g"), number(x, "n_load"), air_state(x)
    )
    forward_warnings(ctx, stall.warnings)
    solution = stall.solution
    return {
        "v_s": solution.v_s,
        "cl_max": solution.cl_max,
        "alpha_s": solution.alpha_s,
        "polar": solution.polar,
    }


def _number(values: Mapping[str, object], name: str) -> float:
    value = values[name]
    if not isinstance(value, float):
        msg = f"parameter {name!r} must be a number, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def _polar(y: Mapping[str, object]) -> Polar | None:
    polar = y["polar"]
    return polar if isinstance(polar, Polar) else None


def _unchecked(what: str) -> CheckResult:
    return CheckResult(state="unchecked", message=f"{what}: the polar is not available")


@postcondition("stall-speed", "cl_max_at_stall_reynolds_number")
def cl_max_at_stall_reynolds_number(
    x: Mapping[str, object], y: Mapping[str, object]
) -> CheckResult:
    """The Probe: C_L,max is the polar's value at ``alpha_S`` and closes the lift balance at ``V_S``.

    The polar is the sweep at ``V_S``, so its sample at ``alpha_S`` is AeroBuildup re-run at
    (``V_S``, ``alpha_S``) in the stall Reynolds number. ``V_S`` must equal
    ``sqrt(2 |n| m g / (rho S_ref |C_L|))`` with that ``C_L`` and the kernel's ``S_ref``.
    """
    polar = _polar(y)
    if polar is None:
        return _unchecked("the Probe needs the sweep at V_S")
    alpha_s, cl_max, v_s = _number(y, "alpha_s"), _number(y, "cl_max"), _number(y, "v_s")
    if alpha_s not in polar.alpha_deg:
        return CheckResult(
            state="violated", message=f"alpha_S = {alpha_s} deg is not a sample of the sweep at V_S"
        )
    cl_sample = polar.cl[polar.alpha_deg.index(alpha_s)]
    if cl_sample != cl_max:
        return CheckResult(
            state="violated",
            message=f"C_L,max = {cl_max} differs from the sweep's C_L = {cl_sample} at alpha_S",
        )
    airplane = x["airplane"]
    if not isinstance(airplane, AirplaneGeometry):
        msg = "parameter 'airplane' must be the geometry"
        raise TypeError(msg)
    area = main_wing_properties(airplane).s_ref
    weight = abs(_number(x, "n_load")) * _number(x, "m") * _number(x, "g")
    probe = math.sqrt(2.0 * weight / (_number(x, "rho") * area * abs(cl_sample)))
    deviation = abs(v_s - probe) / v_s
    if deviation > PROBE_TOLERANCE:
        return CheckResult(
            state="violated",
            message=(
                f"V_S = {v_s:.6g} m/s differs from the closed form {probe:.6g} m/s with the "
                f"C_L = {cl_sample:.6g} of the sweep at alpha_S by {deviation:.2e}"
            ),
        )
    return CheckResult(state="held", message="V_S closes the lift balance at the sweep's C_L")


def _first_extremum_check(y: Mapping[str, object], *, upright: bool) -> CheckResult:
    """The optimum is the first sampled C_L peak (trough) from alpha = 0, within one sweep step."""
    polar = _polar(y)
    what = "peak" if upright else "trough"
    if polar is None:
        return _unchecked(f"the first C_L {what} is read off the sweep")
    index = first_extremum_from_zero(polar.alpha_deg, polar.cl, upright=upright)
    if index is None:
        return CheckResult(
            state="violated", message=f"the sweep at V_S has no C_L {what} inside its range"
        )
    alpha_s, cl_max = _number(y, "alpha_s"), _number(y, "cl_max")
    peak_alpha, peak_cl = polar.alpha_deg[index], polar.cl[index]
    if abs(peak_alpha - alpha_s) > ALPHA_STEP_DEG + 1e-9:
        return CheckResult(
            state="violated",
            message=(
                f"alpha_S = {alpha_s} deg is not at the first C_L {what} of the sweep "
                f"({peak_alpha} deg): the optimum is on another branch"
            ),
        )
    beyond = (peak_cl - cl_max) if upright else (cl_max - peak_cl)
    if beyond > PEAK_TOLERANCE:
        return CheckResult(
            state="violated",
            message=f"C_L = {cl_max} lies {beyond:.2e} short of the first sampled {what} {peak_cl}",
        )
    return CheckResult(state="held", message=f"the optimum is the first C_L {what}")


@postcondition("stall-speed", "optimum_at_first_cl_peak")
def optimum_at_first_cl_peak(x: Mapping[str, object], y: Mapping[str, object]) -> CheckResult:
    """For n > 0: ``alpha_S`` is the first sampled C_L peak of the sweep (K32)."""
    return _first_extremum_check(y, upright=True)


@postcondition("stall-speed", "optimum_at_first_cl_trough")
def optimum_at_first_cl_trough(x: Mapping[str, object], y: Mapping[str, object]) -> CheckResult:
    """For n < 0: ``alpha_S`` is the first sampled C_L trough of the sweep (K32 mirrored)."""
    return _first_extremum_check(y, upright=False)


@postcondition("stall-speed", "alpha_range_past_inverted_stall")
def alpha_range_past_inverted_stall(
    x: Mapping[str, object], y: Mapping[str, object]
) -> CheckResult:
    """The inverted sweep reaches past the trough: the trough lies strictly inside the range.

    A boundary sample is never passed off as C_L,min (ADR 0020).
    """
    polar = _polar(y)
    if polar is None:
        return _unchecked("the sweep range is read off the polar")
    index = first_extremum_from_zero(polar.alpha_deg, polar.cl, upright=False)
    if index is None:
        return CheckResult(
            state="violated",
            message=(
                f"the C_L of the inverted sweep ({polar.alpha_deg[0]} to {polar.alpha_deg[-1]} deg) "
                "has no trough inside its range"
            ),
        )
    return CheckResult(state="held", message="the trough lies inside the sampled range")
