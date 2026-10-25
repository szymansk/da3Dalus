"""Canon formula ``roll-rate``: the steady roll at a given aileron deflection (ARCHITECTURE ch. 8.5, 8.8).

One coroutine over two method worlds (A11): ``aerobuildup`` solves the steady roll with IPOPT over
AeroBuildup, ``avl`` with the ailerons driven directly in AVL. Both solve the same roll: rotation
about the stability x axis through the airplane's reference point, the stability-axis rolling moment
zero, positive for a roll to the right. The speed is the approach speed; a deflection beyond the
reference angle is computed and declared, never clipped.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["roll_rate"]

# Sadraey, Aircraft Design (2013) §12.4.3: beyond about 20-25 deg of aileron deflection the flow
# separates over the aileron and its effectiveness drops; recommendation |delta_A,max| <= 25 deg.
# Transport and general-aviation material, not checked at model Reynolds number (ADR 0028); the
# canon sets no limit, the reference only labels the angle.
DEFLECTION_REFERENCE_DEG = 25.0


def warn_deflection_beyond_reference(ctx: Context, delta_deg: float) -> None:
    """Declare an aileron deflection beyond the reference angle (a ``practice`` warning).

    Args:
        ctx: The formula context.
        delta_deg: The aileron deflection in degrees (either sign).
    """
    if abs(delta_deg) > DEFLECTION_REFERENCE_DEG:
        ctx.warn(
            "aileron_deflection_beyond_reference",
            f"The aileron deflection of {delta_deg:g} deg is beyond {DEFLECTION_REFERENCE_DEG:g} "
            "deg, where flow separation over the aileron lowers its effectiveness (Sadraey, "
            "Aircraft Design, 12.4.3; transport and general-aviation material, not checked at "
            "model Reynolds numbers). The value is computed at the given angle.",
            {"deflection_deg": delta_deg, "reference_deg": DEFLECTION_REFERENCE_DEG},
        )


@formula("roll-rate")
async def roll_rate(x: Inputs, ctx: Context) -> dict[str, float]:
    """The roll rate of the airplane at the aileron deflection ``delta_a``, in the world of ``ctx.world``.

    - ``aerobuildup``: IPOPT over AeroBuildup for the angle of attack and the roll rate at
      ``L = m g`` and zero stability-axis rolling moment.
    - ``avl``: the vortex lattice at the lift coefficient ``m g / (1/2 rho V_app^2 S_ref)`` with the
      kernel's ``S_ref``, ``r rm 0`` and the ailerons driven at ``delta_a``.

    The nondimensional rate is ``p b / 2V`` with the bound ``b_ref`` and ``V_app`` in both worlds.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, the ISA air
            state ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in m/s, ``v_app`` the approach speed in
            m/s, ``b_ref`` the span in m and ``delta_a`` the aileron deflection in degrees
            (positive = roll to the right).
        ctx: The formula context; ``ctx.world`` is the world, ``ctx.solvers`` the adapters.

    Returns:
        ``p`` in deg/s and ``p_hat`` (1), positive for a roll to the right.

    Raises:
        TypeError: If a number is not a number or ``ctx.world`` is not a world of this formula.
        FormulaError: From the adapter, unchanged.
    """
    airplane = airplane_of(x)
    delta, speed, span = number(x, "delta_a"), number(x, "v_app"), number(x, "b_ref")
    warn_deflection_beyond_reference(ctx, delta)
    world = ctx.world
    if world == "aerobuildup":
        steady = await ctx.solvers.opti.steady_roll(
            airplane, number(x, "m"), number(x, "g"), air_state(x), speed, delta
        )
        forward_warnings(ctx, steady.warnings)
        rate = steady.p_rad_s
    elif world == "avl":
        dynamic_pressure = 0.5 * number(x, "rho") * speed**2
        reference = await ctx.solvers.geometry.main_wing_reference(airplane)
        cl = number(x, "m") * number(x, "g") / (dynamic_pressure * reference.s_ref)
        found = await ctx.solvers.avl.steady_roll(airplane, cl, delta)
        forward_warnings(ctx, found.warnings)
        rate = found.p_hat * 2.0 * speed / span
    else:
        msg = f"roll-rate has no world {world!r}"
        raise TypeError(msg)
    return {"p": math.degrees(rate), "p_hat": rate * span / (2.0 * speed)}
