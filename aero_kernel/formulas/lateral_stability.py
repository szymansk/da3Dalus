"""The lateral static stability at one speed, shared by the three ``lateral-static-stability-*`` entries.

The three canon entries are one procedure at three operating points (``V_md``, ``V_app``, ``V_mp``);
each binds its own speed and produces its own outputs, so the work is written once here and the three
modules are bindings (ARCHITECTURE ch. 8.5).
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of, forward_warnings, number

__all__ = ["lateral_stability"]


def _no_finite_time(reason: str, detail: dict[str, float]) -> FormulaError:
    """The error of a spiral that has no finite doubling or halving time."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        f"the spiral root has no finite time constant: {reason}",
        "the spiral is neutral at this operating point, or the roll-yaw coupling vanishes",
        detail=dict(detail),
    )


def _spiral_time(
    gravity: float,
    speed: float,
    e_spiral: float,
    c_l_beta: float,
    c_n_beta: float,
    c_l_p: float,
    c_n_p: float,
) -> tuple[float, float]:
    """The spiral root ``lambda_s = -(g/V) E / (C_l,beta C_n,p - C_n,beta C_l,p)`` and its time.

    The approximation without inertias (Etkin and Reid): the root of the quasi-static spiral mode.
    The time is ``ln 2 / lambda_s`` for a root above zero (the bank doubles) and
    ``-ln 2 / |lambda_s|`` for one below it (the bank halves), the sign marking which.

    Returns:
        ``(lambda_s, time)`` in 1/s and s.

    Raises:
        FormulaError: ``unsupported_configuration`` if the denominator or the root is zero.
    """
    denominator = c_l_beta * c_n_p - c_n_beta * c_l_p
    try:
        root = -(gravity / speed) * e_spiral / denominator
    except ZeroDivisionError as error:
        raise _no_finite_time(
            "C_l,beta C_n,p - C_n,beta C_l,p is zero", {"denominator": denominator}
        ) from error
    try:
        return root, math.copysign(math.log(2.0) / abs(root), root)
    except ZeroDivisionError as error:
        raise _no_finite_time("the spiral criterion is zero", {"e_spiral": e_spiral}) from error


async def lateral_stability(
    x: Inputs, ctx: Context, *, roll_due_to_yaw_rate: bool = False
) -> dict[str, float]:
    """``C_l,beta``, ``C_n,beta``, the spiral criterion and its time from one AVL solution.

    AVL runs at ``C_L = m g / (1/2 rho V^2 S_ref)`` with the kernel's ``S_ref`` and the fuselages as
    bodies, the moment reference at the design CG. ``E = C_l,beta C_n,r - C_n,beta C_l,r`` is
    positive for a stable spiral; the time is the doubling time of an unstable spiral and, for a
    stable one, the time to halve with a negative sign (declared). Numbers, no verdicts (A10).

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``x_cg`` the design CG in m
            and ``v`` the speed in m/s.
        ctx: The formula context; ``ctx.solvers.avl`` and ``ctx.solvers.geometry`` are the adapters.
        roll_due_to_yaw_rate: Whether the entry also outputs ``C_l,r`` (``lateral-static-stability-mp``
            does, maintainer decision 2026-10-27, #1275): the engine rejects an output the entry does
            not declare.

    Returns:
        ``c_l_beta`` and ``c_n_beta`` in 1/rad, with ``c_l_r`` (per ``r'b/2V``) if asked, ``e_spiral`` as AVL's derivatives give it (``C_l,beta`` per
        rad times ``C_n,r`` per ``r'b/2V``) and ``t2_spiral`` in s.

    Raises:
        FormulaError: ``invalid_input`` for a lift coefficient that is not positive;
            ``unsupported_configuration`` for a spiral without a finite time constant; from the
            adapters, unchanged.
    """
    airplane = airplane_of(x)
    speed, gravity = number(x, "v"), number(x, "g")
    reference = await ctx.solvers.geometry.main_wing_reference(airplane)
    cl = number(x, "m") * gravity / (0.5 * number(x, "rho") * speed**2 * reference.s_ref)
    if math.isnan(cl) or cl <= 0.0:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "invalid_input",
            f"the lift coefficient {cl} of the lift balance is not positive",
            "give a positive mass, gravity, density, speed and reference area",
            parameter="m",
        )
    found = await ctx.solvers.avl.lateral_derivatives(airplane, cl, number(x, "x_cg"))
    forward_warnings(ctx, found.warnings)
    e_spiral = found.c_l_beta * found.c_n_r - found.c_n_beta * found.c_l_r
    root, time = _spiral_time(
        gravity, speed, e_spiral, found.c_l_beta, found.c_n_beta, found.c_l_p, found.c_n_p
    )
    if root < 0.0:
        ctx.warn(
            "spiral_halving_time_reported",
            "The spiral is stable: a bank halves and never doubles. The reported time is the time "
            "to halve, ln 2 / |lambda_s|, with a negative sign.",
            {"lambda_s": root, "halving_time_s": -time},
        )
    outputs = {
        "c_l_beta": found.c_l_beta,
        "c_n_beta": found.c_n_beta,
        "e_spiral": e_spiral,
        "t2_spiral": time,
    }
    if roll_due_to_yaw_rate:
        outputs["c_l_r"] = found.c_l_r
    return outputs
