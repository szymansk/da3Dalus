"""Canon formula ``control-surface-hinge-moments``: the hinge moment of every control surface of a role.

One AVL solution per application (ARCHITECTURE ch. 8.5, 8.8): the lift coefficient of the operating
point ``n m g / (q S_ref)`` fixes the angle of attack, only the surfaces acting in the role are
deflected, by the role's deflection, and AVL's ``Chinge`` of each surface is turned into a moment
``q S_ref c_ref Chinge`` (AVL refers it to the aircraft's reference area and chord). The pitching
moment is not trimmed. The result is a per-surface value: the keys are surface keys
``<wing>.<device>[_left|_right]``; the engine combines the applications' entries into one quantity.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula
from aero_kernel.solvers.avl_hinge import ROLE_CODES

__all__ = ["control_surface_hinge_moments"]


def role_of(x: Inputs) -> str:
    """The role the application evaluates, from its constant ``role`` (1 aileron ... 4 flap).

    Raises:
        TypeError: If the constant is not a number.
        KeyError: If it is not one of the role codes (a defect of the canon).
    """
    return ROLE_CODES[round(number(x, "role"))]


@formula("control-surface-hinge-moments")
async def control_surface_hinge_moments(x: Inputs, ctx: Context) -> dict[str, dict[str, float]]:
    """The hinge moment in N*m of every control surface acting in the role, at the role's deflection.

    Args:
        x: ``airplane`` the geometry (devices at rest), ``m`` the mass in kg, ``g`` the gravity in
            m/s^2, ``n_load`` the load factor, ``rho`` the air density in kg/m^3, ``mu`` the dynamic
            viscosity in Pa s, ``a`` the speed of sound in m/s, ``v`` the flight speed in m/s,
            ``delta`` the role's deflection in degrees and ``role`` the role code.
        ctx: The formula context; ``ctx.solvers.avl`` is the AVL adapter.

    Returns:
        ``h`` per surface key, positive in the sense of a positive deflection of that surface.

    Raises:
        TypeError: If a number is not a number.
        FormulaError: From the adapter, unchanged.
    """
    airplane = airplane_of(x)
    speed = number(x, "v")
    dynamic_pressure = 0.5 * number(x, "rho") * speed**2
    reference = await ctx.solvers.geometry.main_wing_reference(airplane)
    cl = (
        number(x, "n_load") * number(x, "m") * number(x, "g") / (dynamic_pressure * reference.s_ref)
    )
    found = await ctx.solvers.avl.hinge_moments(
        airplane,
        cl=cl,
        role=role_of(x),
        delta_deg=number(x, "delta"),
        speed_ms=speed,
        air=air_state(x),
    )
    forward_warnings(ctx, found.warnings)
    ctx.warn(
        "hinge_moment_inviscid_estimate",
        "The hinge moment is AVL's: inviscid, steady, attached flow and linear in the deflection. "
        "In attached flow it is typically an over-estimate; with flow separation behind the hinge or "
        "the trailing edge, at large deflection, or at a chord Reynolds number below 7e4 it is "
        "unbounded (the Reynolds warnings of the surfaces say where). It is not a servo torque: "
        "friction, linkage and margins are not in it.",
    )
    ctx.warn(
        "hinge_moment_pitch_untrimmed",
        "The angle of attack follows from the lift L = n m g alone; no other control trims the "
        "pitching moment. The hinge moment is that of the deflected surface at this angle of "
        "attack, not of a trimmed flight state.",
    )
    return {"h": found.moments}
