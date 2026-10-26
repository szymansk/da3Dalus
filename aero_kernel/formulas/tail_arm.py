"""The tail arm from the design CG, shared by ``horizontal-tail-arm`` and ``vertical-tail-arm`` (gh-1272)."""

from collections import Counter
from collections.abc import Collection

from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of, number
from pydantic import JsonValue

__all__ = ["tail_arm_from_cg"]


async def tail_arm_from_cg(
    x: Inputs, ctx: Context, surface_types: Collection[str], role: str
) -> float:
    """Distance along x from the design CG to the quarter-chord MAC of the one surface of the given types.

    The surface is chosen by ``surface_type`` only, never by position or planform. Its quarter-chord
    MAC is ASB's (``Wing.aerodynamic_center``), asked of the GEO adapter: the kernel integrates no
    planform of its own (ADR 0022).

    Args:
        x: ``airplane`` the geometry and ``x_cg`` the design CG in m (geometry frame, aft positive).
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.
        surface_types: The ``surface_type`` values that count as the tail.
        role: Name of the tail for the error message, e.g. ``horizontal tail``.

    Returns:
        The arm in m, aft positive.

    Raises:
        FormulaError: ``unsupported_configuration`` (``unsupported_layout``) unless exactly one wing
            has one of the types; from the adapter, unchanged.
    """
    airplane = airplane_of(x)
    wings = list((airplane.wings or {}).items())
    keys = [key for key, wing in wings if wing.surface_type in surface_types]
    if len(keys) != 1:
        found = sorted(str(wing.surface_type) for _, wing in wings)
        counts: dict[str, JsonValue] = dict(Counter(str(wing.surface_type) for _, wing in wings))
        detail: dict[str, JsonValue] = {"surface_types": list(found), "counts": counts}
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_layout",
            f"the tail arm needs exactly one {role} ({' or '.join(sorted(surface_types))}); "
            f"this airplane has {len(keys)} of them among the surfaces {', '.join(found)}",
            "a tailless wing, a canard, a tandem wing and a twin tail are not covered yet",
            detail=detail,
            parameter="airplane",
        )
    tail_x = await ctx.solvers.geometry.quarter_chord_mac_x(airplane, keys[0])
    return tail_x - number(x, "x_cg")
