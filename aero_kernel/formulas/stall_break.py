"""Canon formula ``stall-break``: where the lift curve breaks past the stall (ch. 8.5, 8.12).

``alpha_break`` is the angle past ``alpha_S`` at which the lift coefficient of the computed polar has
fallen to ``(1 - f) C_L,max``, linearly interpolated between the two bracketing samples of the
published sweep; ``width`` is its distance from ``alpha_S``. The event is not bracketed if the polar
never falls that far: then there is no value (ADR 0020), never the last or the peak sample.

**Resolution check** (maintainer, 2026-10-24: raise the resolution, never loosen a threshold). The
published sweep has a step of 0.25 deg. The break is computed a second time from a sweep at half that
step, from ``alpha_S`` to the end of the range, at the same airplane, speed and air state. The two
angles are compared against :data:`RESOLUTION_TOLERANCE_DEG`.

**Tolerance, fixed before it was measured.** One step of the published sweep, 0.25 deg. Basis: linear
interpolation between samples cannot be trusted below the sample spacing, so a finer sweep that moves
the break by more than one published step shows the published value is resolved by the grid and not by
the polar. The number is not taken from a source (none exists for a computed polar); it is derived from
the sweep's own step, and the half-step sweep is the finer reference. A difference above it is the
declared defect warning ``stall_break_resolution`` with both values; the value of the published sweep
stands, because it is the polar the other quantities (``polar-stall``) are published from.
"""

import math
from collections.abc import Mapping

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of, number
from aero_kernel.registry import formula
from aero_kernel.schema import Polar
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import ALPHA_MAX_DEG, ALPHA_MIN_DEG, ALPHA_STEP_DEG
from aero_kernel.solvers.stall_math import first_crossing_below

__all__ = ["RESOLUTION_TOLERANCE_DEG", "stall_break"]

# The resolution check's tolerance: one step of the published sweep (see the module docstring).
RESOLUTION_TOLERANCE_DEG = ALPHA_STEP_DEG
# The check's sweep runs at half the published step.
HALF_STEP_DEG = ALPHA_STEP_DEG / 2.0


def _polar(x: Mapping[str, object]) -> Polar:
    value = x["polar_s"]
    if not isinstance(value, Polar):
        msg = f"parameter 'polar_s' must be a polar, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def _invalid(parameter: str, message: str, hint: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.INVALID_INPUT, "invalid_input", message, hint, parameter=parameter
    )


def _half_step_grid(alpha_s: float) -> list[float]:
    """The angles of the check's sweep: ``alpha_S`` and the half-step lattice up to the range end.

    The lattice is the one of the published sweep refined by two, so every published sample past the
    stall angle is among the check's samples.
    """
    count = round((ALPHA_MAX_DEG - ALPHA_MIN_DEG) / HALF_STEP_DEG)
    lattice = (ALPHA_MIN_DEG + k * HALF_STEP_DEG for k in range(count + 1))
    return [alpha_s, *(a for a in lattice if a > alpha_s + config().opt_alpha_margin_deg.value)]


@formula("stall-break")
async def stall_break(x: Inputs, ctx: Context) -> dict[str, float]:
    """The angle where the lift has fallen by the fraction ``f`` past the stall, and its distance.

    Args:
        x: ``polar_s`` the sweep at ``V_S`` with ``alpha_s`` among its samples, ``alpha_s`` in
            degrees, ``cl_max`` the lift coefficient there, ``f`` the break fraction (0 < f < 1),
            ``airplane`` (the sweep of the resolution check is re-run at the same airplane and at the
            flow conditions the polar carries: speed and air state).
        ctx: The formula context; ``ctx.solvers.opti`` runs the finer sweep.

    Returns:
        ``alpha_break`` in degrees and ``width`` = ``alpha_break`` - ``alpha_s`` in degrees, both
        from the published sweep.

    Raises:
        TypeError: If ``polar_s`` is not a polar, ``airplane`` is not the geometry or a number is
            not a number.
        FormulaError: ``invalid_input`` for ``f`` outside (0, 1), a non-positive ``cl_max`` or an
            ``alpha_s`` that is no sample of the polar or a polar without flow conditions;
            ``not_converged`` if the polar never falls
            to the level (or the finer sweep does not) and from the adapter, unchanged.
    """
    polar = _polar(x)
    alpha_s, cl_max, fraction = number(x, "alpha_s"), number(x, "cl_max"), number(x, "f")
    if not 0.0 < fraction < 1.0:
        raise _invalid("f", f"the break fraction f = {fraction} is not in (0, 1)", "give 0 < f < 1")
    if not (math.isfinite(cl_max) and cl_max > 0.0):
        raise _invalid("cl_max", f"C_L,max = {cl_max} is not positive", "give C_L,max > 0")
    if alpha_s not in polar.alpha_deg:
        raise _invalid(
            "alpha_s",
            f"alpha_S = {alpha_s} deg is not a sample of the polar",
            "give the polar published with alpha_S",
        )
    flow = polar.conditions
    if flow is None:
        raise _invalid(
            "polar_s",
            "the polar does not say which flow it was computed at",
            "give the polar published by stall-speed",
        )
    level = (1.0 - fraction) * cl_max
    published = first_crossing_below(polar.alpha_deg, polar.cl, alpha_s, level)
    if published is None:
        raise FormulaError(
            ErrorCategory.NOT_CONVERGED,
            "not_converged",
            f"the lift coefficient does not fall to {level:.4g} past alpha_S = {alpha_s} deg "
            f"inside the sweep (to {polar.alpha_deg[-1]} deg)",
            "the stall break is not bracketed by the sampled angles of attack",
            detail={"alpha_s": alpha_s, "level": level, "alpha_max_deg": polar.alpha_deg[-1]},
        )
    air = AirState(
        density=flow.density,
        dynamic_viscosity=flow.dynamic_viscosity,
        speed_of_sound=flow.speed_of_sound,
    )
    finer = await ctx.solvers.opti.sweep(airplane_of(x), air, flow.v_ms, _half_step_grid(alpha_s))
    refined = first_crossing_below(finer.alpha_deg, finer.cl, alpha_s, level)
    if refined is None:
        raise FormulaError(
            ErrorCategory.NOT_CONVERGED,
            "not_converged",
            f"the sweep at half the step does not bracket the stall break found at {published} deg",
            "the published break is not reproduced by the finer sweep",
            detail={"alpha_break_published_deg": published, "alpha_s": alpha_s},
        )
    if abs(refined - published) > RESOLUTION_TOLERANCE_DEG:
        ctx.warn(
            "stall_break_resolution",
            f"the stall break moves from {published:.4f} to {refined:.4f} deg when the sweep step "
            f"is halved: more than one published step, so the grid resolves it, not the polar",
            {
                "alpha_break_published_deg": published,
                "alpha_break_half_step_deg": refined,
                "step_deg": ALPHA_STEP_DEG,
                "half_step_deg": HALF_STEP_DEG,
                "tolerance_deg": RESOLUTION_TOLERANCE_DEG,
            },
        )
    return {"alpha_break": published, "width": published - alpha_s}
