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
from typing import NamedTuple

# ISA sea-level constants
_G = 9.80665  # m/s²
_RHO_ISA_SL = 1.225  # kg/m³

# Speed-polar sweep: CL from CL_ms·1.4 down to CL_min_sweep
_CL_SWEEP_POINTS = 200
_CL_MIN_RATIO = 0.25  # fraction of CL_bg — stops before stall region


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
    e_oswald : Oswald efficiency factor (dimensionless, 0 < e ≤ 1)
    cd0 : zero-lift drag coefficient (dimensionless, > 0)
    rho : air density [kg/m³], default ISA sea-level 1.225
    """
    missing = _check_inputs(mass_kg=mass_kg, s_ref_m2=s_ref_m2, ar=ar, e_oswald=e_oswald, cd0=cd0)
    if missing:
        return _MissingInputs(missing=missing)

    # All inputs validated — narrow types
    assert mass_kg is not None and s_ref_m2 is not None
    assert ar is not None and e_oswald is not None and cd0 is not None

    weight_n = mass_kg * _G
    k = _induced_drag_factor(ar, e_oswald)

    # Special CL values
    cl_bg = _cl_best_glide(cd0, k)
    cl_ms = _cl_min_sink(cd0, k)

    # Sweep CL from slightly above CL_ms down to a low-speed stop
    cl_high = cl_ms * 1.40
    cl_low = cl_bg * _CL_MIN_RATIO  # well below best glide, not useful to plot further
    # Build grid of CL values (descending → ascending V for the plot)
    cl_arr = _linspace(cl_high, cl_low, _CL_SWEEP_POINTS)

    v_arr: list[float] = []
    sink_arr: list[float] = []
    for cl in cl_arr:
        v = _velocity(weight_n, rho, s_ref_m2, cl)
        sink = _sink_rate(v, cd0, k, cl)
        v_arr.append(round(v, 4))
        sink_arr.append(round(sink, 5))

    # Best-glide and min-sink points
    bg = SpeedPolarPoint(
        v_mps=round(_velocity(weight_n, rho, s_ref_m2, cl_bg), 4),
        sink_mps=round(_sink_rate(_velocity(weight_n, rho, s_ref_m2, cl_bg), cd0, k, cl_bg), 5),
        cl=round(cl_bg, 6),
    )
    ms = SpeedPolarPoint(
        v_mps=round(_velocity(weight_n, rho, s_ref_m2, cl_ms), 4),
        sink_mps=round(_sink_rate(_velocity(weight_n, rho, s_ref_m2, cl_ms), cd0, k, cl_ms), 5),
        cl=round(cl_ms, 6),
    )

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
        },
    )


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
