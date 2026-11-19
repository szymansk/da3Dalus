"""Canon formula ``best-angle-of-climb``: the speed and angle of the steepest steady climb at full throttle.

The entry maximises ``gamma`` subject to the exact force balances of a steady climb,
``L = m g cos(gamma)`` and ``T - D >= m g sin(gamma)``, with ``0 <= gamma <= pi/2``. For a given speed the
largest ``gamma`` is the root of ``T - D(V, cos(gamma)) - m g sin(gamma)``
(:func:`aero_kernel.formulas.powered_flight.climb_angle`); it is maximised over the speed (scan, golden
section). Where the thrust exceeds the weight plus the zero-lift drag the climb is vertical over a range of
speeds and has no single ``V_x`` (entry, "When the answer is vertical"): the result is ``gamma = 90 deg``
at the upper edge of that range, declared with the notice ``powered_limit_declared``. An optimum on the stall
corner (the wing cannot carry the lift of a slower speed) is declared with the same notice.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.powered_flight import (
    RIGHT_ANGLE,
    Optimum,
    PoweredFlight,
    climb_angle,
    finish_climb,
    maximise_over_speed,
    vertical_upper_edge,
)
from aero_kernel.registry import formula

__all__ = ["best_angle_of_climb"]


@formula("best-angle-of-climb")
async def best_angle_of_climb(x: Inputs, ctx: Context) -> dict[str, float]:
    """The best angle of climb at full throttle and the speed it is flown at.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V,
            ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on
            route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations, declares
            the route and the vertical bound. Warnings of the answer's evaluation are forwarded, those
            of the iterates are not.

    Returns:
        ``v_x`` in m/s and ``gamma_max`` in degrees.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` if no speed gives a climb at full throttle;
            ``not_converged``; the failures of the drive train
            (``missing_input``, ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)

    optimum = await maximise_over_speed(
        lambda v: climb_angle(flight, v), flight, flight.climb_scan_start()
    )
    gamma = optimum.value
    if gamma >= RIGHT_ANGLE:
        optimum = Optimum(await vertical_upper_edge(flight, optimum.v), gamma, False)
    await finish_climb(flight, optimum, gamma)
    return {"v_x": optimum.v, "gamma_max": math.degrees(gamma)}
