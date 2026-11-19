"""Canon formula ``thrust-at-airspeed-from-coefficient``: ``T = C_T rho n^2 D^4`` (Brandt & Selig 2011, II.F)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula, relation

__all__ = ["thrust", "thrust_at_airspeed_from_coefficient"]


@relation("thrust-at-airspeed-from-coefficient")
def thrust(c_t: float, rho: float, n_prop: float, d_prop: float) -> float:
    """The thrust of a propeller from its thrust coefficient (the definition of ``C_T`` read backwards).

    Args:
        c_t: Thrust coefficient (1); negative past the zero-thrust point, and then passed on as is.
        rho: Air density in kg/m^3.
        n_prop: Propeller speed in 1/s.
        d_prop: Propeller diameter in m.

    Returns:
        The thrust in N.
    """
    return c_t * rho * n_prop**2 * d_prop**4


@formula("thrust-at-airspeed-from-coefficient")
async def thrust_at_airspeed_from_coefficient(x: Inputs, ctx: Context) -> dict[str, float]:
    """The thrust at the propeller speed and advance ratio the coefficient belongs to.

    Args:
        x: ``c_t`` (1), ``rho`` in kg/m^3, ``n_prop`` in 1/s, ``d_prop`` in m.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``t`` in N, canon quantity ``thrust-at-airspeed``.
    """
    del ctx
    return {
        "t": thrust(number(x, "c_t"), number(x, "rho"), number(x, "n_prop"), number(x, "d_prop"))
    }
