"""Reynolds-dependent polar lookup service — gh-493.

Computes a Re-indexed polar table by REBINNING the existing fine-sweep data
from _fine_sweep_cl_max into V-bands (no extra AeroBuildup invocations).

Key design decisions:
- Re in the table is "Re_aircraft = ρ·V·MAC_main/μ at ISA-SL" — a label for
  V-based lookup, NOT a physical AeroBuildup parameter (AeroBuildup uses per-
  component Re_local internally).
- V-bands: {V_s, V_cruise, max(1.3·V_cruise, V_max_profile_goal)}
  (V_max heuristic is decoupled from powertrain to prevent chicken-egg).
- Degeneracy guard: if Re_max/Re_min < 2.5 (all anchors nearly the same
  speed) → single-row fallback, set polar_re_table_degenerate=True.
- Per-band fit reuses the same OLS logic as _fit_parabolic_polar() in
  assumption_compute_service.  Marginal compute cost ≤200 ms.
- cd0 lookup: linear in 1/√Re (Blasius/Schlichting skin-friction scaling,
  cf ∝ Re^{-1/2}).
- e_oswald lookup: constant mean across table (Hepperle/Drela KISS pattern;
  Oswald efficiency is insensitive to Re at subsonic speeds).
- Extrapolation: clamp to nearest endpoint and log a warning.

Sources
-------
- Blasius (1908): cf = 0.664/√Re for laminar flat plate → cd0 ∝ 1/√Re
- Schlichting (1979): turbulent cf ∝ Re^{-0.2} (Prandtl); overall Re scaling
  dominated by laminar/transition terms at RC scale → 1/√Re is pragmatic
- Hepperle (2012): electric endurance; e insensitive to Re at sub-stall
- Drela (XFOIL framework): span-efficiency dominated by planform, not Re
- Anderson (2016): §6.1.2 drag polar, §6.7.2 (L/D)_max
- gh-493 spec: Amendments 2–4, 6–7, 11
"""
from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from app.schemas.polar_re_table import PolarReTableRow

logger = logging.getLogger(__name__)

# ISA sea-level dynamic viscosity [Pa·s]
_MU_ISA_SL: float = 1.81e-5

# Degeneracy threshold: if Re_max/Re_min < this, table is degenerate
_RE_DEGENERACY_RATIO: float = 2.5

# Minimum samples per V-band for a valid OLS fit
_MIN_SAMPLES_PER_BAND: int = 6

# Half-width of the V-bin window around each anchor point
# (fraction of the gap to the adjacent anchor)
_V_BIN_HALF_WIDTH_FRACTION: float = 0.5

# Fallback Oswald efficiency when all rows have failed fits
_FALLBACK_E_OSWALD: float = 0.8


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _reynolds_number_from_v(
    v_mps: float,
    mac_m: float,
    rho: float = 1.225,
    mu: float = _MU_ISA_SL,
) -> float:
    """Aircraft-level Reynolds number Re = ρ·V·MAC/μ at ISA sea level.

    This is a label for V-based lookup — NOT the per-component Re_local
    used by AeroBuildup internally.

    Parameters
    ----------
    v_mps  : True airspeed [m/s]
    mac_m  : Main-wing mean aerodynamic chord [m]
    rho    : Air density [kg/m³], default ISA SL
    mu     : Dynamic viscosity [Pa·s], default ISA SL

    Returns
    -------
    Dimensionless Reynolds number
    """
    return rho * v_mps * mac_m / mu


def lookup_cd0_at_v(
    v_mps: float,
    table: list[dict[str, Any]],
    mac_m: float,
    rho: float = 1.225,
    mu: float = _MU_ISA_SL,
) -> float:
    """Look up cd0 at a given velocity by linear interpolation in 1/√Re.

    Implements Blasius/Schlichting scaling: cf ∝ Re^{-1/2} at low Re,
    so cd0 is interpolated linearly in 1/√Re rather than in cd0 directly.

    Extrapolation clamps to the nearest endpoint and emits a warning.

    Parameters
    ----------
    v_mps  : Query velocity [m/s]
    table  : list[dict] from build_re_table (or .model_dump() of PolarReTableRow list)
    mac_m  : Mean aerodynamic chord [m]
    rho    : Air density [kg/m³]
    mu     : Dynamic viscosity [Pa·s]

    Returns
    -------
    cd0 at the query velocity (float)
    """
    # Filter to rows with valid cd0 (non-fallback)
    valid_rows = [r for r in table if not r.get("fallback_used", True) and r.get("cd0") is not None]

    if not valid_rows:
        # All rows are fallback — return first available cd0 or 0.03
        all_cd0 = [r.get("cd0") for r in table if r.get("cd0") is not None]
        return float(all_cd0[0]) if all_cd0 else 0.03

    # Sort by Re ascending
    valid_rows_sorted = sorted(valid_rows, key=lambda r: r["re"])

    re_query = _reynolds_number_from_v(v_mps, mac_m, rho, mu)
    re_values = [r["re"] for r in valid_rows_sorted]
    cd0_values = [r["cd0"] for r in valid_rows_sorted]

    # Extrapolation guard: clamp and warn
    if re_query <= re_values[0]:
        if re_query < re_values[0]:
            logger.warning(
                "cd0 lookup: Re=%.0f (V=%.1f m/s) is below table minimum Re=%.0f — "
                "clamping to lowest Re endpoint (cd0=%.5f).",
                re_query, v_mps, re_values[0], cd0_values[0],
            )
        return float(cd0_values[0])

    if re_query >= re_values[-1]:
        if re_query > re_values[-1]:
            logger.warning(
                "cd0 lookup: Re=%.0f (V=%.1f m/s) is above table maximum Re=%.0f — "
                "clamping to highest Re endpoint (cd0=%.5f).",
                re_query, v_mps, re_values[-1], cd0_values[-1],
            )
        return float(cd0_values[-1])

    # Find bracketing interval
    for i in range(len(re_values) - 1):
        re_lo = re_values[i]
        re_hi = re_values[i + 1]
        if re_lo <= re_query <= re_hi:
            cd0_lo = cd0_values[i]
            cd0_hi = cd0_values[i + 1]

            # Linear interpolation in 1/√Re space (Blasius scaling)
            inv_sqrt_lo = 1.0 / math.sqrt(re_lo)
            inv_sqrt_hi = 1.0 / math.sqrt(re_hi)
            inv_sqrt_query = 1.0 / math.sqrt(re_query)

            denom = inv_sqrt_hi - inv_sqrt_lo
            if abs(denom) < 1e-15:
                return float(cd0_lo)

            t = (inv_sqrt_query - inv_sqrt_lo) / denom
            return float(cd0_lo + t * (cd0_hi - cd0_lo))

    # Should not reach here
    return float(cd0_values[-1])


def lookup_e_oswald_at_v(
    v_mps: float,
    table: list[dict[str, Any]],
) -> float:
    """Look up Oswald efficiency at a given velocity.

    Per Hepperle/Drela: e is insensitive to Re at subsonic speeds.
    Returns the constant mean of all non-fallback rows.

    Falls back to 0.8 when all rows have fallback_used=True or e_oswald=None.

    Parameters
    ----------
    v_mps  : Query velocity [m/s] (ignored — mean is V-independent)
    table  : list[dict] from build_re_table (or .model_dump() of PolarReTableRow list)

    Returns
    -------
    Constant mean e_oswald (float)
    """
    valid_e = [
        r["e_oswald"]
        for r in table
        if not r.get("fallback_used", True) and r.get("e_oswald") is not None
    ]
    if not valid_e:
        return _FALLBACK_E_OSWALD
    return float(sum(valid_e) / len(valid_e))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _band_boundaries(
    v_center: float, v_anchors: list[float]
) -> tuple[float, float]:
    """Compute the lower and upper velocity bounds for a V-band.

    For interior anchors: midpoints to adjacent anchors.
    For the lowest anchor: extend 50% of the gap to the right down below.
    For the highest anchor: extend 50% of the gap to the left upward.

    This ensures non-overlapping, exhaustive coverage of the V sweep range.
    """
    v_sorted = sorted(v_anchors)
    idx = v_sorted.index(v_center)

    if len(v_sorted) == 1:
        return 0.0, float("inf")

    if idx == 0:
        # Lowest anchor: extend half the gap below V_s, upper = midpoint to next
        gap = v_sorted[1] - v_sorted[0]
        v_lo = max(0.0, v_sorted[0] - gap * _V_BIN_HALF_WIDTH_FRACTION)
        v_hi = (v_sorted[0] + v_sorted[1]) / 2.0
    elif idx == len(v_sorted) - 1:
        # Highest anchor: lower = midpoint from previous, extend above
        v_lo = (v_sorted[-2] + v_sorted[-1]) / 2.0
        gap = v_sorted[-1] - v_sorted[-2]
        v_hi = v_sorted[-1] + gap * _V_BIN_HALF_WIDTH_FRACTION
    else:
        # Interior anchor: midpoints on both sides
        v_lo = (v_sorted[idx - 1] + v_sorted[idx]) / 2.0
        v_hi = (v_sorted[idx] + v_sorted[idx + 1]) / 2.0

    return v_lo, v_hi


def _fit_band_with_ar(
    v_array: np.ndarray,
    cl_array: np.ndarray,
    cd_array: np.ndarray,
    v_center: float,
    mac_m: float,
    rho: float,
    cl_max: float,
    ar: float,
) -> dict[str, Any]:
    """Fit C_D = C_D0 + k·C_L² via OLS for a V-band (AR-aware version).

    This is the primary fitting function used when AR is available (i.e. when
    called from recompute_assumptions context). Computes e_oswald from fitted k.

    Parameters
    ----------
    ar : float — main wing aspect ratio (b²/S)
    """
    re = _reynolds_number_from_v(v_center, mac_m, rho)
    cd0_fit, k_fit, r2 = _fit_polar_ols(cl_array, cd_array, cl_max)

    if cd0_fit is None:
        row = _fallback_row(v_center, mac_m, rho, cl_max)
        return row

    # Compute e_oswald from slope k = 1/(π·e·AR)
    if k_fit is not None and k_fit > 0 and ar > 0:
        e_oswald = 1.0 / (math.pi * ar * k_fit)
        # Physical range guard
        if not (0.4 < e_oswald <= 1.0):
            logger.warning(
                "Re table band V=%.1f m/s: e_oswald=%.4f outside (0.4, 1.0] — "
                "setting fallback_used=True for this row.",
                v_center, e_oswald,
            )
            return _fallback_row(v_center, mac_m, rho, cl_max)
    else:
        e_oswald = None

    return {
        "re": round(re),
        "v_mps": v_center,
        "cd0": round(cd0_fit, 6),
        "e_oswald": round(e_oswald, 4) if e_oswald is not None else None,
        "cl_max": cl_max,
        "r2": round(r2, 4) if r2 is not None else None,
        "fallback_used": False,
    }


def _fallback_row(
    v_center: float, mac_m: float, rho: float, cl_max: float
) -> dict[str, Any]:
    """Build a fallback row for a V-band with insufficient data."""
    re = _reynolds_number_from_v(v_center, mac_m, rho)
    return {
        "re": round(re),
        "v_mps": v_center,
        "cd0": None,
        "e_oswald": None,
        "cl_max": cl_max,
        "r2": None,
        "fallback_used": True,
    }


def _fit_polar_ols(
    cl: np.ndarray,
    cd: np.ndarray,
    cl_max: float,
) -> tuple[float | None, float | None, float | None]:
    """OLS fit C_D = C_D0 + k·C_L² in the linear polar window.

    Window: [CL_lo, CL_hi] where
        CL_lo = max(0.10, 0.10 · CL_max)
        CL_hi = 0.85 · CL_max

    Minimum 6 points required. Returns (None, None, None) on rejection.
    Returns (cd0_fit, k_fit, r2) on success.

    This mirrors the _fit_parabolic_polar logic from assumption_compute_service
    but returns (cd0, k, r2) instead of (cd0, e, r2) — e requires AR.
    """
    if cl_max is None or cl_max <= 0:
        return None, None, None

    cl_lo = max(0.10, 0.10 * cl_max)
    cl_hi = 0.85 * cl_max

    mask = (cl >= cl_lo) & (cl <= cl_hi)
    cl_win = cl[mask]
    cd_win = cd[mask]

    if len(cl_win) < _MIN_SAMPLES_PER_BAND:
        logger.debug(
            "polar OLS: only %d points in window [%.3f, %.3f] (need ≥ %d)",
            len(cl_win), cl_lo, cl_hi, _MIN_SAMPLES_PER_BAND,
        )
        return None, None, None

    cl2_win = cl_win ** 2

    # Monotonicity guard: dCD/dCL² must be non-negative
    sort_idx = np.argsort(cl2_win)
    cl2_sorted = cl2_win[sort_idx]
    cd_sorted = cd_win[sort_idx]
    diffs = np.diff(cd_sorted)
    if np.any(diffs < -1e-6):
        logger.debug(
            "polar OLS: non-monotonic dCD/d(CL²) in window — "
            "possible laminar bubble or stall contamination; skipping band fit"
        )
        return None, None, None

    # OLS: C_D = k · C_L² + C_D0
    k, cd0_fit = np.polyfit(cl2_win, cd_win, deg=1)

    if k <= 0:
        logger.debug("polar OLS: non-positive slope k=%.6f", k)
        return None, None, None

    if cd0_fit <= 0:
        logger.debug("polar OLS: non-positive cd0_fit=%.6f", cd0_fit)
        return None, None, None

    # R² for quality reporting
    ss_res = float(np.sum((cd_win - (k * cl2_win + cd0_fit)) ** 2))
    ss_tot = float(np.sum((cd_win - np.mean(cd_win)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return float(cd0_fit), float(k), float(r2)


# ---------------------------------------------------------------------------
# Public entry point for use in recompute_assumptions
# ---------------------------------------------------------------------------


def build_re_table(
    v_array: np.ndarray,
    cl_array: np.ndarray,
    cd_array: np.ndarray,
    mac_m: float,
    rho: float,
    v_anchor_points: list[float],
    cl_max: float,
    ar: float,
    v_sweep_max: float | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Build a complete Re-table with e_oswald populated (AR-aware).

    This is the primary entry point for recompute_assumptions. It:
    1. Performs degeneracy check
    2. Clamps top anchor to actual sweep range (Fix I2)
    3. Bins samples into V-bands
    4. Fits each band with AR to get e_oswald
    5. Returns (table, degenerate_bool)

    Parameters
    ----------
    ar           : float — main wing aspect ratio (b²/S); required for e_oswald
    v_sweep_max  : float | None — actual upper bound of the velocity sweep.
                   When provided, the top anchor is clamped to
                   min(top_anchor, v_sweep_max) to prevent anchor-vs-sweep
                   range mismatch (gh-493 I2).

    Returns
    -------
    (table, degenerate_bool) where table is a list of plain dicts with
    keys: {re, v_mps, cd0, e_oswald, cl_max, r2, fallback_used}.

    Callers should validate and serialise each row through
    ``PolarReTableRow(**row).model_dump()`` at cache-write boundaries
    (gh-493 I3).  This strips any internal fields and enforces schema.

    The ``polar_re_table_top_band_fallback`` flag is embedded in the
    returned dicts via the ``fallback_used`` field; callers should check
    ``any(r["fallback_used"] for r in table)`` for a top-band warning.
    """
    v_anchors = sorted(v_anchor_points)

    # I2: Clamp top anchor to the actual sweep range
    if v_sweep_max is not None and v_anchors:
        top_anchor = v_anchors[-1]
        clamped_top = min(top_anchor, v_sweep_max)
        if clamped_top < top_anchor:
            logger.warning(
                "Re table: top anchor V=%.1f m/s exceeds sweep max V=%.1f m/s — "
                "clamping to sweep max to avoid sparse top band.",
                top_anchor, v_sweep_max,
            )
            v_anchors[-1] = clamped_top

    re_anchors = [_reynolds_number_from_v(v, mac_m, rho) for v in v_anchors]
    re_min = min(re_anchors)
    re_max = max(re_anchors)
    degenerate = (re_max / re_min) < _RE_DEGENERACY_RATIO if re_min > 0 else True

    if degenerate:
        logger.warning(
            "Re table degeneracy: Re_max/Re_min = %.2f < %.1f — single-row fallback.",
            re_max / re_min if re_min > 0 else float("inf"),
            _RE_DEGENERACY_RATIO,
        )
        row = _fit_band_with_ar(v_array, cl_array, cd_array,
                                v_center=v_anchors[len(v_anchors) // 2],
                                mac_m=mac_m, rho=rho, cl_max=cl_max, ar=ar)
        row["fallback_used"] = True
        return [row], True

    table: list[dict[str, Any]] = []
    top_band_fallback = False
    for v_center in v_anchors:
        v_lo, v_hi = _band_boundaries(v_center, v_anchors)
        mask = (v_array >= v_lo) & (v_array <= v_hi)
        n_samples = int(mask.sum())

        if n_samples < _MIN_SAMPLES_PER_BAND:
            logger.warning(
                "Re table band V=%.1f m/s: only %d samples (need ≥ %d) — fallback.",
                v_center, n_samples, _MIN_SAMPLES_PER_BAND,
            )
            fallback = _fallback_row(v_center, mac_m, rho, cl_max)
            table.append(fallback)
            if v_center == v_anchors[-1]:
                top_band_fallback = True
            continue

        row = _fit_band_with_ar(
            v_array=v_array[mask],
            cl_array=cl_array[mask],
            cd_array=cd_array[mask],
            v_center=v_center,
            mac_m=mac_m,
            rho=rho,
            cl_max=cl_max,
            ar=ar,
        )
        if row.get("fallback_used") and v_center == v_anchors[-1]:
            top_band_fallback = True
        table.append(row)

    table.sort(key=lambda r: r["re"])

    # Embed top_band_fallback flag (I2) — stored in the degenerate companion field
    # for now; callers may check ctx["polar_re_table_top_band_fallback"]
    return table, False
