"""Canon formula ``propeller-table-lookup``: ``C_T`` (and ``C_P``) of the fitted propeller at ``J`` and ``n``.

The table is the caller's (``Components.propeller.table``, APC's PER3 data: one rpm block per
propeller speed, ``C_T(J)`` and ``C_P(J)`` in each). A block holds one Reynolds number
(Brandt & Selig 2011, II.F), so the coefficient at a propeller speed between two blocks is the
linear interpolation, in rpm, of the two blocks' linear interpolations in ``J``: continuous in the
speed, which the torque balance of ``motor-propeller-equilibrium`` needs (ARCHITECTURE ch. 8.11,
rule 2: interpolated across blocks).

There is no extrapolation and no clamp (ADR 0020): a speed outside the first and last block, or an
advance ratio beyond the tabulated range of a block the speed needs, is the declared failure
``outside_propeller_table``.
"""

from bisect import bisect_right
from dataclasses import dataclass

from aero_kernel.components import Components, PropellerTable, RpmBlock
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula, relation
from pydantic import JsonValue

__all__ = ["Coefficients", "components_of", "propeller_table_lookup", "table_lookup"]

_RPM_PER_HZ = 60.0


@dataclass(frozen=True)
class Coefficients:
    """The propeller coefficients at one point of the table.

    Attributes:
        c_t: Thrust coefficient (1).
        c_p: Power coefficient (1).
    """

    c_t: float
    c_p: float


def components_of(x: Inputs) -> Components:
    """The pushed components bound to the parameter ``components``."""
    value = x["components"]
    if not isinstance(value, Components):
        msg = f"parameter 'components' must be the components, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def table_of(components: Components) -> PropellerTable:
    """The propeller table of the components.

    Raises:
        FormulaError: ``missing_input`` if the propeller or its table is not pushed.
    """
    if components.propeller is None or components.propeller.table is None:
        absent = (
            "components.propeller" if components.propeller is None else "components.propeller.table"
        )
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "missing_input",
            f"propeller-table-lookup needs `{absent}`, which the pushed components do not carry.",
            "Push the propeller's performance table (C_T and C_P per rpm block) with the components.",
            detail={"inputs": list[JsonValue]([absent])},
            parameter="components",
        )
    return components.propeller.table


def _outside(message: str, detail: dict[str, JsonValue]) -> FormulaError:
    """The declared failure of a point the table does not cover."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "outside_propeller_table",
        message,
        "Use a propeller whose table covers the operating point; the kernel does not extrapolate.",
        detail=detail,
    )


def _in_block(block: RpmBlock, j: float) -> Coefficients:
    """Linear interpolation in ``J`` within one block; ``j`` must lie inside the block's range."""
    if not block.j[0] <= j <= block.j[-1]:
        raise _outside(
            f"the advance ratio J = {j:.6g} is outside the table at {block.rpm:g} rpm "
            f"(J from {block.j[0]:g} to {block.j[-1]:g}).",
            {"j": j, "rpm": block.rpm, "j_min": block.j[0], "j_max": block.j[-1]},
        )
    upper = min(max(bisect_right(block.j, j), 1), len(block.j) - 1)
    lower = upper - 1
    span = block.j[upper] - block.j[lower]
    fraction = (j - block.j[lower]) / span
    return Coefficients(
        c_t=block.ct[lower] + fraction * (block.ct[upper] - block.ct[lower]),
        c_p=block.cp[lower] + fraction * (block.cp[upper] - block.cp[lower]),
    )


@relation("propeller-table-lookup")
def table_lookup(components: Components, j: float, n_prop: float) -> Coefficients:
    """``C_T`` and ``C_P`` of the fitted propeller at the advance ratio and the propeller speed.

    The relation embedded by the propulsion embedders and called by the formula below (ADR 0022).

    Args:
        components: The pushed components; the table is ``components.propeller.table``.
        j: Advance ratio (1), >= 0.
        n_prop: Propeller speed in 1/s.

    Returns:
        The coefficients, interpolated in ``J`` and in rpm.

    Raises:
        FormulaError: ``missing_input`` if no table is pushed; ``outside_propeller_table`` if the
            speed is outside the first and last block or ``j`` outside the range of a block used.
    """
    blocks = table_of(components).blocks
    rpm = n_prop * _RPM_PER_HZ
    if not blocks[0].rpm <= rpm <= blocks[-1].rpm:
        raise _outside(
            f"the propeller speed {rpm:.6g} rpm is outside the table "
            f"({blocks[0].rpm:g} to {blocks[-1].rpm:g} rpm).",
            {"rpm": rpm, "rpm_min": blocks[0].rpm, "rpm_max": blocks[-1].rpm},
        )
    upper = min(max(bisect_right([b.rpm for b in blocks], rpm), 1), len(blocks) - 1)
    if len(blocks) == 1:
        return _in_block(blocks[0], j)
    low, high = blocks[upper - 1], blocks[upper]
    fraction = (rpm - low.rpm) / (high.rpm - low.rpm)
    at_low = _in_block(low, j)
    if fraction == 0.0:
        return at_low
    at_high = _in_block(high, j)
    return Coefficients(
        c_t=at_low.c_t + fraction * (at_high.c_t - at_low.c_t),
        c_p=at_low.c_p + fraction * (at_high.c_p - at_low.c_p),
    )


@formula("propeller-table-lookup")
async def propeller_table_lookup(x: Inputs, ctx: Context) -> dict[str, float]:
    """Read the coefficients of the fitted propeller from its table.

    Args:
        x: ``components`` the pushed components, ``j`` the advance ratio (1) and ``n_prop`` the
            propeller speed in 1/s that selects the rpm blocks.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``c_t`` (1), canon quantity ``thrust-coefficient``, and ``c_p`` (1), which the application
        does not expose: the embedders read it through the relation.

    Raises:
        TypeError: If ``components`` is not the components document.
        FormulaError: From :func:`table_lookup`, unchanged.
    """
    del ctx
    found = table_lookup(components_of(x), number(x, "j"), number(x, "n_prop"))
    return {"c_t": found.c_t, "c_p": found.c_p}
