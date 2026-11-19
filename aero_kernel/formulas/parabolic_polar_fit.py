"""Canon formula ``parabolic-polar-fit``: the parabola fitted to the solver polar along level flight (ADR 0026).

The OPT adapter returns the solver polar along level flight: ``fit_points`` points equally spaced in
``C_L`` over the window ``[max(0.1, 0.1 C_L,max), 0.85 C_L,max]`` (rule ``parabolic-polar-fit``,
BR-16), each flown at the speed where ``L = m g``. This module fits ``C_D = C_D0 + k C_L^2`` to it by
least squares and reads the Oswald factor ``e = 1 / (pi AR k)`` of Anderson 6e 6.7.2. The result is for
display; no performance quantity reads it (ADR 0026). A polar that is not physically a parabola is
declared, never replaced.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula
from pydantic import JsonValue

__all__ = ["ParabolaFit", "fit_parabola", "parabolic_polar_fit"]

RULE = "parabolic-polar-fit"


@dataclass(frozen=True)
class ParabolaFit:
    """The least-squares parabola ``C_D = C_D0 + k C_L^2`` of a polar.

    Attributes:
        cd0: The intercept (zero-lift drag coefficient).
        k: The slope in ``C_L^2`` (induced-drag factor).
        rms: Root mean square of the solver ``C_D`` minus the parabola, over the points.
        max_abs: Largest absolute deviation of the solver ``C_D`` from the parabola.
    """

    cd0: float
    k: float
    rms: float
    max_abs: float


def fit_parabola(cl: Sequence[float], cd: Sequence[float]) -> ParabolaFit:
    """Fit ``C_D = C_D0 + k C_L^2`` to points by ordinary least squares in ``C_L^2``.

    Args:
        cl: The lift coefficients of the points (at least two distinct ``C_L^2``).
        cd: The drag coefficients of the points.

    Returns:
        The fit and its residual.
    """
    x = np.asarray(cl, dtype=float) ** 2
    y = np.asarray(cd, dtype=float)
    design = np.column_stack([np.ones_like(x), x])
    (cd0, k), *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ np.array([cd0, k])
    return ParabolaFit(
        cd0=float(cd0),
        k=float(k),
        rms=float(math.sqrt(float(np.mean(residual**2)))),
        max_abs=float(np.max(np.abs(residual))),
    )


def _window(x: Inputs, ctx: Context) -> list[float]:
    """The levels of the fit: ``fit_points`` values equally spaced over the window of ``C_L``.

    Raises:
        FormulaError: ``invalid_input`` if the window is empty or the number of points is not an
            integer of at least three.
    """
    rules = ctx.solvers.rules
    cl_max = number(x, "cl_max")
    low = max(
        rules.value(RULE, "window_cl_floor"), rules.value(RULE, "window_lower_fraction") * cl_max
    )
    high = rules.value(RULE, "window_upper_fraction") * cl_max
    if not high > low:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "invalid_input",
            f"the fit window of C_L is empty: C_L,max = {cl_max:.4g} gives [{low:.4g}, {high:.4g}]",
            "the fit needs an airplane whose C_L,max is clearly above the window floor",
            detail={"cl_low": low, "cl_high": high, "cl_max": cl_max},
            parameter="cl_max",
        )
    count = rules.value(RULE, "fit_points")
    if count != int(count) or count < 3:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "invalid_input",
            f"fit_points = {count} must be an integer of at least 3",
            "give rule_overrides['parabolic-polar-fit.fit_points'] an integer of at least 3",
        )
    return [low + (high - low) * i / (int(count) - 1) for i in range(int(count))]


def _nonphysical(fit: ParabolaFit, e_osw: float, ceiling: float) -> list[str]:
    """The reasons the fitted numbers are not physically meaningful (none if they are)."""
    reasons: list[str] = []
    if fit.k <= 0.0:
        reasons.append("k_not_positive")
    if fit.cd0 <= 0.0:
        reasons.append("cd0_not_positive")
    if e_osw > ceiling:
        reasons.append("e_above_maximum")
    return reasons


@formula("parabolic-polar-fit")
async def parabolic_polar_fit(x: Inputs, ctx: Context) -> dict[str, float]:
    """The zero-lift drag coefficient and the Oswald factor of the polar fitted to the solver.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, the ISA air
            state ``rho`` in kg/m^3, ``mu`` in Pa s and ``a`` in m/s, ``ar`` the aspect ratio (1)
            and ``cl_max`` the maximum lift coefficient (1).
        ctx: The formula context; ``ctx.solvers.opti`` computes the level-flight polar.

    Returns:
        ``cd0`` the zero-lift drag coefficient (1) and ``e_osw`` the Oswald factor (1).

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: ``invalid_input`` for an empty window; ``not_converged`` for a fitted slope of
            exactly zero (no finite Oswald factor) and from the adapter, unchanged.

    Warnings: ``polar_fit_residual`` (``notice``, every fit); ``polar_fit_nonphysical`` (``error``)
        if the slope or ``C_D0`` is at or below zero or ``e`` above ``max_oswald``: the fitted numbers
        are returned and declared, never replaced (ADR 0020).
    """
    levels = _window(x, ctx)
    flight = await ctx.solvers.opti.level_polar(
        airplane_of(x), number(x, "m"), number(x, "g"), air_state(x), levels
    )
    forward_warnings(ctx, flight.warnings)
    polar = flight.polar
    fit = fit_parabola(polar.cl, polar.cd)
    if math.isclose(fit.k, 0.0, abs_tol=config().opt_zero_span.value):
        raise FormulaError(
            ErrorCategory.NOT_CONVERGED,
            "not_converged",
            "the drag of the level-flight polar does not depend on the lift coefficient: the "
            "fitted slope is exactly zero, so there is no finite Oswald factor",
            "the solver polar is flat in C_L over the fit window; check the airplane",
            detail={"cd0": fit.cd0},
        )
    e_osw = 1.0 / (math.pi * number(x, "ar") * fit.k)
    detail: dict[str, JsonValue] = {
        "points": len(polar.cl),
        "cl_min": min(polar.cl),
        "cl_max": max(polar.cl),
        "v_min_ms": min(polar.v_ms),
        "v_max_ms": max(polar.v_ms),
        "rms": fit.rms,
        "max_abs": fit.max_abs,
        "max_relative": max(abs(r) / cd for r, cd in _residuals(polar.cl, polar.cd, fit)),
    }
    ctx.warn(
        "polar_fit_residual",
        f"The parabola C_D0 + k C_L^2 was fitted to {len(polar.cl)} level-flight points of the "
        f"solver polar (C_L {min(polar.cl):.3g} to {max(polar.cl):.3g}); the solver C_D differs "
        f"from it by {fit.rms:.2e} (RMS) and {fit.max_abs:.2e} (largest).",
        detail,
    )
    reasons = _nonphysical(fit, e_osw, ctx.solvers.rules.value(RULE, "max_oswald"))
    if reasons:
        ctx.warn(
            "polar_fit_nonphysical",
            "The fitted parabola is not physically meaningful: "
            f"C_D0 = {fit.cd0:.4g}, k = {fit.k:.4g}, e = {e_osw:.4g}. The numbers are returned "
            "as fitted and nothing replaces them; the closed forms that read them are refused "
            "where they are undefined.",
            {"reasons": list(reasons), "cd0": fit.cd0, "k": fit.k, "e_osw": e_osw},  # pyright: ignore[reportArgumentType]
        )
    return {"cd0": fit.cd0, "e_osw": e_osw}


def _residuals(
    cl: Sequence[float], cd: Sequence[float], fit: ParabolaFit
) -> list[tuple[float, float]]:
    """Per point: the solver ``C_D`` minus the parabola, and the solver ``C_D``."""
    return [(c - (fit.cd0 + fit.k * level * level), c) for level, c in zip(cl, cd, strict=True)]
