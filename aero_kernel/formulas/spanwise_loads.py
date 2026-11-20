"""Canon formula ``spanwise-loads``: lift, shear force and bending moment of the main wing (ch. 8.12).

One AVL solution at ``L = n m g`` with the controls undeflected and the pitch not trimmed. The strip
normal force of the right half of the main wing is the lift per unit span; AVL integrates it from
the tip to the shear force and the bending moment (``VM``). The adapter returns them per dynamic
pressure ``q = 1/2 rho V^2``; this formula scales them to the operating point of the caller. The root
row is at the centreline: the mesh puts the root of a mirrored wing there, so the moment of the root
row is already the centreline moment.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import airplane_of, forward_warnings, number
from aero_kernel.registry import CheckResult, formula, precondition
from aero_kernel.schema import Curve
from pydantic import JsonValue

__all__ = ["air_density_positive", "flight_speed_positive", "spanwise_loads"]


@precondition("spanwise-loads", "flight_speed_positive")
def flight_speed_positive(x: Inputs) -> CheckResult:
    """The flight speed of the operating point must be positive: the dynamic pressure divides by it."""
    speed = number(x, "v")
    if speed > 0.0:
        return CheckResult(state="held", message=f"the flight speed {speed} m/s is positive")
    return CheckResult(
        state="violated",
        message=f"the flight speed {speed} m/s is not positive; give the speed of the load case in m/s",
    )


@precondition("spanwise-loads", "air_density_positive")
def air_density_positive(x: Inputs) -> CheckResult:
    """The air density of the operating point must be positive: it makes the dynamic pressure."""
    rho = number(x, "rho")
    if rho > 0.0:
        return CheckResult(state="held", message=f"the air density {rho} kg/m^3 is positive")
    return CheckResult(
        state="violated",
        message=f"the air density {rho} kg/m^3 is not positive; check the altitude of the load case",
    )


@formula("spanwise-loads")
async def spanwise_loads(x: Inputs, ctx: Context) -> dict[str, Curve]:
    """The aerodynamic load of the right half of the main wing at the operating point ``(n, V)``.

    The lift coefficient of the AVL run is ``n m g / (q S_ref)`` with ``q = 1/2 rho V^2`` and the
    kernel's ``S_ref``; ``n`` may be negative (a downward load). The result is the aerodynamic load
    only: no inertial relief, pitch untrimmed, main wing only (declared as ``spanwise_loads_scope``).

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, ``n_load``
            the load factor (1), ``rho`` the air density in kg/m^3 and ``v`` the flight speed in m/s.
        ctx: The formula context; ``ctx.solvers.avl`` solves the loads.

    Returns:
        ``l_y`` in N/m over the strip positions, ``v_y`` in N and ``m_y`` in N m over the root, the
        strips and the tip, all against ``y`` in m from the centreline, positive outward.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged. A speed or density that is not positive is
            refused before this runs, by the canon preconditions of the entry.
    """
    airplane = airplane_of(x)
    speed, rho = number(x, "v"), number(x, "rho")
    q = 0.5 * rho * speed**2
    reference = await ctx.solvers.geometry.main_wing_reference(airplane)
    cl = number(x, "n_load") * number(x, "m") * number(x, "g") / (q * reference.s_ref)
    found = await ctx.solvers.avl.spanwise_loads(airplane, cl)
    forward_warnings(ctx, found.warnings)
    detail: dict[str, JsonValue] = {"cl": cl, "q_pa": q}
    load = number(x, "n_load") * number(x, "m") * number(x, "g")
    share = ""
    if abs(load) > 0.0:
        wing_share = 2.0 * q * found.shear[0] / load  # both halves' normal force over n m g
        detail["wing_share"] = wing_share
        share = f" The main wing carries {wing_share:.3f} of n m g in this solution."
    ctx.warn(
        "spanwise_loads_scope",
        "The loads are those of the right half of the main wing from one vortex lattice solution at "
        "L = n m g with the controls undeflected: aerodynamic load only (no inertial relief, "
        "which is conservative for upward load and not for downward load or heavy masses near the "
        "tip), normal force only, attached flow. The pitch is not trimmed, so the share of the "
        "load the wing carries depends on the lift coefficient: the tail load is roughly constant, "
        "so at a low lift coefficient the wing carries more than half of n m g per half wing "
        "(a download on the tail) and at a high one slightly less." + share + " The lift curve "
        "starts at the centre of the first strip; the shear and the moment start at y = 0, and a "
        "wing stored off the centreline is carried to y = 0 by the mesh, so the first strip stands "
        "for the load from y = 0 to its outer edge.",
        detail,
    )
    return {
        "l_y": Curve(x=found.y_strip, y=tuple(q * value for value in found.c_cl)),
        "v_y": Curve(x=found.y_station, y=tuple(q * value for value in found.shear)),
        "m_y": Curve(x=found.y_station, y=tuple(q * value for value in found.moment)),
    }
