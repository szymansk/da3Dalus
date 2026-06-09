"""Aircraft speed polar (Geschwindigkeitspolare) — closed-form, pure math (gh-841).

Reference formulas (ISA sea level, parabolic drag polar):
    W = m · g                          [N]       g = 9.80665 m/s²
    V(CL) = sqrt(2W / (ρ · S · CL))  [m/s]     ρ = 1.225 kg/m³
    CD = CD0 + k · CL²                           k = 1 / (π · AR · e)
    sink(CL) = V · CD / CL            [m/s]

Special CL values:
    CL_bg   = sqrt(CD0 / k)           best-glide  ((L/D)_max tangent from origin)
    CL_ms   = sqrt(3 · CD0 / k)       min-sink    (= √3 · CL_bg)
    V_ms    ≈ 0.76 · V_bg             (closed-form ratio for parabolic polar)

All inputs/outputs use SI units.  No AeroSandbox, no solver dependencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, NamedTuple

# ISA sea-level constants
_G = 9.80665  # m/s²
_RHO_ISA_SL = 1.225  # kg/m³

# Speed-polar sweep: CL from CL_ms·1.4 down to CL_min_sweep
_CL_SWEEP_POINTS = 200
_CL_MIN_RATIO = 0.25  # fraction of CL_bg — stops before stall region

# Reynolds mode (gh-924): one Picard pass re-looks-up cd0/e at the converged
# speed, matching the characteristic-speed chips (assumption_compute_service,
# gh-493) so the polar's V_md / V_min_sink markers equal the chip values.
_PICARD_PASSES = 1


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpeedPolarPoint:
    """A single (V, sink, CL) triplet on the polar curve."""

    v_mps: float
    sink_mps: float
    cl: float


@dataclass(frozen=True)
class SpeedPolarResult:
    """Full speed polar for a single aircraft configuration.

    Attributes
    ----------
    v_mps : list of V values [m/s] (ascending)
    sink_mps : list of corresponding sink rates [m/s] (positive = down)
    cl : list of CL values (descending, paired with v/sink)
    best_glide : SpeedPolarPoint at (L/D)_max — tangent from origin
    min_sink : SpeedPolarPoint at minimum sink rate
    inputs : dict with the inputs that produced this result (for provenance)
    """

    v_mps: list[float]
    sink_mps: list[float]
    cl: list[float]
    best_glide: SpeedPolarPoint
    min_sink: SpeedPolarPoint
    inputs: dict


class _MissingInputs(NamedTuple):
    missing: list[str]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_speed_polar(
    mass_kg: float | None,
    s_ref_m2: float | None,
    ar: float | None,
    e_oswald: float | None,
    cd0: float | None,
    *,
    rho: float = _RHO_ISA_SL,
    polar_re_table: list[dict[str, Any]] | None = None,
    mac_m: float | None = None,
    cl_max: float | None = None,
) -> SpeedPolarResult | _MissingInputs:
    """Compute the aircraft speed polar from parabolic-polar parameters.

    Returns a ``SpeedPolarResult`` on success, or a ``_MissingInputs``
    tuple listing the absent / non-positive parameters when the caller
    should produce an empty-state response.

    Parameters
    ----------
    mass_kg : aircraft mass [kg]
    s_ref_m2 : reference wing area [m²]
    ar : aspect ratio (dimensionless)
    e_oswald : Oswald efficiency factor (dimensionless, 0 < e ≤ 1) — used as the
        fallback / legacy value when ``polar_re_table`` is not supplied
    cd0 : zero-lift drag coefficient (dimensionless, > 0) — fallback / legacy
    rho : air density [kg/m³], default ISA sea-level 1.225
    polar_re_table : optional Reynolds-binned cd0/e table. When supplied (with
        ``mac_m``), the curve and the V_md / V_min_sink markers use the
        Reynolds-dependent ``cd0(V)`` / ``e(V)`` model — the SAME model the
        characteristic-speed chips use (gh-493) — so the polar markers match
        the chips instead of diverging (gh-924).
    mac_m : mean aerodynamic chord [m], required for the Reynolds lookups.
    cl_max : maximum lift coefficient. When supplied, the CL sweep is truncated
        at ``cl_max`` (the curve stops at V_stall instead of plotting a
        physically-unreachable sub-stall region) and V_md / V_min_sink are
        clamped to V_stall = V(cl_max) (gh-683), matching the chips.
    """
    missing = _check_inputs(mass_kg=mass_kg, s_ref_m2=s_ref_m2, ar=ar, e_oswald=e_oswald, cd0=cd0)
    if missing:
        return _MissingInputs(missing=missing)

    # All inputs validated — narrow types
    assert mass_kg is not None and s_ref_m2 is not None
    assert ar is not None and e_oswald is not None and cd0 is not None

    weight_n = mass_kg * _G

    reynolds_mode = bool(polar_re_table) and mac_m is not None and mac_m > 0

    def _cd0_e_at(v: float) -> tuple[float, float]:
        """Reynolds cd0(V)/e(V) when a table is supplied, else the fixed pair."""
        if reynolds_mode:
            from app.services.polar_re_table_service import (
                lookup_cd0_at_v,
                lookup_e_oswald_at_v,
            )

            assert polar_re_table is not None and mac_m is not None
            return (
                lookup_cd0_at_v(v, polar_re_table, mac_m, rho),
                lookup_e_oswald_at_v(v, polar_re_table),
            )
        return cd0, e_oswald

    # V_stall and the CL ceiling for the sweep / marker clamp.
    v_stall = _velocity(weight_n, rho, s_ref_m2, cl_max) if (cl_max and cl_max > 0) else None

    # --- Special CL points (best-glide, min-sink) -------------------------
    # One Picard pass: solve the closed-form optimum, re-look-up cd0/e at the
    # converged speed, solve once more — identical to the chips' refinement.
    cl_bg, v_bg, cd0_bg, k_bg = _converge_special_point(
        _cl_best_glide, cd0, e_oswald, ar, weight_n, rho, s_ref_m2, _cd0_e_at
    )
    cl_ms, v_ms, cd0_ms, k_ms = _converge_special_point(
        _cl_min_sink, cd0, e_oswald, ar, weight_n, rho, s_ref_m2, _cd0_e_at
    )

    # Clamp V_md / V_min_sink to V_stall — the closed-form optimum CL can
    # exceed CL_max (high-AR / draggy polars), back-solving an unreachable
    # sub-stall speed (gh-683). Clamping surfaces the real operating point.
    if v_stall is not None and cl_max is not None:
        if cl_bg >= cl_max:
            cl_bg, v_bg = cl_max, v_stall
            cd0_bg, e_bg = _cd0_e_at(v_bg)
            k_bg = _induced_drag_factor(ar, e_bg)
        if cl_ms >= cl_max:
            cl_ms, v_ms = cl_max, v_stall
            cd0_ms, e_ms = _cd0_e_at(v_ms)
            k_ms = _induced_drag_factor(ar, e_ms)

    bg = SpeedPolarPoint(
        v_mps=round(v_bg, 4),
        sink_mps=round(_sink_rate(v_bg, cd0_bg, k_bg, cl_bg), 5),
        cl=round(cl_bg, 6),
    )
    ms = SpeedPolarPoint(
        v_mps=round(v_ms, 4),
        sink_mps=round(_sink_rate(v_ms, cd0_ms, k_ms, cl_ms), 5),
        cl=round(cl_ms, 6),
    )

    # --- Curve sweep ------------------------------------------------------
    # High-CL (low-speed) end: stop at CL_max so we never plot past stall.
    cl_high = cl_ms * 1.40
    if cl_max and cl_max > 0:
        cl_high = min(cl_high, cl_max)
    cl_low = cl_bg * _CL_MIN_RATIO
    cl_arr = _linspace(cl_high, cl_low, _CL_SWEEP_POINTS)

    v_arr: list[float] = []
    sink_arr: list[float] = []
    for cl in cl_arr:
        v = _velocity(weight_n, rho, s_ref_m2, cl)
        cd0_v, e_v = _cd0_e_at(v)
        k_v = _induced_drag_factor(ar, e_v)
        v_arr.append(round(v, 4))
        sink_arr.append(round(_sink_rate(v, cd0_v, k_v, cl), 5))

    return SpeedPolarResult(
        v_mps=v_arr,
        sink_mps=sink_arr,
        cl=[round(c, 6) for c in cl_arr],
        best_glide=bg,
        min_sink=ms,
        inputs={
            "mass_kg": mass_kg,
            "s_ref_m2": s_ref_m2,
            "ar": ar,
            "e_oswald": e_oswald,
            "cd0": cd0,
            "rho": rho,
            "reynolds_mode": reynolds_mode,
            "cl_max": cl_max,
        },
    )


def _converge_special_point(
    cl_fn,
    cd0: float,
    e_oswald: float,
    ar: float,
    weight_n: float,
    rho: float,
    s_ref_m2: float,
    cd0_e_at,
) -> tuple[float, float, float, float]:
    """Solve a special-point CL (best-glide or min-sink) with one Picard pass.

    Returns ``(cl, v, cd0_at_v, k_at_v)``. With a fixed cd0/e (legacy mode)
    this reduces to the closed-form value in a single shot; with the Reynolds
    table it refines cd0/e at the converged speed exactly like the chips.
    """
    cd0_i, e_i = cd0, e_oswald
    cl = v = 0.0
    for _ in range(_PICARD_PASSES + 1):
        k = _induced_drag_factor(ar, e_i)
        cl = cl_fn(cd0_i, k)
        v = _velocity(weight_n, rho, s_ref_m2, cl)
        cd0_i, e_i = cd0_e_at(v)
    return cl, v, cd0_i, _induced_drag_factor(ar, e_i)


def is_missing(result: SpeedPolarResult | _MissingInputs) -> bool:
    """Return True when ``compute_speed_polar`` returned a _MissingInputs."""
    return isinstance(result, _MissingInputs)


# ---------------------------------------------------------------------------
# Pure math helpers (unit-testable in isolation)
# ---------------------------------------------------------------------------


def _check_inputs(
    *,
    mass_kg: float | None,
    s_ref_m2: float | None,
    ar: float | None,
    e_oswald: float | None,
    cd0: float | None,
) -> list[str]:
    """Return a list of missing/invalid input names (empty = all OK)."""
    missing: list[str] = []
    for name, val in [
        ("mass_kg", mass_kg),
        ("s_ref_m2", s_ref_m2),
        ("ar", ar),
        ("e_oswald", e_oswald),
        ("cd0", cd0),
    ]:
        if val is None or not math.isfinite(val) or val <= 0:
            missing.append(name)
    return missing


def _induced_drag_factor(ar: float, e_oswald: float) -> float:
    """k = 1 / (π · AR · e)."""
    return 1.0 / (math.pi * ar * e_oswald)


def _cl_best_glide(cd0: float, k: float) -> float:
    """CL at (L/D)_max = sqrt(CD0 / k)."""
    return math.sqrt(cd0 / k)


def _cl_min_sink(cd0: float, k: float) -> float:
    """CL at minimum sink = sqrt(3 · CD0 / k) = √3 · CL_bg."""
    return math.sqrt(3.0 * cd0 / k)


def _velocity(weight_n: float, rho: float, s_ref_m2: float, cl: float) -> float:
    """V = sqrt(2W / (ρ · S · CL)) [m/s]."""
    return math.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl))


def _sink_rate(v_mps: float, cd0: float, k: float, cl: float) -> float:
    """sink = V · CD / CL  (positive = downward) [m/s]."""
    cd = cd0 + k * cl**2
    return v_mps * cd / cl


def _linspace(start: float, stop: float, n: int) -> list[float]:
    """Uniform grid from start to stop with n points."""
    if n <= 1:
        return [start]
    step = (stop - start) / (n - 1)
    return [start + i * step for i in range(n)]
