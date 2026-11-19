"""Canon formula ``aileron-deflection-required``: the aileron angle a roll-rate target needs (ch. 8.5, 8.8).

The inverse of ``roll-rate``: the same steady roll (:func:`steady_roll_rate`, one roll model for
the kernel), solved for the aileron command that gives the target roll rate at the speed ``v``.

- ``aerobuildup``: the command is searched upward from 0 in steps until the roll rate reaches the
  target (then the root is refined, Illinois regula falsi) or stops increasing (the method's own
  maximum: ``target_above_method_maximum``, never a clipped angle).
- ``avl``: AVL is linear in the deflection, so one run at a reference command gives the answer
  directly. Beyond ``|p b / 2V| <= 0.10`` of the target the world declares itself outside its
  validity and leaves the interval (maintainer decision on #1243, 2026-10-25).

A negative target is solved as its mirror: the roll is antisymmetric in the command (tested for
``roll-rate``), so the deflection is negative.
"""

import math
from dataclasses import dataclass

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.roll_rate import steady_roll_rate, warn_deflection_beyond_reference
from aero_kernel.formulas.values import forward_warnings, number
from aero_kernel.registry import formula
from aero_kernel.schema import KernelWarning

__all__ = ["aileron_deflection_required"]

# Warnings of a trial evaluation that describe the trial, not the answer: the answer's own are
# issued once, for the returned deflection. ``avl_roll_rate_beyond_range`` is the adapter's
# statement about the AVL reference run (a small command), not about the target's roll rate; the
# target's own range is declared as ``world_outside_validity``.
_TRIAL_ONLY = frozenset(
    {
        "world_outside_validity",
        "aileron_deflection_beyond_reference",
        "avl_roll_rate_beyond_range",
    }
)


@dataclass(frozen=True)
class _Point:
    """One evaluation of the steady roll: the command, the roll rate (rad/s) and its caveats."""

    delta: float
    rate: float
    warnings: tuple[KernelWarning, ...]


async def _evaluate(x: Inputs, ctx: Context, speed: float, delta: float) -> _Point:
    """The steady roll at the command ``delta`` (deg), its warnings kept apart from the context's."""
    scratch = Context(origin="aileron-deflection-required", solvers=ctx.solvers, world=ctx.world)
    rate = await steady_roll_rate({**x, "delta_a": delta}, scratch, speed)
    return _Point(delta, rate, scratch.warnings)


def _forward(ctx: Context, point: _Point) -> None:
    """Report the caveats of the answer's evaluation as the formula's own."""
    forward_warnings(ctx, tuple(w for w in point.warnings if w.code not in _TRIAL_ONLY))


def _above_grid_maximum(best: _Point, target_rad_s: float, step_deg: float) -> FormulaError:
    """The error of a target above the roll rate the search found (AeroBuildup world).

    The search marches the command in steps of ``step_deg`` and stops where the roll rate no longer
    rises, so ``best`` is the highest value on that grid, not a refined maximum.
    """
    maximum = math.degrees(best.rate)
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "target_above_method_maximum",
        f"The roll-rate target of {math.degrees(target_rad_s):g} deg/s lies above the highest roll "
        f"rate found on the {step_deg:g} deg search grid of the aileron command, {maximum:g} deg/s "
        f"at {best.delta:g} deg (the roll rate does not rise beyond it); there is no solution in "
        "this world.",
        "lower the roll-rate target, or give a device with more roll authority",
        {
            "target_deg_s": math.degrees(target_rad_s),
            "max_roll_rate_deg_s": maximum,
            "delta_a_deg": best.delta,
            "search_step_deg": step_deg,
        },
    )


def _no_avl_roll(point: _Point, p_hat: float, floor: float, target_rad_s: float) -> FormulaError:
    """The error of an AVL reference run that shows no roll to scale (the same case as above)."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "target_above_method_maximum",
        f"The roll-rate target of {math.degrees(target_rad_s):g} deg/s cannot be reached: at the "
        f"reference command of {point.delta:g} deg AVL gives p b / 2V = {p_hat:g}, not above the "
        f"print resolution of {floor:g}, so the roll is not scaled to a command.",
        "lower the roll-rate target, or give a device with more roll authority",
        {
            "target_deg_s": math.degrees(target_rad_s),
            "max_roll_rate_deg_s": math.degrees(point.rate),
            "delta_a_deg": point.delta,
            "p_hat_reference": p_hat,
            "print_floor": floor,
        },
    )


def _reached(rate: float, target: float, tolerance: float) -> bool:
    return abs(rate - target) <= tolerance * target


async def _refine(
    x: Inputs, ctx: Context, speed: float, target: float, bracket: tuple[_Point, _Point]
) -> _Point:
    """Illinois regula falsi on ``p(delta) - target`` inside a bracket (below, above)."""
    settings = config()
    tolerance = settings.opt_roll_target_tolerance.value
    refinements = int(settings.opt_roll_max_refinements.value)
    low, high = bracket
    f_low, f_high = low.rate - target, high.rate - target
    side = 0
    for _ in range(refinements):
        delta = (low.delta * f_high - high.delta * f_low) / (f_high - f_low)
        point = await _evaluate(x, ctx, speed, delta)
        f_new = point.rate - target
        if _reached(point.rate, target, tolerance):
            return point
        if f_new > 0.0:
            high, f_high = point, f_new
            f_low = f_low / 2.0 if side == 1 else f_low
            side = 1
        else:
            low, f_low = point, f_new
            f_high = f_high / 2.0 if side == -1 else f_high
            side = -1
    msg = "the search for the aileron command did not reach the roll-rate target"
    raise FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"{msg} within {refinements} refinements.",
        "report the case; the roll rate is not smooth in the command",
        {"target_deg_s": math.degrees(target), "delta_a_deg": low.delta},
    )


async def _search_aerobuildup(x: Inputs, ctx: Context, speed: float, target: float) -> _Point:
    """March the command upward from 0; refine once the target is bracketed (``target`` > 0)."""
    settings = config()
    step, limit = settings.opt_roll_search_step.value, settings.opt_roll_search_limit.value
    # p(0) = 0 is assumed, not evaluated: the airplane is symmetric and undeflected at command 0
    # (a flaperon's bias is symmetric), so the steady roll does not turn.
    previous = _Point(0.0, 0.0, ())
    k = 1
    while k * step <= limit:
        point = await _evaluate(x, ctx, speed, k * step)
        if _reached(point.rate, target, settings.opt_roll_target_tolerance.value):
            return point
        if point.rate > target:
            return await _refine(x, ctx, speed, target, (previous, point))
        if point.rate <= previous.rate:
            raise _above_grid_maximum(previous, target, step)
        previous, k = point, k + 1
    raise FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"The roll rate still rises at the search limit of {limit:g} deg and has not reached "
        f"the target of {math.degrees(target):g} deg/s.",
        "report the case; no maximum of the roll rate was found",
        {"target_deg_s": math.degrees(target), "delta_a_deg": limit},
    )


async def _solve_aerobuildup(x: Inputs, ctx: Context, speed: float, target: float) -> float:
    """The command of the AeroBuildup world for a signed target (rad/s)."""
    if not target:  # an exact zero given by the caller: no roll wanted, no deflection, no solve
        return 0.0
    point = await _search_aerobuildup(x, ctx, speed, abs(target))
    _forward(ctx, point)
    return math.copysign(point.delta, target)


async def _solve_avl(x: Inputs, ctx: Context, speed: float, target: float) -> float:
    """The command of the AVL world: linear in the command, from one run at the reference command."""
    if not target:  # an exact zero given by the caller: no roll wanted, no deflection, no solve
        return 0.0
    settings = config()
    reference = settings.avl_roll_reference_deflection.value
    point = await _evaluate(x, ctx, speed, reference)
    span = number(x, "b_ref")
    p_hat_reference = point.rate * span / (2.0 * speed)
    floor = settings.avl_roll_print_floor.value
    if p_hat_reference <= floor:  # quantisation noise, none, or a reversed device
        raise _no_avl_roll(point, p_hat_reference, floor, target)
    p_hat_target = target * span / (2.0 * speed)
    delta = reference * p_hat_target / p_hat_reference
    _forward(ctx, point)
    limit = ctx.solvers.rules.value("avl-roll-rate-validity", "max_roll_rate_coefficient")
    if abs(p_hat_target) > limit:
        ctx.warn(
            "world_outside_validity",
            f"The AVL world needs p b / 2V = {p_hat_target:g} for the target, outside AVL's "
            f"stated range of |p b / 2V| <= {limit:g} (AVL is linear in the deflection). Its "
            f"deflection of {delta:g} deg is not used: the interval is the AeroBuildup world alone.",
            {
                "p_hat": p_hat_target,
                "p_deg_s": math.degrees(target),
                "limit": limit,
                "delta_a_deg": delta,
            },
        )
    return delta


@formula("aileron-deflection-required")
async def aileron_deflection_required(x: Inputs, ctx: Context) -> dict[str, float]:
    """The aileron deflection that gives the roll-rate target ``p_target`` at the speed ``v``.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, the ISA air
            state ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in m/s, ``b_ref`` the span in m, ``v``
            the flight speed in m/s and ``p_target`` the roll-rate target in deg/s (positive = roll
            to the right).
        ctx: The formula context; ``ctx.world`` is the world, ``ctx.solvers`` the adapters.

    Returns:
        ``delta_a_req`` in degrees, signed like the target.

    Raises:
        TypeError: If a number is not a number or ``ctx.world`` is not a world of this formula.
        FormulaError: ``target_above_method_maximum`` (the target exceeds what the world reaches),
            ``not_converged`` (the search ended without a root), or the adapter's error unchanged.
    """
    speed = number(x, "v")
    target = math.radians(number(x, "p_target"))
    if ctx.world == "aerobuildup":
        delta = await _solve_aerobuildup(x, ctx, speed, target)
    elif ctx.world == "avl":
        delta = await _solve_avl(x, ctx, speed, target)
    else:
        msg = f"the required aileron deflection has no world {ctx.world!r}"
        raise TypeError(msg)
    warn_deflection_beyond_reference(ctx, delta)
    return {"delta_a_req": delta}
