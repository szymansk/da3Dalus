"""Canon formula ``dive-speed``: the terminal speed of a vertical dive at full throttle.

Lift is zero, so the drag balances the weight plus the thrust: ``D(V, alpha_0) = m g + T(V)`` with
``alpha_0`` the zero-lift angle (the drag at the load factor 0, :class:`PoweredFlight`). The drag grows and
the thrust falls with the speed, so ``H(V) = D - m g - T`` rises through zero once; the upward scan brackets
it and Illinois regula falsi refines it. The drag of a windmilling or stopped propeller is not modelled
(canon ``Q-PT-10``); the thrust is the full-throttle thrust of the table. If the speed runs past the table of
the propeller before the root, the drive-train relation ends the search with ``outside_propeller_table``
(no extrapolation, gh-1411): the declared failure.

The scan starts at the clean stall speed ``v_s`` (gh-1419). There the zero-lift drag is ``C_D0 / C_L,max`` of the
weight, so the surplus is negative, and the root lies above ``v_s``, if ``C_D0 / C_L,max < 1 + T(v_s) / (m g)``.
Where the surplus is already positive at ``v_s`` the terminal speed lies below it: the declared failure
``no_feasible_speed`` says so.
"""

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.powered_flight import (
    TABLE_FAILURE,
    VERTICAL_FLIGHT,
    PoweredFlight,
    illinois_root,
    no_feasible_speed,
    scan_speeds,
    table_failure,
)
from aero_kernel.registry import formula

__all__ = ["dive_speed"]


async def _surplus(flight: PoweredFlight, v: float) -> float:
    """The drag at zero lift minus the weight and the thrust at full throttle at ``v`` (N).

    The zero-lift point must exist at every speed (a lift curve that does not cross zero before its first
    peak is a failure of the adapter, not a stall: it is raised, not skipped).

    Raises:
        FormulaError: ``outside_propeller_table`` naming the speed at which the dive left the table.
    """
    drag = await flight.required_drag(v, VERTICAL_FLIGHT)
    try:
        thrust = flight.thrust(v)
    except FormulaError as error:
        if error.code != TABLE_FAILURE:
            raise
        raise table_failure(
            v,
            f"the dive left the propeller table at {v:.4g} m/s before the zero-lift drag "
            f"({drag:.4g} N) reached the weight ({flight.weight:.4g} N) plus the thrust",
        ) from error
    return drag - flight.weight - thrust


def _not_reached() -> FormulaError:
    return FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        "the zero-lift drag does not reach the weight plus the full-throttle thrust below the scan limit "
        f"of {config().powered_speed_scan_limit.value:g} m/s",
        "report the case; the scan limit ends the search",
    )


def _below_the_stall_speed(v: float, surplus: float) -> FormulaError:
    """The dive is already terminal at the first scan speed: its speed lies below the clean stall speed."""
    return no_feasible_speed(
        f"the zero-lift drag already exceeds the weight plus the full-throttle thrust by {surplus:.4g} N at "
        f"the clean stall speed {v:.4g} m/s, so the terminal speed of the dive lies below the clean stall "
        "speed, where the scan does not look"
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
        FormulaError: ``no_feasible_speed`` if the drag already exceeds the weight plus the thrust at the
            clean stall speed; ``not_converged`` if the drag does not reach the weight plus the thrust within
            the scan; the failures of the drive train (``missing_input``,
            ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)
    previous: tuple[float, float] | None = None
    for v in scan_speeds(flight.v_s):
        surplus = await _surplus(flight, v)
        if surplus > 0.0:
            if previous is None:
                raise _below_the_stall_speed(v, surplus)
            v_d = await illinois_root(
                lambda speed: _surplus(flight, speed),
                previous,
                (v, surplus),
                flight.weight,
            )
            await flight.answer(v_d, VERTICAL_FLIGHT)
            return {"v_d": v_d}
        previous = (v, surplus)
    raise _not_reached()
