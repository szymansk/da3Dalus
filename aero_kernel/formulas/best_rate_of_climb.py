"""Canon formula ``best-rate-of-climb``: the speed and rate of the steepest-in-time steady climb at full throttle.

The entry maximises ``V sin(gamma)`` subject to the exact force balances of a steady climb,
``L = m g cos(gamma)`` and ``T - D >= m g sin(gamma)``, with ``0 <= gamma <= pi/2``. For a given speed the
largest ``gamma`` the thrust allows is the root of ``T - D(V, cos(gamma)) - m g sin(gamma)``
(:func:`aero_kernel.formulas.powered_flight.climb_angle`: the one drag solve at the load factor
``cos(gamma)``, the one full-throttle thrust); the rate of climb ``V sin(gamma)`` is then maximised over
the speed (scan, golden section). The vertical climb (``gamma = 90 deg``) is the entry's one declared exception to
"no bound active". An optimum on the stall corner is declared (notice), not a failure.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.powered_flight import (
    PoweredFlight,
    Unflyable,
    climb_angle,
    finish_climb,
    maximise_over_speed,
)
from aero_kernel.registry import formula

__all__ = ["best_rate_of_climb"]


@formula("best-rate-of-climb")
async def best_rate_of_climb(x: Inputs, ctx: Context) -> dict[str, float]:
    """The best rate of climb at full throttle and the speed it is flown at.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V,
            ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on
            route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations, declares
            the route and the bound the optimum lies on. Warnings of the answer's evaluation are forwarded, those
            of the iterates are not.

    Returns:
        ``v_y`` in m/s and ``roc_max`` in m/s.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` if no speed gives a climb at full throttle;
            ``not_converged``; the failures of the drive train
            (``missing_input``, ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)

    async def rate(v: float) -> float | Unflyable:
        gamma = await climb_angle(flight, v)
        return gamma if isinstance(gamma, Unflyable) else v * math.sin(gamma)

    optimum = await maximise_over_speed(rate, flight)
    gamma = await climb_angle(flight, optimum.v)
    if isinstance(
        gamma, Unflyable
    ):  # pragma: no cover - the optimum is evaluated at a speed that climbs
        msg = "the best-rate-of-climb speed does not climb"
        raise AssertionError(msg)
    await finish_climb(flight, optimum, gamma)
    return {"v_y": optimum.v, "roc_max": optimum.value}
