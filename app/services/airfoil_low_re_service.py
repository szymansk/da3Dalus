"""Low-Re airfoil suitability scoring service (gh-821).

IMPORTANT DISTINCTION from polar_re_table_service (gh-493):
  - ``polar_re_table_service`` is *aircraft-level*: it re-bins fine aircraft
    sweep data into speed-band (V-band) Re labels at the main-wing MAC for a
    specific aircraft configuration.
  - This module is *2D per-airfoil*: polars are precomputed across an absolute
    Re grid (40k–750k) for each airfoil shape, independent of any aircraft.
    The two Re concepts are fundamentally different and must not be conflated.

Key responsibilities:
  1. ``classify_family``  — heuristic family label from coordinate geometry.
  2. ``compute_airfoil_low_re`` — NeuralFoil sweep + metric extraction + fit.
  3. ``_level_flight_cl`` — standalone CL helper (shared constant with
     endurance_service; G=9.80665, RHO=1.225).
  4. ``score_re_agnostic`` / ``score_mission`` / ``score_target_cl`` — three
     scoring lenses evaluated at query time (no precomputed scores stored).
  5. ``interpolate_polar_at_re`` — log-linear interpolation between grid points.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from app.schemas.airfoil import AirfoilFamily

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical constants (reuse values from endurance_service — keep in sync)
# ---------------------------------------------------------------------------
G = 9.80665  # m/s²
RHO = 1.225  # kg/m³  (ISA sea-level)

# Thresholds for family classifier
_SYMMETRIC_MAX_CAMBER_PCT = 0.5  # max_camber_pct below which → symmetric
_SEMI_SYMMETRIC_MAX_CAMBER_PCT = 2.0  # between SYMMETRIC and this → semi_symmetric
_FLAT_BOTTOM_Y_THRESHOLD = 0.002  # lower surface mean abs(y) below this → flat
_REFLEX_CAMBER_AT_TE_THRESHOLD = -0.003  # camber_at_te below this → reflexed


# ---------------------------------------------------------------------------
# Family classifier
# ---------------------------------------------------------------------------


def classify_family(coords: np.ndarray) -> AirfoilFamily:
    """Classify an airfoil into one of five family labels from its coordinates.

    Parameters
    ----------
    coords : np.ndarray, shape (N, 2)
        Closed contour as [x, y] pairs, conventional Selig order (TE→LE→TE
        or any complete closed loop). The contour must cover both surfaces.

    Returns
    -------
    str
        One of: 'flat_bottom', 'semi_symmetric', 'symmetric', 'cambered',
        'reflexed'.

    Algorithm
    ---------
    1. Split into upper / lower surfaces by finding the leading edge (min x).
    2. Compute camber line by interpolating both surfaces to common x stations.
    3. Evaluate:
       - reflex: camber_at_te (camber line at x≈1) strongly negative.
       - flat_bottom: mean |y_lower| < threshold (lower surface near y=0).
       - symmetric: max |camber| < threshold.
       - semi_symmetric: max |camber| < moderate threshold.
       - cambered: otherwise.

    NOTE: The existing ``_compute_geometry_stats`` in endpoints/airfoils.py
    returns max thickness/camber + their x-positions but does NOT extract
    ``camber_at_te`` or detect reflex. This function implements those separately
    from the mean camber line.
    """
    coords = np.asarray(coords, dtype=float)
    # Find LE (min x) to split surfaces
    le_idx = int(np.argmin(coords[:, 0]))

    # Split: assume coords go upper→LE→lower or TE→upper→LE→lower→TE
    # Strategy: sort all points by x, separate into upper (y >= camber) and lower
    # Use a different approach: find LE, split at LE
    n = len(coords)
    # Upper: one side of LE
    # Walk from LE in both directions to build upper and lower
    # Simpler: find all unique x-sorted points, compute mean camber
    upper_mask = np.zeros(n, dtype=bool)
    lower_mask = np.zeros(n, dtype=bool)

    # Approach: use the two sides by splitting at LE index
    # Segment 1: coords[0:le_idx+1]  (or reversed: TE->LE)
    # Segment 2: coords[le_idx:]     (LE->TE)
    seg_a = coords[: le_idx + 1]  # index 0..le_idx
    seg_b = coords[le_idx:]  # index le_idx..end

    # Both segments go from or to LE. Orient them LE→TE for interpolation.
    # seg_a: if x is descending (TE→LE), reverse it → LE→TE
    if len(seg_a) > 1 and seg_a[0, 0] > seg_a[-1, 0]:
        seg_a = seg_a[::-1]
    # seg_b: should be LE→TE (x ascending)
    if len(seg_b) > 1 and seg_b[0, 0] > seg_b[-1, 0]:
        seg_b = seg_b[::-1]

    # Assign upper vs lower by which has higher y at mid-chord
    x_ref = 0.3
    y_a = np.interp(x_ref, np.sort(seg_a[:, 0]), seg_a[np.argsort(seg_a[:, 0]), 1])
    y_b = np.interp(x_ref, np.sort(seg_b[:, 0]), seg_b[np.argsort(seg_b[:, 0]), 1])

    if y_a >= y_b:
        upper, lower = seg_a, seg_b
    else:
        upper, lower = seg_b, seg_a

    # Sort both surfaces by x for interpolation
    upper_s = upper[np.argsort(upper[:, 0])]
    lower_s = lower[np.argsort(lower[:, 0])]

    x_min = max(upper_s[0, 0], lower_s[0, 0])
    x_max = min(upper_s[-1, 0], lower_s[-1, 0])
    x_eval = np.linspace(x_min, x_max, 200)

    y_upper = np.interp(x_eval, upper_s[:, 0], upper_s[:, 1])
    y_lower = np.interp(x_eval, lower_s[:, 0], lower_s[:, 1])
    camber = (y_upper + y_lower) / 2.0

    max_camber = float(np.max(camber))
    max_camber_pct = max_camber * 100.0  # as % of chord (coords normalized 0..1)

    # camber_at_te: evaluate camber line at x=max(x_eval) which is near TE
    camber_at_te = float(camber[-1])

    # Lower surface mean abs y (flat-bottom detection)
    mean_lower_abs_y = float(np.mean(np.abs(y_lower)))

    # --- Classification rules (ordered by priority) ---
    # 1. Reflexed: camber line is clearly negative (below chord) at TE
    if camber_at_te < _REFLEX_CAMBER_AT_TE_THRESHOLD:
        return "reflexed"

    # 2. Flat-bottom: lower surface is essentially flat (y ≈ 0)
    if mean_lower_abs_y < _FLAT_BOTTOM_Y_THRESHOLD:
        return "flat_bottom"

    # 3. Symmetric: almost no camber
    if max_camber_pct < _SYMMETRIC_MAX_CAMBER_PCT:
        return "symmetric"

    # 4. Semi-symmetric: small camber
    if max_camber_pct < _SEMI_SYMMETRIC_MAX_CAMBER_PCT:
        return "semi_symmetric"

    # 5. Cambered: everything else
    return "cambered"


# ---------------------------------------------------------------------------
# Reynolds interpolation
# ---------------------------------------------------------------------------


def interpolate_polar_at_re(
    polar_rows: list,
    re_query: float,
    re_grid: list[int],
) -> dict | None:
    """Interpolate (or clamp) polar metrics to the query Re.

    Interpolation is linear in ln(Re), matching NeuralFoil's training encoding.

    Parameters
    ----------
    polar_rows : list[AirfoilLowRePolarModel]
        All persisted rows for one airfoil, any order.
    re_query : float
        Query Reynolds number (already clamped to grid if needed).
    re_grid : list[int]
        The absolute Re grid (from settings).

    Returns
    -------
    dict | None
        Interpolated scalar metrics, or None if no rows available.
    """
    if not polar_rows:
        return None

    rows_by_re = {float(r.reynolds): r for r in polar_rows}
    available_re = sorted(rows_by_re.keys())

    if not available_re:
        return None

    # Exact match
    if re_query in rows_by_re:
        r = rows_by_re[re_query]
        return _row_to_dict(r)

    # Find bounding grid points
    lo = max((re for re in available_re if re <= re_query), default=None)
    hi = min((re for re in available_re if re >= re_query), default=None)

    if lo is None:
        return _row_to_dict(rows_by_re[available_re[0]])
    if hi is None:
        return _row_to_dict(rows_by_re[available_re[-1]])

    # Linear in ln(Re)
    t = (math.log(re_query) - math.log(lo)) / (math.log(hi) - math.log(lo))
    r_lo = rows_by_re[lo]
    r_hi = rows_by_re[hi]
    return _interpolate_rows(r_lo, r_hi, t)


def _row_to_dict(row: Any) -> dict:
    return {
        "ld_max": row.ld_max,
        "cl_max": row.cl_max,
        "alpha_attached_lo": row.alpha_attached_lo,
        "alpha_attached_hi": row.alpha_attached_hi,
        "drag_bucket_width": row.drag_bucket_width,
        "cd_min": row.cd_min,
        "stall_gentleness": row.stall_gentleness,
        "cd0": row.cd0,
        "k": row.k,
        "cl0": row.cl0,
        "cl_valid_lo": row.cl_valid_lo,
        "cl_valid_hi": row.cl_valid_hi,
        "min_analysis_confidence": row.min_analysis_confidence,
    }


def _lerp(a: Any, b: Any, t: float) -> Any:
    if a is None or b is None:
        return a if b is None else b
    return a + t * (b - a)


def _interpolate_rows(r_lo: Any, r_hi: Any, t: float) -> dict:
    return {
        "ld_max": _lerp(r_lo.ld_max, r_hi.ld_max, t),
        "cl_max": _lerp(r_lo.cl_max, r_hi.cl_max, t),
        "alpha_attached_lo": _lerp(r_lo.alpha_attached_lo, r_hi.alpha_attached_lo, t),
        "alpha_attached_hi": _lerp(r_lo.alpha_attached_hi, r_hi.alpha_attached_hi, t),
        "drag_bucket_width": _lerp(r_lo.drag_bucket_width, r_hi.drag_bucket_width, t),
        "cd_min": _lerp(r_lo.cd_min, r_hi.cd_min, t),
        "stall_gentleness": _lerp(r_lo.stall_gentleness, r_hi.stall_gentleness, t),
        "cd0": _lerp(r_lo.cd0, r_hi.cd0, t),
        "k": _lerp(r_lo.k, r_hi.k, t),
        "cl0": _lerp(r_lo.cl0, r_hi.cl0, t),
        "cl_valid_lo": _lerp(r_lo.cl_valid_lo, r_hi.cl_valid_lo, t),
        "cl_valid_hi": _lerp(r_lo.cl_valid_hi, r_hi.cl_valid_hi, t),
        "min_analysis_confidence": _lerp(
            r_lo.min_analysis_confidence, r_hi.min_analysis_confidence, t
        ),
    }


# ---------------------------------------------------------------------------
# NeuralFoil compute (import-guarded for linux/aarch64)
# ---------------------------------------------------------------------------


def compute_airfoil_low_re(
    name: str,
    coords: np.ndarray,
    re_grid: list[int],
    *,
    model_size: str = "xxxlarge",
    n_crit: float = 9.0,
    confidence_gate: float = 0.90,
    alpha_start: float = -5.0,
    alpha_end: float = 18.0,
    alpha_step: float = 0.2,
) -> list[dict]:
    """Run NeuralFoil on `coords` across each Re in `re_grid` and return metrics.

    Parameters
    ----------
    name : str
        Airfoil name (for NeuralFoil identification).
    coords : np.ndarray, shape (N, 2)
        Closed contour coordinates (Selig format, normalised 0..1).
    re_grid : list[int]
        Absolute Re grid points to evaluate.
    model_size : str
        NeuralFoil model size. Default 'xxxlarge' for the backfill;
        the interactive endpoint at endpoints/airfoils.py:111 uses 'large'.
        These defaults are intentionally different — do NOT collapse.
    n_crit : float
        Transition criterion (e^N method).
    confidence_gate : float
        Minimum analysis_confidence to include an alpha in metric extraction.
    alpha_start, alpha_end, alpha_step : float
        α sweep bounds in degrees.

    Returns
    -------
    list[dict]
        One dict per Re-grid point with scalar metrics + fit coefficients.
        May be empty if AeroSandbox is not available on this platform.
    """
    try:
        import aerosandbox as asb
    except ImportError:
        logger.warning("AeroSandbox not available — skipping NeuralFoil compute for %s", name)
        return []

    alpha_deg = np.arange(alpha_start, alpha_end + alpha_step * 0.5, alpha_step)
    airfoil = asb.Airfoil(name=name, coordinates=coords)
    results: list[dict] = []

    for re in re_grid:
        raw = airfoil.get_aero_from_neuralfoil(
            alpha=alpha_deg,
            Re=float(re),
            mach=0.0,
            n_crit=float(n_crit),
            model_size=model_size,
        )

        cl_arr = np.atleast_1d(np.asarray(raw.get("CL", np.nan), dtype=float))
        cd_arr = np.atleast_1d(np.asarray(raw.get("CD", np.nan), dtype=float))
        conf_arr = np.atleast_1d(np.asarray(raw.get("analysis_confidence", np.nan), dtype=float))

        # Broadcast scalar confidence
        if conf_arr.size == 1:
            conf_arr = np.full_like(cl_arr, float(conf_arr[0]))

        min_confidence = float(np.nanmin(conf_arr)) if np.any(np.isfinite(conf_arr)) else 0.0

        # Gate: only use alpha points with confidence >= gate
        trusted = conf_arr >= confidence_gate
        cl_trusted = cl_arr[trusted] if trusted.any() else np.array([])
        cd_trusted = cd_arr[trusted] if trusted.any() else np.array([])
        alpha_trusted = alpha_deg[trusted] if trusted.any() else np.array([])

        row = _extract_metrics(
            cl_trusted,
            cd_trusted,
            alpha_trusted,
            min_confidence,
            re,
            model_size=model_size,
            n_crit=n_crit,
        )
        results.append(row)

    return results


def _extract_metrics(
    cl: np.ndarray,
    cd: np.ndarray,
    alpha: np.ndarray,
    min_confidence: float,
    reynolds: float,
    *,
    model_size: str,
    n_crit: float,
) -> dict:
    """Extract scalar metrics from trusted CL/CD/alpha arrays."""
    from datetime import datetime, timezone

    result: dict = {
        "reynolds": reynolds,
        "ld_max": None,
        "cl_max": None,
        "alpha_attached_lo": None,
        "alpha_attached_hi": None,
        "drag_bucket_width": None,
        "cd_min": None,
        "stall_gentleness": None,
        "cd0": None,
        "k": None,
        "cl0": None,
        "cl_valid_lo": None,
        "cl_valid_hi": None,
        "min_analysis_confidence": min_confidence,
        "neuralfoil_model_size": model_size,
        "n_crit": n_crit,
        "computed_at": datetime.now(timezone.utc),
    }

    if len(cl) < 4 or len(cd) < 4:
        return result

    finite_mask = np.isfinite(cl) & np.isfinite(cd)
    cl_f = cl[finite_mask]
    cd_f = cd[finite_mask]
    alpha_f = alpha[finite_mask]

    if len(cl_f) < 4:
        return result

    # CL_max
    idx_max = int(np.argmax(cl_f))
    cl_max = float(cl_f[idx_max])
    result["cl_max"] = cl_max

    # Stall gentleness: dCL/dα just past the CL_max peak
    # Use linear fit over the 3 points after peak
    if idx_max + 3 < len(cl_f):
        post_cl = cl_f[idx_max : idx_max + 4]
        post_alpha = alpha_f[idx_max : idx_max + 4]
        coeffs = np.polyfit(post_alpha, post_cl, 1)
        result["stall_gentleness"] = float(coeffs[0])

    # CD_min
    idx_cd_min = int(np.argmin(cd_f))
    cd_min = float(cd_f[idx_cd_min])
    result["cd_min"] = cd_min

    # L/D max
    with np.errstate(divide="ignore", invalid="ignore"):
        ld = np.where(cd_f > 1e-12, cl_f / cd_f, np.nan)
    if np.any(np.isfinite(ld)):
        result["ld_max"] = float(np.nanmax(ld))

    # Drag bucket width: ΔCL where CD ≤ 1.15 * CD_min
    cd_threshold = 1.15 * cd_min
    bucket_mask = cd_f <= cd_threshold
    if bucket_mask.any():
        bucket_cl = cl_f[bucket_mask]
        result["drag_bucket_width"] = float(np.max(bucket_cl) - np.min(bucket_cl))

    # Attached-flow α window: where CL is finite and below stall
    # Use the ascending part of the CL curve up to CL_max
    attached = cl_f[: idx_max + 1]
    attached_alpha = alpha_f[: idx_max + 1]
    if len(attached_alpha) >= 2:
        result["alpha_attached_lo"] = float(attached_alpha[0])
        result["alpha_attached_hi"] = float(attached_alpha[-1])

    # Parabolic drag polar fit: CD = cd0 + k * (CL - cl0)^2
    # OLS pattern reused from assumption_compute_service._fit_parabolic_polar
    # NOTE: the existing service fits CD = cd0 + CL^2/(π*e*AR) — AR-coupled,
    # no cl0 offset. Here we fit the airfoil-level cl0 offset independently.
    if len(cl_f) >= 5:
        try:
            # Fit: CD = cd0 + k*(CL - cl0)^2 = (cd0 + k*cl0^2) - 2k*cl0*CL + k*CL^2
            # Let p = [k, -2k*cl0, cd0+k*cl0^2] → polyfit(CL, CD, 2)
            p = np.polyfit(cl_f, cd_f, 2)
            k_fit = float(p[0])
            b_fit = float(p[1])
            c_fit = float(p[2])
            if k_fit > 0:
                cl0_fit = -b_fit / (2.0 * k_fit)
                cd0_fit = c_fit - k_fit * cl0_fit**2
                if cd0_fit > 0:
                    result["cd0"] = cd0_fit
                    result["k"] = k_fit
                    result["cl0"] = cl0_fit
                    # Validity range: CL where parabolic fit error is acceptable
                    # Use the entire range with trusted data as validity range
                    result["cl_valid_lo"] = float(np.min(cl_f))
                    result["cl_valid_hi"] = float(np.max(cl_f))
        except (np.linalg.LinAlgError, ValueError):
            pass

    return result


# ---------------------------------------------------------------------------
# Standalone _level_flight_cl helper
# ---------------------------------------------------------------------------


def _level_flight_cl(mass_kg: float, v_ms: float, s_ref_m2: float) -> float:
    """Compute the level-flight lift coefficient.

    CL = (m·g) / (0.5·ρ·V²·S)

    Uses the same G and RHO constants as endurance_service (G=9.80665,
    RHO=1.225 kg/m³ ISA sea-level) — keep in sync.

    Parameters
    ----------
    mass_kg : float   Aircraft mass [kg]
    v_ms    : float   True airspeed [m/s]
    s_ref_m2 : float  Wing reference area [m²]

    Returns
    -------
    float   Level-flight lift coefficient (dimensionless)
    """
    if v_ms <= 0 or s_ref_m2 <= 0:
        raise ValueError(f"v_ms and s_ref_m2 must be positive; got {v_ms=}, {s_ref_m2=}")
    q = 0.5 * RHO * v_ms**2
    return (mass_kg * G) / (q * s_ref_m2)


# ---------------------------------------------------------------------------
# Three scoring lenses
# ---------------------------------------------------------------------------


def score_re_agnostic(polar: dict) -> float | None:
    """Compute the re_agnostic suitability score (0..1) from interpolated metrics.

    Higher is better. Returns None if insufficient data.

    Formula: weighted sum of normalised scalar metrics:
      - ld_max_norm:          0.35 weight
      - cl_max_norm:          0.25 weight
      - drag_bucket_width:    0.20 weight
      - stall_gentleness:     0.10 weight (gentle = score bonus)
      - cd_min_inv:           0.10 weight (lower CD = better)

    All components normalised to [0..1] using soft reference values.
    """
    if polar is None:
        return None

    ld_max = polar.get("ld_max")
    cl_max = polar.get("cl_max")
    bucket = polar.get("drag_bucket_width")
    stall = polar.get("stall_gentleness")
    cd_min = polar.get("cd_min")

    # Soft reference (typical good low-Re values)
    LD_REF = 60.0  # excellent L/D at low Re
    CL_MAX_REF = 1.5
    BUCKET_REF = 0.8  # wide drag bucket
    CD_MIN_REF = 0.008  # low CD_min

    components: list[tuple[float, float]] = []

    if ld_max is not None and ld_max > 0:
        components.append((min(ld_max / LD_REF, 1.0), 0.35))

    if cl_max is not None and cl_max > 0:
        components.append((min(cl_max / CL_MAX_REF, 1.0), 0.25))

    if bucket is not None and bucket >= 0:
        components.append((min(bucket / BUCKET_REF, 1.0), 0.20))

    if stall is not None:
        # stall_gentleness is dCL/dα past peak; close to 0 → gentle (good)
        # very negative → abrupt stall (bad)
        # Map: 0 → 1.0, ≤ -0.15 → 0.0 (linear)
        gentleness_score = max(0.0, min(1.0, 1.0 + stall / 0.15))
        components.append((gentleness_score, 0.10))

    if cd_min is not None and cd_min > 0:
        # Lower cd_min → better; reference CD_MIN_REF maps to 1.0
        cd_score = min(CD_MIN_REF / cd_min, 1.0)
        components.append((cd_score, 0.10))

    if not components:
        return None

    total_weight = sum(w for _, w in components)
    if total_weight <= 0:
        return None

    score = sum(v * w for v, w in components) / total_weight
    return float(min(max(score, 0.0), 1.0))


def score_mission(
    re_agnostic: float | None,
    family: str,
    max_thickness_pct: float | None,
    cl_max: float | None,
    mission_type: str,
    mission_weights: dict,
) -> float | None:
    """Compute mission-weighted suitability score.

    score_mission = re_agnostic * family_bonus * thickness_match * cl_max_bonus

    All multipliers are clipped to [0..1] so the result stays in [0..1].
    """
    if re_agnostic is None or mission_type not in mission_weights:
        return None

    weights = mission_weights[mission_type]
    preferred_families = weights.get("preferred_families", [])
    t_min = weights.get("thickness_min_pct", 0.0)
    t_max = weights.get("thickness_max_pct", 100.0)
    cl_max_weight = weights.get("cl_max_weight", 0.5)

    # Family bonus: 1.0 if preferred, 0.7 if not
    family_bonus = 1.0 if family in preferred_families else 0.7

    # Thickness match: 1.0 if in band, linearly degraded outside
    thickness_match = 1.0
    if max_thickness_pct is not None:
        if t_min <= max_thickness_pct <= t_max:
            thickness_match = 1.0
        elif max_thickness_pct < t_min:
            gap = t_min - max_thickness_pct
            thickness_match = max(0.0, 1.0 - gap / 5.0)
        else:
            gap = max_thickness_pct - t_max
            thickness_match = max(0.0, 1.0 - gap / 5.0)

    # CL_max bonus (scaled by cl_max_weight; CL_max=1.5 → full bonus)
    cl_bonus = 1.0
    if cl_max is not None:
        cl_norm = min(cl_max / 1.5, 1.0)
        # Weighted interpolation: (1-weight) * 1.0 + weight * cl_norm
        cl_bonus = (1.0 - cl_max_weight) + cl_max_weight * cl_norm

    mission_score = re_agnostic * family_bonus * thickness_match * cl_bonus
    return float(min(max(mission_score, 0.0), 1.0))


def score_target_cl(
    polar: dict,
    cl_target: float,
) -> float | None:
    """Score how well an airfoil performs at the target CL (0..1).

    Uses the parabolic drag fit CD = cd0 + k*(CL-cl0)^2 to compute the L/D
    at the target operating point, then normalises against reference L/D values.

    Scoring is based on L/D (= cl_target / cd_at_target) rather than absolute
    CD.  Absolute-CD normalisation breaks at high-CL operating points (glider
    min-sink CL ≈ 1.2–1.8) where even excellent airfoils have CD > 0.05,
    producing a spurious 0.0 score for the entire glider min-sink column.

    Reference values (RC sailplane / glider range):
      L/D ≥ 30 at target CL  → score 1.0   (excellent high-lift section)
      L/D ≤  8 at target CL  → score 0.0   (poor)

    Returns None if fit coefficients are absent.
    Higher score = better aerodynamic efficiency at cl_target.
    """
    if polar is None:
        return None

    cd0 = polar.get("cd0")
    k = polar.get("k")
    cl0 = polar.get("cl0")
    cl_lo = polar.get("cl_valid_lo")
    cl_hi = polar.get("cl_valid_hi")

    if any(v is None for v in (cd0, k, cl0)):
        return None

    # Check if cl_target is within the valid fit range
    in_range = True
    if cl_lo is not None and cl_hi is not None:
        if cl_target < cl_lo or cl_target > cl_hi:
            in_range = False

    cd_at_target = cd0 + k * (cl_target - cl0) ** 2

    if cd_at_target <= 0:
        return 0.0

    # Score on L/D — CL-independent, works at any operating point
    ld_at_target = abs(cl_target) / cd_at_target

    LD_REF_EXCELLENT = 30.0
    LD_REF_POOR = 8.0

    ld_score = (ld_at_target - LD_REF_POOR) / (LD_REF_EXCELLENT - LD_REF_POOR)
    ld_score = max(0.0, min(ld_score, 1.0))

    # Penalise if outside valid range
    if not in_range:
        ld_score *= 0.5

    return float(ld_score)
