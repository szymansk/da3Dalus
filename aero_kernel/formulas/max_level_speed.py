"""Canon formula ``max-level-speed``: the highest speed at which full-throttle thrust still equals drag in level flight.

The entry maximises ``V`` subject to ``L(V, alpha) = m g``, ``T(V, n_prop) >= D(V, alpha)`` and the
motor-propeller balance at ``(V, n_prop)``. ``alpha`` and ``n_prop`` are eliminated by the two existing
solves (the level-flight point and the torque balance, :class:`PoweredFlight`), so the problem is the
highest root of the thrust excess ``G(V) = T(V) - D(V)``. The upward scan of the airspeed finds the
highest sign change from positive to negative, Illinois regula falsi refines it. The spurious branch below
the stall (the entry's multi-start rule) cannot occur: the level-flight point lives on the branch before the
first lift peak, and the scan skips the speeds the wing cannot fly.

If the thrust runs past the table of the propeller before it falls to the drag, the drive-train relations
end the search with ``outside_propeller_table`` (no extrapolation, gh-1411): the declared failure.
"""

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.powered_flight import (
    LEVEL_FLIGHT,
    PoweredFlight,
    illinois_root,
    no_feasible_speed,
    scan_speeds,
)
from aero_kernel.registry import formula

__all__ = ["max_level_speed"]


async def _excess(flight: PoweredFlight, v: float) -> float | None:
    """The thrust at full throttle minus the level-flight drag at ``v``; ``None`` below the stall."""
    drag = await flight.drag(v, LEVEL_FLIGHT)
    return None if drag is None else flight.thrust(v) - drag


async def _bracketed_excess(flight: PoweredFlight, v: float) -> float:
    """The thrust excess at a speed inside a bracket, where the wing must be able to fly level."""
    return flight.thrust(v) - await flight.required_drag(v, LEVEL_FLIGHT)


def _no_level_flight(table_end: float | None) -> FormulaError:
    where = (
        "at every speed the wing can fly in the scan"
        if table_end is None
        else f"at every speed the propeller table covers (it ends before {table_end:.4g} m/s)"
    )
    return no_feasible_speed(f"the thrust at full throttle is below the level-flight drag {where}")


def _beyond_scan(v: float) -> FormulaError:
    return FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"the thrust still exceeds the level-flight drag at the scan limit of "
        f"{config().powered_speed_scan_limit.value:g} m/s",
        "report the case; the scan limit ends the search",
        detail={"v_ms": v},
    )


@formula("max-level-speed")
async def max_level_speed(x: Inputs, ctx: Context) -> dict[str, float]:
    """The maximum speed of level flight at full throttle.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V,
            ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on
            route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations and
            declares the route. Warnings of the answer's evaluation are forwarded, those of the
            iterates are not.

    Returns:
        ``v_max`` in m/s.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` if the thrust is below the drag at every
            speed the wing can fly; ``not_converged`` if the thrust still exceeds the drag at the scan
            limit; the failures of the drive train (``missing_input``, ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)
    last_positive: tuple[float, float] | None = None
    for v in scan_speeds():
        try:
            excess = await _excess(flight, v)
        except FormulaError as error:
            if last_positive is not None or error.code != "outside_propeller_table":
                raise
            raise _no_level_flight(v) from error
        if excess is None:
            continue
        if excess > 0.0:
            last_positive = (v, excess)
        elif last_positive is not None:
            v_max = await illinois_root(
                lambda speed: _bracketed_excess(flight, speed),
                last_positive,
                (v, excess),
                flight.weight,
            )
            await flight.answer(v_max, LEVEL_FLIGHT)
            return {"v_max": v_max}
    if last_positive is None:
        raise _no_level_flight(None)
    raise _beyond_scan(last_positive[0])
