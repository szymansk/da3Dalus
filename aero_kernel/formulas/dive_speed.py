"""Canon formula ``dive-speed``: the terminal speed of a vertical dive at full throttle.

Lift is zero, so the drag balances the weight plus the thrust: ``D(V, alpha_0) = m g + T(V)`` with
``alpha_0`` the zero-lift angle (the drag at the load factor 0, :class:`PoweredFlight`). The drag grows and
the thrust falls with the speed, so ``H(V) = D - m g - T`` rises through zero once; the upward scan brackets
it and Illinois regula falsi refines it. The drag of a windmilling or stopped propeller is not modelled
(canon ``Q-PT-10``); the thrust is the full-throttle thrust of the table. If the speed runs past the table of
the propeller before the root, the drive-train relation ends the search with ``outside_propeller_table``
(no extrapolation, gh-1411): the declared failure.
"""

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.powered_flight import (
    VERTICAL_FLIGHT,
    PoweredFlight,
    illinois_root,
    scan_speeds,
)
from aero_kernel.registry import formula

__all__ = ["dive_speed"]


async def _surplus(flight: PoweredFlight, v: float) -> float | None:
    """The drag at zero lift minus the weight and the thrust at full throttle at ``v`` (N).

    ``None`` where the lift curve has no zero-lift point before its first peak at this speed (a very low
    Reynolds number): the speed is skipped, the dive does not end there.
    """
    drag = await flight.drag(v, VERTICAL_FLIGHT)
    return None if drag is None else drag - flight.weight - flight.thrust(v)


async def _bracketed_surplus(flight: PoweredFlight, v: float) -> float:
    """The surplus at a speed inside a bracket, where the zero-lift point must exist."""
    return await flight.required_drag(v, VERTICAL_FLIGHT) - flight.weight - flight.thrust(v)


def _not_reached(at_start: bool) -> FormulaError:
    where = (
        "already at the first scan speed"
        if at_start
        else f"below the scan limit of {config().powered_speed_scan_limit.value:g} m/s"
    )
    return FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"the zero-lift drag does not reach the weight plus the full-throttle thrust {where}",
        "report the case; the scan limit ends the search",
    )


@formula("dive-speed")
async def dive_speed(x: Inputs, ctx: Context) -> dict[str, float]:
    """The speed at which a vertical dive at full throttle stops accelerating.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V,
            ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on
            route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations and
            declares the route. Warnings of the answer's evaluation are forwarded.

    Returns:
        ``v_d`` in m/s.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``not_converged`` if the drag does not reach the weight plus the thrust within
            the scan; the failures of the drive train (``missing_input``,
            ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)
    previous: tuple[float, float] | None = None
    for v in scan_speeds():
        surplus = await _surplus(flight, v)
        if surplus is None:
            continue
        if surplus > 0.0:
            if previous is None:
                break
            v_d = await illinois_root(
                lambda speed: _bracketed_surplus(flight, speed),
                previous,
                (v, surplus),
                flight.weight,
            )
            await flight.answer(v_d, VERTICAL_FLIGHT)
            return {"v_d": v_d}
        previous = (v, surplus)
    raise _not_reached(previous is None)
