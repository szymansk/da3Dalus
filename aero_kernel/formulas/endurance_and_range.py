"""Canon formula ``endurance-and-range``: flight time and range at the airplane's own two speeds.

``t_est = 3600 E_bat / P_bat(V_mp)`` and ``R_est = 3600 E_bat V_md / P_bat(V_md)``, with the battery
power ``P_bat(V)`` of level flight from the embedded ``motor-propeller-part-load`` relation (the
canon's ``embeds``; no second implementation of the balance, ADR 0022, and no assumed drive-train
efficiency, maintainer 2026-10-25, #1235). The energy is the rated pack energy ``E_bat``, as the
canon declares: no usable fraction, no voltage sag, no reserve.

Only the answer's caveats are forwarded: those of the two level-flight solves, the route and, for a
speed the drive train cannot hold (``r_T > 1``), the part-load postcondition.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.motor_propeller_part_load import (
    energy_over_power,
    forward_part_load_caveats,
    part_load_at,
)
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["endurance_and_range"]


@formula("endurance-and-range")
async def endurance_and_range(x: Inputs, ctx: Context) -> dict[str, float]:
    """Flight time at ``V_mp`` and range at ``V_md`` on the rated battery energy.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``e_bat`` in Wh, ``v_mp`` and ``v_md`` in m/s, ``components``, ``k_v`` in rpm/V,
            ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and
            ``eta_mot`` are bound for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup and hands out the embedded relations.

    Returns:
        ``t_est`` in s and ``r_est`` in m.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; ``not_converged``,
            ``outside_propeller_table``, ``no_thrust_at_full_throttle`` of the part-load chain;
            ``non_positive_battery_power``.
    """
    v_mp, v_md, e_bat = number(x, "v_mp"), number(x, "v_md"), number(x, "e_bat")
    at_mp = await part_load_at(x, ctx, v_mp)
    at_md = await part_load_at(x, ctx, v_md)
    t_est = energy_over_power(e_bat, at_mp.point.p_bat, v_mp)
    r_est = v_md * energy_over_power(e_bat, at_md.point.p_bat, v_md)
    forward_part_load_caveats(ctx, [at_mp, at_md], e_bat)
    return {"t_est": t_est, "r_est": r_est}
