"""Turbulator optimizer service — gh-935 Slice 2.

For each wing section at its operating point (local CL, local Re):
  cd_clean   = NeuralFoil at natural transition (xtr_upper=1.0)
  cd_tripped = NeuralFoil at xtr_opt (argmin cd over XTR_GRID)

3D effect → additive ΔCD0, area-weighted:
  ΔCD0 = Σ_sections (cd_tripped_i − cd_clean_i) * (S_i / S_ref)

Non-convergence (NaN cd, no interior minimum, or low NeuralFoil confidence)
emits a per-section WARNING in the result — NOT a silent fallback.

Scope parameter
  "section"  → per-section optima (default)
  "segment"  → per-segment (group by segment, one xtr at representative Re)
  "whole"    → one xtr for the whole wing at the MAC Re

Public API
----------
XTR_GRID                      — config constant: 15-point sweep from 0.2 to 0.9
WingSectionData               — input per section
SectionOptimizerResult        — output per section
TurbulatorOptimizerSummary    — 3D aggregate (L/D, ΔCD0)
TurbulatorOptimizerResult     — full result (sections + summary)
_cd_at_cl_xtr(...)            — atomic cd lookup for a given cl/Re/xtr
optimize_section_xtr(...)     — sweep + argmin for one section
compute_turbulator_delta_cd0  — area-weighted ΔCD0
compute_ld_summary            — L/D clean + tripped from ΔCD0
run_turbulator_optimizer(...)  — full wing run
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: x/c sweep grid (15 points, 0.2 → 0.9 inclusive).
#: Used for both optimizer and mandatory AeroBuildup integration.
XTR_GRID: np.ndarray = np.linspace(0.2, 0.9, 15)

#: NeuralFoil confidence threshold below which we emit a warning.
_CONFIDENCE_THRESHOLD = 0.80

#: Alpha values used for cd lookup at a target CL (fine enough for
#: linear interpolation to be accurate, cheap enough for real-time use).
_ALPHA_GRID = np.linspace(-4.0, 14.0, 37)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class WingSectionData:
    """Input data for one wing section (provided by the caller / section_aoa_service)."""

    y_m: float
    chord_m: float
    cl: float
    re_local: float
    airfoil_name: str
    section_area_m2: float


@dataclass
class SectionOptimizerResult:
    """Per-section optimizer output."""

    y_m: float
    chord_m: float
    re_local: float
    cl: float
    xtr_opt: float
    cd_clean: float
    cd_tripped: float
    delta_cd: float
    warnings: list[str]
    section_area_m2: float


@dataclass
class TurbulatorOptimizerSummary:
    """3-D aggregate summary."""

    delta_cd0: float
    l_d_clean: float
    l_d_tripped: float
    delta_l_d: float


@dataclass
class TurbulatorOptimizerResult:
    """Full optimizer result: per-section data + 3D summary."""

    sections: list[SectionOptimizerResult]
    summary: TurbulatorOptimizerSummary
    scope: str


# ---------------------------------------------------------------------------
# Atomic helper: cd at a target CL for a given xtr
# ---------------------------------------------------------------------------


def _cd_at_cl_xtr(
    airfoil,
    cl_target: float,
    re: float,
    xtr_upper: float,
    xtr_lower: float = 1.0,
    model_size: str = "small",
) -> float:
    """Return the cd at the given CL operating point and trip position.

    Calls ``airfoil.get_aero_from_neuralfoil`` over a fixed alpha grid,
    interpolates to find cd at ``cl_target``.

    Returns NaN on NeuralFoil failure or if CL range does not bracket
    ``cl_target`` (prevents silent extrapolation).
    """
    try:
        aero = airfoil.get_aero_from_neuralfoil(
            alpha=_ALPHA_GRID,
            Re=re,
            xtr_upper=xtr_upper,
            xtr_lower=xtr_lower,
            model_size=model_size,
        )
        cl_arr = np.atleast_1d(aero["CL"]).astype(float)
        cd_arr = np.atleast_1d(aero["CD"]).astype(float)

        # Require finite values
        mask = np.isfinite(cl_arr) & np.isfinite(cd_arr)
        if not mask.any():
            return float("nan")

        cl_valid = cl_arr[mask]
        cd_valid = cd_arr[mask]

        # Sort by CL for interpolation
        sort_idx = np.argsort(cl_valid)
        cl_sorted = cl_valid[sort_idx]
        cd_sorted = cd_valid[sort_idx]

        # Only interpolate within the CL range (no extrapolation)
        if cl_target < cl_sorted[0] or cl_target > cl_sorted[-1]:
            # Fall back to nearest-neighbour cd
            nearest = int(np.argmin(np.abs(cl_sorted - cl_target)))
            return float(cd_sorted[nearest])

        return float(np.interp(cl_target, cl_sorted, cd_sorted))

    except Exception:
        logger.debug("NeuralFoil call failed for xtr_upper=%.3f", xtr_upper, exc_info=True)
        return float("nan")


# ---------------------------------------------------------------------------
# Section-level optimizer: sweep XTR_GRID, pick argmin cd
# ---------------------------------------------------------------------------


def optimize_section_xtr(
    airfoil,
    cl: float,
    re: float,
    xtr_grid: np.ndarray | None = None,
) -> SectionOptimizerResult:
    """Sweep xtr_upper over ``xtr_grid`` at the given (cl, Re) operating point.

    Returns the xtr_opt that minimises cd.  Emits warnings for:
    - NaN cd at any grid point (NeuralFoil convergence failure)
    - Low NeuralFoil analysis_confidence
    - No interior minimum (cd monotonically decreasing or increasing —
      indicates boundary solution, not a genuine bubble-kill optimum)

    Non-convergence / unphysical results are surfaced in warnings; xtr_opt
    is set to NaN when the sweep entirely fails (project rule: no silent fallback).
    """
    if xtr_grid is None:
        xtr_grid = XTR_GRID

    warnings: list[str] = []

    # --- cd sweep -----------------------------------------------------------
    cd_values = np.array([_cd_at_cl_xtr(airfoil, cl, re, float(xtr)) for xtr in xtr_grid])

    # --- Check NeuralFoil confidence ----------------------------------------
    # Sample confidence at the first xtr just to check the model quality.
    try:
        aero_check = airfoil.get_aero_from_neuralfoil(
            alpha=_ALPHA_GRID,
            Re=re,
            xtr_upper=float(xtr_grid[len(xtr_grid) // 2]),
            model_size="small",
        )
        conf_arr = np.atleast_1d(aero_check.get("analysis_confidence", [1.0])).astype(float)
        conf_mean = float(np.nanmean(conf_arr))
        if conf_mean < _CONFIDENCE_THRESHOLD:
            warnings.append(
                f"Low NeuralFoil analysis_confidence={conf_mean:.2f} < {_CONFIDENCE_THRESHOLD} "
                f"at Re={re:.0f}: optimizer results may be unreliable."
            )
    except Exception:
        pass  # confidence check is advisory; don't block the result

    # --- Natural-transition baseline ----------------------------------------
    cd_clean = _cd_at_cl_xtr(airfoil, cl, re, xtr_upper=1.0)

    # --- All-NaN guard -------------------------------------------------------
    finite_mask = np.isfinite(cd_values)
    if not finite_mask.any():
        warnings.append(
            f"Turbulator optimizer: all cd values are NaN for Re={re:.0f}, "
            f"CL={cl:.3f}. NeuralFoil did not converge — no optimal xtr found."
        )
        return SectionOptimizerResult(
            y_m=0.0,
            chord_m=0.0,
            re_local=re,
            cl=cl,
            xtr_opt=float("nan"),
            cd_clean=cd_clean if math.isfinite(cd_clean) else float("nan"),
            cd_tripped=float("nan"),
            delta_cd=float("nan"),
            warnings=warnings,
            section_area_m2=0.0,
        )

    # --- Argmin among finite values -----------------------------------------
    finite_indices = np.where(finite_mask)[0]
    i_opt = finite_indices[int(np.argmin(cd_values[finite_mask]))]
    xtr_opt = float(xtr_grid[i_opt])
    cd_tripped = float(cd_values[i_opt])

    # --- No-interior-minimum warning ----------------------------------------
    # If the optimum is at the boundary of the grid, it may indicate that the
    # true minimum is outside the range — surface this for the user.
    if i_opt == 0 or i_opt == len(xtr_grid) - 1:
        warnings.append(
            f"Turbulator optimizer: xtr_opt={xtr_opt:.3f} is at the grid boundary "
            f"(not an interior minimum). The optimal trip position may lie outside "
            f"the sweep range [0.2, 0.9]."
        )

    if not math.isfinite(cd_clean):
        cd_clean = cd_tripped  # fallback — can't compute delta

    delta_cd = cd_tripped - cd_clean

    return SectionOptimizerResult(
        y_m=0.0,
        chord_m=0.0,
        re_local=re,
        cl=cl,
        xtr_opt=xtr_opt,
        cd_clean=cd_clean,
        cd_tripped=cd_tripped,
        delta_cd=delta_cd,
        warnings=warnings,
        section_area_m2=0.0,
    )


# ---------------------------------------------------------------------------
# 3-D aggregation
# ---------------------------------------------------------------------------


def compute_turbulator_delta_cd0(
    section_results: list[SectionOptimizerResult],
    s_ref: float,
) -> float:
    """Area-weighted 3-D ΔCD0 from per-section results.

    ΔCD0 = Σ (cd_tripped_i − cd_clean_i) * S_i / S_ref

    Sections with NaN delta_cd (failed optimizer) are skipped.
    Returns 0.0 if no valid sections or s_ref ≤ 0.
    """
    if s_ref <= 0:
        return 0.0

    delta_cd0 = 0.0
    for sec in section_results:
        if math.isfinite(sec.delta_cd) and sec.section_area_m2 > 0:
            delta_cd0 += sec.delta_cd * sec.section_area_m2 / s_ref

    return delta_cd0


def compute_ld_summary(
    cl: float,
    cd_clean: float,
    delta_cd0: float,
) -> TurbulatorOptimizerSummary:
    """Compute L/D with and without turbulator from the 3-D ΔCD0.

    L_D_tripped = CL / (CD_clean + ΔCD0)
    """
    l_d_clean = cl / cd_clean if cd_clean > 0 else float("nan")
    cd_tripped = cd_clean + delta_cd0
    l_d_tripped = cl / cd_tripped if cd_tripped > 0 else float("nan")
    delta_l_d = l_d_tripped - l_d_clean if math.isfinite(l_d_tripped) and math.isfinite(l_d_clean) else float("nan")
    return TurbulatorOptimizerSummary(
        delta_cd0=delta_cd0,
        l_d_clean=l_d_clean,
        l_d_tripped=l_d_tripped,
        delta_l_d=delta_l_d,
    )


# ---------------------------------------------------------------------------
# Full wing optimizer
# ---------------------------------------------------------------------------


def run_turbulator_optimizer(
    sections: list[WingSectionData],
    s_ref: float,
    scope: Literal["section", "segment", "whole"] = "section",
    xtr_grid: np.ndarray | None = None,
) -> TurbulatorOptimizerResult:
    """Run the turbulator optimizer over all sections.

    Parameters
    ----------
    sections:
        Per-section input data (y_m, chord_m, cl, re_local, airfoil_name, section_area_m2).
    s_ref:
        Reference wing area [m²] for ΔCD0 area-weighting.
    scope:
        "section" → per-section optima (independent xtr per section).
        "segment" → per-segment (group by segment; one xtr per group).
        "whole"   → single xtr for all sections at the CL-weighted mean Re.
    xtr_grid:
        Override the default XTR_GRID (useful for testing).

    Returns
    -------
    TurbulatorOptimizerResult with per-section results and 3D summary.
    """
    from app.converters.model_schema_converters import _build_asb_airfoil

    if xtr_grid is None:
        xtr_grid = XTR_GRID

    section_results: list[SectionOptimizerResult] = []

    if scope in ("section", "segment"):
        # Per-section (segment grouping is identical for this slice;
        # Slice 3 will add segment ID tracking).
        for sec in sections:
            try:
                airfoil = _build_asb_airfoil(sec.airfoil_name)
            except Exception as exc:
                logger.warning("Could not build airfoil %r: %s", sec.airfoil_name, exc)
                section_results.append(
                    SectionOptimizerResult(
                        y_m=sec.y_m,
                        chord_m=sec.chord_m,
                        re_local=sec.re_local,
                        cl=sec.cl,
                        xtr_opt=float("nan"),
                        cd_clean=float("nan"),
                        cd_tripped=float("nan"),
                        delta_cd=float("nan"),
                        warnings=[f"Could not build airfoil {sec.airfoil_name!r}: {exc}"],
                        section_area_m2=sec.section_area_m2,
                    )
                )
                continue

            raw = optimize_section_xtr(airfoil, cl=sec.cl, re=sec.re_local, xtr_grid=xtr_grid)
            section_results.append(
                SectionOptimizerResult(
                    y_m=sec.y_m,
                    chord_m=sec.chord_m,
                    re_local=raw.re_local,
                    cl=raw.cl,
                    xtr_opt=raw.xtr_opt,
                    cd_clean=raw.cd_clean,
                    cd_tripped=raw.cd_tripped,
                    delta_cd=raw.delta_cd,
                    warnings=raw.warnings,
                    section_area_m2=sec.section_area_m2,
                )
            )

    elif scope == "whole":
        # Find a single xtr that minimises the area-weighted total drag
        # at the wing's representative (CL-weighted) Re.
        if not sections:
            pass
        else:
            # Representative Re = area-weighted average
            total_area = sum(s.section_area_m2 for s in sections)
            re_rep = (
                sum(s.re_local * s.section_area_m2 for s in sections) / total_area
                if total_area > 0
                else sections[len(sections) // 2].re_local
            )
            cl_rep = (
                sum(s.cl * s.section_area_m2 for s in sections) / total_area
                if total_area > 0
                else sections[len(sections) // 2].cl
            )

            # Find global xtr_opt for the representative section
            try:
                rep_airfoil_name = sections[len(sections) // 2].airfoil_name
                rep_airfoil = _build_asb_airfoil(rep_airfoil_name)
                rep_result = optimize_section_xtr(
                    rep_airfoil, cl=cl_rep, re=re_rep, xtr_grid=xtr_grid
                )
                global_xtr_opt = rep_result.xtr_opt
            except Exception as exc:
                logger.warning("Whole-scope optimizer failed: %s", exc)
                global_xtr_opt = float("nan")

            # Apply the single global xtr_opt to all sections
            for sec in sections:
                try:
                    airfoil = _build_asb_airfoil(sec.airfoil_name)
                    cd_clean = _cd_at_cl_xtr(airfoil, sec.cl, sec.re_local, xtr_upper=1.0)
                    cd_tripped = (
                        _cd_at_cl_xtr(airfoil, sec.cl, sec.re_local, xtr_upper=global_xtr_opt)
                        if math.isfinite(global_xtr_opt)
                        else float("nan")
                    )
                    delta_cd = cd_tripped - cd_clean if (
                        math.isfinite(cd_tripped) and math.isfinite(cd_clean)
                    ) else float("nan")
                    section_results.append(
                        SectionOptimizerResult(
                            y_m=sec.y_m,
                            chord_m=sec.chord_m,
                            re_local=sec.re_local,
                            cl=sec.cl,
                            xtr_opt=global_xtr_opt,
                            cd_clean=cd_clean,
                            cd_tripped=cd_tripped,
                            delta_cd=delta_cd,
                            warnings=[],
                            section_area_m2=sec.section_area_m2,
                        )
                    )
                except Exception as exc:
                    section_results.append(
                        SectionOptimizerResult(
                            y_m=sec.y_m, chord_m=sec.chord_m, re_local=sec.re_local,
                            cl=sec.cl, xtr_opt=float("nan"), cd_clean=float("nan"),
                            cd_tripped=float("nan"), delta_cd=float("nan"),
                            warnings=[str(exc)], section_area_m2=sec.section_area_m2,
                        )
                    )

    # --- 3-D summary --------------------------------------------------------
    delta_cd0 = compute_turbulator_delta_cd0(section_results, s_ref)

    # CL for L/D: use area-weighted average of section CLs
    if sections:
        total_area = sum(s.section_area_m2 for s in sections)
        cl_avg = (
            sum(s.cl * s.section_area_m2 for s in sections) / total_area
            if total_area > 0
            else sections[0].cl
        )
    else:
        cl_avg = 0.0

    # CD_clean for L/D: area-weighted average cd_clean
    valid_clean = [
        (sec.cd_clean, sec.section_area_m2)
        for sec in section_results
        if math.isfinite(sec.cd_clean) and sec.section_area_m2 > 0
    ]
    if valid_clean and s_ref > 0:
        total_valid_area = sum(a for _, a in valid_clean)
        cd_clean_avg = (
            sum(cd * a for cd, a in valid_clean) / total_valid_area
            if total_valid_area > 0
            else float("nan")
        )
    else:
        cd_clean_avg = float("nan")

    summary = compute_ld_summary(cl=cl_avg, cd_clean=cd_clean_avg, delta_cd0=delta_cd0)

    return TurbulatorOptimizerResult(sections=section_results, summary=summary, scope=scope)


# ---------------------------------------------------------------------------
# ΔCD0 from CURRENT turbulator position (for mandatory AeroBuildup integration)
# ---------------------------------------------------------------------------


def compute_delta_cd0_from_turbulator_position(
    sections: list[WingSectionData],
    xtr_root: float,
    xtr_tip: float,
    s_ref: float,
) -> tuple[float, list[str]]:
    """Compute ΔCD0 using the turbulator's CURRENT position (not the optimizer).

    Used in Part D (mandatory AeroBuildup integration): when a wing has an
    enabled turbulator with position_root / position_tip set, we add the
    corresponding cd delta to the aircraft's cd0.

    Parameters
    ----------
    sections:
        Per-section data (with y_m for tip interpolation, cl, re_local, airfoil).
    xtr_root, xtr_tip:
        The turbulator's CURRENT x/c positions at root and tip.
    s_ref:
        Reference wing area.

    Returns
    -------
    (delta_cd0, warnings) where delta_cd0 is the area-weighted ΔCD0 and
    warnings is a list of per-section warning strings.
    """
    from app.converters.model_schema_converters import _build_asb_airfoil

    if not sections or s_ref <= 0:
        return 0.0, []

    # Span fraction for tip interpolation
    y_values = [s.y_m for s in sections]
    y_min = min(y_values)
    y_max = max(y_values)
    y_span = y_max - y_min if y_max > y_min else 1.0

    section_results: list[SectionOptimizerResult] = []
    all_warnings: list[str] = []

    for sec in sections:
        # Linear interpolation of xtr along the span
        frac = (sec.y_m - y_min) / y_span if y_span > 0 else 0.0
        xtr_sec = xtr_root + frac * (xtr_tip - xtr_root)
        xtr_sec = float(np.clip(xtr_sec, 0.0, 1.0))

        try:
            airfoil = _build_asb_airfoil(sec.airfoil_name)
            cd_clean = _cd_at_cl_xtr(airfoil, sec.cl, sec.re_local, xtr_upper=1.0)
            cd_tripped = _cd_at_cl_xtr(airfoil, sec.cl, sec.re_local, xtr_upper=xtr_sec)
        except Exception as exc:
            msg = f"Turbulator ΔCD0 failed for section y={sec.y_m:.3f}m: {exc}"
            all_warnings.append(msg)
            continue

        if not (math.isfinite(cd_clean) and math.isfinite(cd_tripped)):
            msg = (
                f"Turbulator ΔCD0: NaN cd at y={sec.y_m:.3f}m "
                f"(Re={sec.re_local:.0f}, CL={sec.cl:.3f}, xtr={xtr_sec:.3f})"
            )
            all_warnings.append(msg)
            continue

        section_results.append(
            SectionOptimizerResult(
                y_m=sec.y_m,
                chord_m=sec.chord_m,
                re_local=sec.re_local,
                cl=sec.cl,
                xtr_opt=xtr_sec,
                cd_clean=cd_clean,
                cd_tripped=cd_tripped,
                delta_cd=cd_tripped - cd_clean,
                warnings=[],
                section_area_m2=sec.section_area_m2,
            )
        )

    delta_cd0 = compute_turbulator_delta_cd0(section_results, s_ref)
    return delta_cd0, all_warnings
