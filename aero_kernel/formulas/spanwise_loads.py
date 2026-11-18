"""Canon formula ``spanwise-loads``: lift, shear force and bending moment of the main wing (ch. 8.12).

One AVL solution at ``L = n m g`` with the controls undeflected and the pitch not trimmed. The strip
normal force of the right half of the main wing is the lift per unit span; AVL integrates it from
the tip to the shear force and the bending moment (``VM``). The adapter returns them per dynamic
pressure ``q = 1/2 rho V^2``; this formula scales them to the operating point of the caller. The root
row is at the centreline: the mesh puts the root of a mirrored wing there, so the moment of the root
row is already the centreline moment.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of, forward_warnings, number
from aero_kernel.registry import formula
from aero_kernel.schema import Curve

__all__ = ["spanwise_loads"]


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
        FormulaError: ``invalid_input`` for a speed or density that is not positive; from the
            adapter, unchanged.
    """
    airplane = airplane_of(x)
    speed, rho = number(x, "v"), number(x, "rho")
    for name, value in (("v", speed), ("rho", rho)):
        if value <= 0.0:
            raise FormulaError(
                ErrorCategory.INVALID_INPUT,
                "invalid_input",
                f"{name} = {value} is not admissible for a load at an operating point",
                "give a positive value",
                parameter=name,
            )
    q = 0.5 * rho * speed**2
    reference = await ctx.solvers.geometry.main_wing_reference(airplane)
    cl = number(x, "n_load") * number(x, "m") * number(x, "g") / (q * reference.s_ref)
    found = await ctx.solvers.avl.spanwise_loads(airplane, cl)
    forward_warnings(ctx, found.warnings)
    ctx.warn(
        "spanwise_loads_scope",
        "The loads are those of the right half of the main wing from one vortex lattice solution at "
        "L = n m g with the controls undeflected: aerodynamic load only (no inertial relief, "
        "which is conservative for upward load and not for downward load or heavy masses near the "
        "tip), the pitch not trimmed, normal force only, attached flow.",
        {"cl": cl, "q_pa": q},
    )
    return {
        "l_y": Curve(x=found.y_strip, y=tuple(q * value for value in found.c_cl)),
        "v_y": Curve(x=found.y_station, y=tuple(q * value for value in found.shear)),
        "m_y": Curve(x=found.y_station, y=tuple(q * value for value in found.moment)),
    }
