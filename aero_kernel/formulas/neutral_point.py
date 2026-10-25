"""Canon formula ``neutral-point``: x_NP over three method worlds (ARCHITECTURE ch. 8.5, 8.13; ADR 0027).

One coroutine, switching on ``ctx.world`` (worlds are runs of one implementation, A7). The textbook
and Pappas worlds are the barycentre of the wing and the tail; the AVL world asks the vortex lattice.
All three are incompressible (Mach 0) and model no fuselage.
"""

from collections import Counter

from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of, forward_warnings, number
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import SurfaceProperties
from aero_kernel.registry import formula
from aero_kernel.solvers.asb_airplane import AC_FRACTION

__all__ = ["neutral_point"]

# Pappas, "If It Flies", Model Aviation 10/2009: the downwash factor 1 - 3.24 / AR_w (after von Mises,
# Prager, Kuerti).
PAPPAS_DOWNWASH = 3.24
# The surface types allowed beside the one main wing and the one horizontal tail (any number).
_BESIDE = frozenset({"vertical_tail", "winglet"})


def _layout(airplane: AirplaneGeometry) -> tuple[str, str]:
    """The keys of the main wing and the horizontal tail of a supported layout, from ``surface_type`` only.

    Raises:
        FormulaError: ``unsupported_configuration`` (``unsupported_layout``) unless there is exactly
            one ``main_wing`` and one ``horizontal_tail`` (any ``vertical_tail`` and ``winglet``).
    """
    wings = list((airplane.wings or {}).items())
    types = Counter(wing.surface_type for _, wing in wings)
    others = set(types) - {"main_wing", "horizontal_tail"} - _BESIDE
    if types["main_wing"] != 1 or types["horizontal_tail"] != 1 or others:
        found = sorted(str(wing.surface_type) for _, wing in wings)
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_layout",
            "the neutral point is defined here for one main wing with one horizontal tail; "
            f"this airplane has the surfaces {', '.join(found)}",
            "a tailless wing, a canard, a tandem wing and a V-tail are not covered yet",
            detail={"surface_types": list(found)},
            parameter="airplane",
        )
    main = next(key for key, wing in wings if wing.surface_type == "main_wing")
    tail = next(key for key, wing in wings if wing.surface_type == "horizontal_tail")
    return main, tail


def _barycentre(main: SurfaceProperties, tail: SurfaceProperties, weight: float) -> float:
    """``(S_w x_ac,w + K S_h x_ac,h) / (S_w + K S_h)`` with the tail weight ``K``."""
    x_main = main.x_le_mac + AC_FRACTION * main.c_mac
    x_tail = tail.x_le_mac + AC_FRACTION * tail.c_mac
    return (main.area * x_main + weight * tail.area * x_tail) / (main.area + weight * tail.area)


def _lift_slope_ratio(main: SurfaceProperties, tail: SurfaceProperties) -> float:
    """``[AR_h / (AR_h + 2)] / [AR_w / (AR_w + 2)]``: the tail's lift slope over the wing's."""
    return (tail.aspect_ratio / (tail.aspect_ratio + 2.0)) / (
        main.aspect_ratio / (main.aspect_ratio + 2.0)
    )


@formula("neutral-point")
async def neutral_point(x: Inputs, ctx: Context) -> dict[str, float]:
    """The neutral point of the airplane in the world of ``ctx.world``.

    - ``textbook``: ``K = eta (1 - 4/(AR_w + 2)) [AR_h/(AR_h + 2)] / [AR_w/(AR_w + 2)]``, ``eta`` the input
      ``tail-efficiency``, derived from Sadraey Eq. 6.67 (§6.7.12) with the lift slopes ``2 pi AR / (AR + 2)`` and the
      downwash ``2 a_w / (pi AR_w)``.
    - ``pappas``: ``K = (1 - 3.24/AR_w) [1/(1 + 2/AR_h)] / [1/(1 + 2/AR_w)]`` (Pappas 10/2009).
      Pappas and AVL imply ``eta = 1``: part of the textbook-Pappas gap is the choice of ``eta``.
    - ``avl``: the vortex lattice at the lift coefficient ``m g / (1/2 rho V_md^2 S_ref)`` with the
      kernel's ``S_ref``. It adds no regime warning: those come with ``V_md`` and are inherited.

    The textbook and Pappas worlds take the area, aspect ratio, MAC and MAC leading edge of the main wing
    and of the tail from the GEO adapter, i.e. AeroSandbox (#1253).

    The layout is checked first, in every world, from ``surface_type`` only; AVL is never started
    for a refused layout. Every world declares ``fuselage_not_modelled``.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, ``rho`` the
            air density in kg/m^3, ``v_md`` the minimum-drag speed in m/s and ``eta_h`` the tail
            efficiency (1, used by the textbook world only).
        ctx: The formula context; ``ctx.world`` is the world, ``ctx.solvers.avl`` the AVL adapter.

    Returns:
        ``x_np`` in m, in the geometry frame, aft positive.

    Raises:
        TypeError: If a number is not a number or ``ctx.world`` is not a world of this formula.
        FormulaError: ``unsupported_layout``; from the adapter, unchanged.
    """
    airplane = airplane_of(x)
    main_key, tail_key = _layout(airplane)
    ctx.warn(
        "fuselage_not_modelled",
        "The fuselage's destabilising contribution is not included in the neutral point (a declared "
        "simplification: about 1-2 % MAC on the reference fleet, USAF DATCOM 4.2.2.1), so the neutral "
        "point is slightly too far aft; larger for a fat fuselage or a long nose.",
    )
    world = ctx.world
    if world in ("textbook", "pappas"):
        main = await ctx.solvers.geometry.surface_reference(airplane, main_key)
        tail = await ctx.solvers.geometry.surface_reference(airplane, tail_key)
        if world == "textbook":
            weight = (
                number(x, "eta_h")
                * (1.0 - 4.0 / (main.aspect_ratio + 2.0))
                * _lift_slope_ratio(main, tail)
            )
        else:
            weight = (1.0 - PAPPAS_DOWNWASH / main.aspect_ratio) * _lift_slope_ratio(main, tail)
        return {"x_np": _barycentre(main, tail, weight)}
    if world == "avl":
        dynamic_pressure = 0.5 * number(x, "rho") * number(x, "v_md") ** 2
        reference = await ctx.solvers.geometry.main_wing_reference(airplane)
        cl = number(x, "m") * number(x, "g") / (dynamic_pressure * reference.s_ref)
        found = await ctx.solvers.avl.neutral_point(airplane, cl)
        forward_warnings(ctx, found.warnings)
        return {"x_np": found.x_np}
    msg = f"neutral-point has no world {world!r}"
    raise TypeError(msg)
