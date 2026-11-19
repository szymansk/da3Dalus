"""Canon formula ``max-level-speed``: the highest speed at which full-throttle thrust still equals drag in level flight.

The entry maximises ``V`` subject to ``L(V, alpha) = m g``, ``T(V, n_prop) >= D(V, alpha)`` and the
motor-propeller balance at ``(V, n_prop)``. ``alpha`` and ``n_prop`` are eliminated by the two existing
solves (the level-flight point and the torque balance, :class:`PoweredFlight`), so the problem is the
largest ``V`` with ``G(V) = T(V) - D(V) >= 0``: the last crossing of ``G`` from positive to negative.

The upward scan of the airspeed runs to the end of the evaluable range (the scan limit, or the end of the
propeller table, which is a bound of the search) and keeps the last positive-to-negative change of ``G``;
Illinois regula falsi refines it. A thrust curve that dips below the drag and recovers is therefore handled
inside the scan (features no narrower than the scan step). If the thrust is still above the drag at the last
speed the table covers, the optimum is on the bound: the declared failure ``outside_propeller_table``. The
spurious branch below the stall (the entry's multi-start rule) cannot occur: the level-flight point lives on
the branch before the first lift peak, and the speeds the wing cannot fly are skipped and declared.
"""

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.powered_flight import (
    LEVEL_FLIGHT,
    TABLE_FAILURE,
    PoweredFlight,
    Unflyable,
    illinois_root,
    never_flyable,
    scan_speeds,
    table_failure,
)
from aero_kernel.registry import formula

__all__ = ["highest_level_speed", "max_level_speed"]


async def _excess(flight: PoweredFlight, v: float) -> float | Unflyable:
    """The thrust at full throttle minus the level-flight drag at ``v``; ``WING`` below the stall."""
    drag = await flight.drag(v, LEVEL_FLIGHT)
    return Unflyable.WING if drag is None else flight.thrust(v) - drag


async def _bracketed_excess(flight: PoweredFlight, v: float) -> float:
    """The thrust excess at a speed inside a bracket, where the wing must be able to fly level."""
    return flight.thrust(v) - await flight.required_drag(v, LEVEL_FLIGHT)


def _beyond_scan(v: float) -> FormulaError:
    return FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"the thrust still exceeds the level-flight drag at the scan limit of "
        f"{config().powered_speed_scan_limit.value:g} m/s",
        "report the case; the scan limit ends the search",
        detail={"v_ms": v},
    )


async def highest_level_speed(flight: PoweredFlight) -> float:
    """The highest speed in m/s at which the thrust at full throttle still equals the level-flight drag.

    The one search of ``max-level-speed`` (the entry's problem at the mass of ``flight``): the upward scan
    from the clean stall speed ``flight.v_s``, the last positive-to-negative change of ``T - D``, Illinois
    regula falsi. Nothing is forwarded or declared: the caller evaluates its answer with
    :meth:`PoweredFlight.answer`. ``mass-envelope`` evaluates this same function at each mass of its sweep
    (one producer of ``V_max``, ADR 0022).

    Raises:
        FormulaError: As documented on :func:`max_level_speed`.
    """
    reasons: set[Unflyable] = set()
    last: tuple[float, float] | None = None  # the last evaluated speed and its excess
    crossing: tuple[tuple[float, float], tuple[float, float]] | None = None
    edge: FormulaError | None = None
    for v in scan_speeds(flight.v_s):
        try:
            excess = await _excess(flight, v)
        except FormulaError as error:
            if error.code != TABLE_FAILURE:
                raise
            edge = error
            reasons.add(Unflyable.TABLE)
            break
        if isinstance(excess, Unflyable):
            reasons.add(excess)
            flight.note_skipped(v, excess)
            continue
        if last is not None and last[1] > 0.0 >= excess:
            crossing = (last, (v, excess))
        elif excess <= 0.0:
            reasons.add(Unflyable.THRUST)
        last = (v, excess)
    if last is None or (crossing is None and last[1] <= 0.0):
        raise never_flyable(reasons, flight.v_s)
    if crossing is None or last[1] > 0.0:
        if edge is not None:
            raise table_failure(
                last[0], "the thrust is still above the drag at the last speed the table covers"
            )
        raise _beyond_scan(last[0])
    v_max = await illinois_root(
        lambda speed: _bracketed_excess(flight, speed), crossing[0], crossing[1], flight.weight
    )
    return v_max


@formula("max-level-speed")
async def max_level_speed(x: Inputs, ctx: Context) -> dict[str, float]:
    """The maximum speed of level flight at full throttle.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V,
            ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on
            route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations and
            declares the route and the speeds skipped. Warnings of the answer's evaluation are
            forwarded, those of the iterates are not.

    Returns:
        ``v_max`` in m/s.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` if the thrust is never above the drag at a speed the wing can
            fly (the message says whether the wing or the thrust stopped every speed); ``not_converged``
            if the thrust still exceeds the drag at the scan limit; ``outside_propeller_table`` if it
            still does where the table ends; ``missing_input`` for an absent ``R_m`` or ``I_0``.
    """
    flight = PoweredFlight(x, ctx)
    v_max = await highest_level_speed(flight)
    await flight.answer(v_max, LEVEL_FLIGHT)
    return {"v_max": v_max}
