"""Canon formula ``static-thrust-to-weight``: ``T_0 / W`` with ``T_0`` the thrust at ``V = 0``.

The formula embeds the propulsion relations (``embeds`` in the canon): the torque balance at
``V = 0``, the advance ratio, the table lookup and the thrust from the coefficient. It reads no
thrust value and holds no second implementation of any of them (ADR 0022).
"""

from collections.abc import Callable
from typing import ParamSpec, TypeVar, cast

from aero_kernel.components import Components
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.advance_ratio_from_speed import advance_ratio
from aero_kernel.formulas.motor_propeller_equilibrium import Balance, declare_route, equilibrium
from aero_kernel.formulas.propeller_table_lookup import Coefficients, components_of, table_lookup
from aero_kernel.formulas.thrust_at_airspeed_from_coefficient import thrust
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["static_thrust_to_weight"]

_P = ParamSpec("_P")
_R = TypeVar("_R")

_STATIC_SPEED_MS = 0.0  # the definition of "static": V = 0


def _relation(ctx: Context, item: str, kind: Callable[_P, _R]) -> Callable[_P, _R]:
    """The embedded relation of ``item``, typed as the function it is (``kind`` names the type)."""
    del kind
    return cast("Callable[_P, _R]", ctx.embedded(item))


def _optional(x: Inputs, name: str) -> float | None:
    """The value of an ``optional`` parameter, ``None`` if absent."""
    return None if x[name] is None else number(x, name)


@formula("static-thrust-to-weight")
async def static_thrust_to_weight(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static thrust over the weight, from the motor-propeller balance at ``V = 0``.

    Args:
        x: ``w`` the weight in N, ``components``, ``rho`` in kg/m^3, ``k_v`` in rpm/V, ``i_0`` in A,
            ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are
            bound for route A and not read on route B.
        ctx: The formula context; it hands out the embedded relations.

    Returns:
        ``t0_w`` (1), canon quantity ``static-thrust-to-weight``.

    Raises:
        TypeError: If ``components`` is not the components document.
        FormulaError: ``invalid_input`` for a weight not above zero; the failures of the embedded
            relations, unchanged.
    """
    weight = number(x, "w")
    if not weight > 0.0:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "non_positive_value",
            f"static-thrust-to-weight needs a weight > 0, got {weight} N.",
            "Give a positive aircraft mass.",
            detail={"value": weight},
            parameter="w",
        )
    components: Components = components_of(x)
    rho, d_prop = number(x, "rho"), number(x, "d_prop")
    balance: Balance = _relation(ctx, "calc:motor-propeller-equilibrium.default", equilibrium)(
        components,
        _STATIC_SPEED_MS,
        rho,
        number(x, "k_v"),
        _optional(x, "i_0"),
        _optional(x, "r_m"),
        number(x, "u_bat"),
        d_prop,
        config().powertrain_balance_tolerance.value,
    )
    j = _relation(ctx, "calc:advance-ratio-from-speed.default", advance_ratio)(
        _STATIC_SPEED_MS, balance.n_prop, d_prop
    )
    coefficients: Coefficients = _relation(
        ctx, "calc:propeller-table-lookup.default", table_lookup
    )(components, j, balance.n_prop)
    t_static = _relation(ctx, "calc:thrust-at-airspeed-from-coefficient.default", thrust)(
        coefficients.c_t, rho, balance.n_prop, d_prop
    )
    declare_route(ctx)
    return {"t0_w": t_static / weight}
