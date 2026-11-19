"""Canon formula ``cruise-target-performance``: flight time and range at the mission's cruise speed.

``t_cruise = 3600 E_bat / P_bat`` and ``R_cruise = V_cruise,target t_cruise``, the battery power
``P_bat`` of level flight at the target speed from the embedded ``motor-propeller-part-load`` relation
(ADR 0022; no assumed drive-train efficiency, maintainer 2026-10-25, #1235). Rated pack energy, no
usable fraction, no sag, no reserve (declared by the canon entry). Applied only where the target is
given (``given: [cruise-speed-target]``).
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.motor_propeller_part_load import (
    energy_over_power,
    forward_part_load_caveats,
    part_load_at,
)
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["cruise_target_performance"]


@formula("cruise-target-performance")
async def cruise_target_performance(x: Inputs, ctx: Context) -> dict[str, float]:
    """Flight time and range at the cruise-speed target on the rated battery energy.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``e_bat`` in Wh, ``v_cruise_target`` in m/s, ``components``, ``k_v`` in rpm/V,
            ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and
            ``eta_mot`` are bound for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup and hands out the embedded relations.

    Returns:
        ``t_cruise`` in s and ``r_cruise`` in m.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; ``not_converged``,
            ``outside_propeller_table``, ``no_thrust_at_full_throttle`` of the part-load chain;
            ``non_positive_battery_power``.
    """
    v = number(x, "v_cruise_target")
    at_target = await part_load_at(x, ctx, v)
    t_cruise = energy_over_power(number(x, "e_bat"), at_target.point.p_bat, v)
    forward_part_load_caveats(ctx, [at_target])
    return {"t_cruise": t_cruise, "r_cruise": v * t_cruise}
