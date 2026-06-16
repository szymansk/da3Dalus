"""Spar-sizing from spanwise bending-moment distribution (gh-1008).

Pure module — no aerosandbox, no database dependencies.
Fast-tier unit-testable.

Reference: kirch Hauptholm (https://www.flugmodellbau-kirch.de/Hauptholm.htm)
and the user's section-modulus scan.

Design formula:
  M_design(y) = |M(y)| · g_limit · j
  erf_W = M_design / σ_allow
  outer = chord(y) · (t/c)(y) · packing
  → solve free dimension per shape

Units:
  Inputs: M in N·m, σ in MPa (N/mm²), dimensions in mm.
  W is in mm³.
  Mass is in kg.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from app.schemas.spar_sizing import SparSizingParams, SparSizingResult, SparSizingStation

logger = logging.getLogger(__name__)

# Fallback t/c ratio when airfoil data is unavailable.
_TC_FALLBACK = 0.12


# ---------------------------------------------------------------------------
# Section-modulus formulas (dimensions in mm, W in mm³)
# ---------------------------------------------------------------------------


def section_modulus_rectangular(b: float, h: float) -> float:
    """Section modulus for a solid rectangular spar b×h (mm).

    W = b · h² / 6   [mm³]
    """
    return b * h**2 / 6.0


def section_modulus_capped(b: float, H: float, h: float) -> float:
    """Section modulus for a capped (I-beam / C-beam) spar.

    b = flange width, H = outer height, h = inner gap height (all mm).
    W = b · (H³ − h³) / (6 · H)   [mm³]
    """
    return b * (H**3 - h**3) / (6.0 * H)


def section_modulus_rod(d: float) -> float:
    """Section modulus for a solid round rod of diameter d (mm).

    W = d³ / 10   [mm³]
    """
    return d**3 / 10.0


def section_modulus_tube(Da: float, Di: float) -> float:
    """Section modulus for a circular tube (outer Da, inner Di, mm).

    W = π · (Da⁴ − Di⁴) / (32 · Da)   [mm³]
    """
    return math.pi * (Da**4 - Di**4) / (32.0 * Da)


# ---------------------------------------------------------------------------
# Required section modulus
# ---------------------------------------------------------------------------


def required_section_modulus(m_design_Nm: float, sigma_allow_mpa: float) -> float:
    """Compute the required section modulus erf_W (mm³).

    erf_W = M_design [N·m] × 1000 [mm/m] / σ_allow [N/mm²]

    Raises ValueError on σ_allow ≤ 0 (callers resolve σ from a material whose
    schema permits 0; guard here so we never divide by zero — gh-1008 review).
    """
    if sigma_allow_mpa <= 0:
        raise ValueError(f"sigma_allow must be positive, got {sigma_allow_mpa}")
    return m_design_Nm * 1000.0 / sigma_allow_mpa


# ---------------------------------------------------------------------------
# solve_dimension — solves the free spar dimension for each shape
# ---------------------------------------------------------------------------


def solve_dimension(
    shape: str,
    erf_w: float,
    outer_mm: float,
    cap_width_mm: float | None = None,
) -> dict[str, Any]:
    """Solve the free spar dimension for the given shape.

    The outer dimension (outer_mm) is fixed by the local airfoil thickness.
    The free dimension is derived analytically.

    Returns a dict with keys:
      - solved_mm: float | None
      - feasible: bool
      - infeasibility_reason: str | None
      - cross_section_area_mm2: float | None
      - inner_mm: float | None   (Tube only — Di)

    Shape dispatch:
      tube:        Da = outer, solve Di → wall = (Da-Di)/2
      rod:         solve d = (10·erf_w)^(1/3), check d ≤ outer
      rectangular: h = outer, solve b = 6·erf_w / h²
      capped:      H = outer, b = cap_width_mm, solve h = (H³-6·H·erf_w/b)^(1/3),
                   gurt = (H-h)/2
    """
    if shape == "tube":
        return _solve_tube(erf_w, outer_mm)
    elif shape == "rod":
        return _solve_rod(erf_w, outer_mm)
    elif shape == "rectangular":
        return _solve_rectangular(erf_w, outer_mm)
    elif shape == "capped":
        if cap_width_mm is None:
            raise ValueError("cap_width_mm is required for shape='capped'")
        return _solve_capped(erf_w, outer_mm, cap_width_mm)
    else:
        raise ValueError(f"Unknown spar shape: {shape!r}")


def _solve_tube(erf_w: float, outer_mm: float) -> dict[str, Any]:
    Da = outer_mm
    discriminant = Da**4 - 32.0 * erf_w * Da / math.pi
    if discriminant < 0.0:
        return {
            "solved_mm": None,
            "feasible": False,
            "infeasibility_reason": "solid needed — required W exceeds tube capacity at this outer diameter",
            "cross_section_area_mm2": None,
            "inner_mm": None,
        }
    Di = discriminant**0.25
    wall = (Da - Di) / 2.0
    area = math.pi * (Da**2 - Di**2) / 4.0
    return {
        "solved_mm": wall,
        "feasible": True,
        "infeasibility_reason": None,
        "cross_section_area_mm2": area,
        "inner_mm": Di,
    }


def _solve_rod(erf_w: float, outer_mm: float) -> dict[str, Any]:
    d = (10.0 * erf_w) ** (1.0 / 3.0)
    if d > outer_mm + 1e-9:
        return {
            "solved_mm": d,
            "feasible": False,
            "infeasibility_reason": (
                f"rod too big — required d={d:.1f} mm exceeds profile thickness {outer_mm:.1f} mm"
            ),
            "cross_section_area_mm2": math.pi * d**2 / 4.0,
            "inner_mm": None,
        }
    area = math.pi * d**2 / 4.0
    return {
        "solved_mm": d,
        "feasible": True,
        "infeasibility_reason": None,
        "cross_section_area_mm2": area,
        "inner_mm": None,
    }


def _solve_rectangular(erf_w: float, outer_mm: float) -> dict[str, Any]:
    h = outer_mm
    b = 6.0 * erf_w / h**2 if h > 0.0 else 0.0
    area = b * h
    return {
        "solved_mm": b,
        "feasible": True,
        "infeasibility_reason": None,
        "cross_section_area_mm2": area,
        "inner_mm": None,
    }


def _solve_capped(erf_w: float, outer_mm: float, cap_width_mm: float) -> dict[str, Any]:
    H = outer_mm
    b = cap_width_mm
    inner_cube = H**3 - 6.0 * H * erf_w / b
    if inner_cube < 0.0:
        return {
            "solved_mm": None,
            "feasible": False,
            "infeasibility_reason": (
                f"capped spar infeasible — H³={H**3:.1f} < 6·H·W/b={6 * H * erf_w / b:.1f}; "
                "increase H or b"
            ),
            "cross_section_area_mm2": None,
            "inner_mm": None,
        }
    h = inner_cube ** (1.0 / 3.0)
    gurt = (H - h) / 2.0
    area = 2.0 * b * gurt  # two flanges (upper + lower)
    return {
        "solved_mm": gurt,
        "feasible": True,
        "infeasibility_reason": None,
        "cross_section_area_mm2": area,
        "inner_mm": h,
    }


# ---------------------------------------------------------------------------
# Mass integration
# ---------------------------------------------------------------------------


def spar_mass_half_kg(
    ys_m: list[float],
    areas_mm2: list[float],
    density_kg_m3: float,
) -> float:
    """Estimate spar mass for a half-span by trapezoidal integration.

    Args:
        ys_m: Spanwise positions in metres, ordered tip-to-root (decreasing).
              May also be root-to-tip — only absolute differences matter.
        areas_mm2: Cross-section area at each station (mm²), same order as ys_m.
        density_kg_m3: Material density in kg/m³.

    Returns:
        Estimated half-span spar mass in kg.
    """
    if len(ys_m) < 2:
        return 0.0

    total_mass = 0.0
    for i in range(len(ys_m) - 1):
        dy = abs(ys_m[i] - ys_m[i + 1])  # segment length (m)
        avg_area_mm2 = (areas_mm2[i] + areas_mm2[i + 1]) / 2.0
        avg_area_m2 = avg_area_mm2 * 1e-6  # mm² → m²
        volume_m3 = avg_area_m2 * dy
        total_mass += density_kg_m3 * volume_m3

    return total_mass


# ---------------------------------------------------------------------------
# compute_spar_sizing — main pure orchestrator
# ---------------------------------------------------------------------------


def compute_spar_sizing(
    stations: list[dict[str, Any]],
    tc_by_y: dict[float, float],
    material_specs: dict[str, Any],
    material_name: str,
    params: SparSizingParams,
    g_limit: float,
    g_limit_fallback: bool,
    surface_name: str,
) -> SparSizingResult:
    """Size the spar at each spanwise station.

    Args:
        stations: List of dicts with keys ``y_m``, ``chord_m``,
            ``bending_moment_Nm`` — ordered tip-to-root (outboard first).
        tc_by_y: Mapping {y_m (float, rounded): t/c ratio} from wing-section
            airfoil data.  Missing entries trigger the 0.12 fallback.
        material_specs: The ``specs`` dict from the ComponentRead (real schema
            keys: ``density_kg_m3``, ``allowable_bending_stress_mpa``).
        material_name: Human-readable material name for the result.
        params: SparSizingParams with shape, j, packing, etc.
        g_limit: Limit load factor from design assumptions.
        g_limit_fallback: True if g_limit is a default fallback.
        surface_name: Name of the aerodynamic surface being sized.

    Returns:
        SparSizingResult with per-station and aggregate results.
    """
    # Resolve σ_allow
    sigma_allow = (
        params.sigma_allow_mpa_override
        if params.sigma_allow_mpa_override is not None
        else float(material_specs["allowable_bending_stress_mpa"])
    )
    density = float(material_specs["density_kg_m3"])

    sized_stations: list[SparSizingStation] = []
    tc_fallback_ys: list[float] = []

    for st in stations:
        y_m = float(st["y_m"])
        chord_m = float(st["chord_m"])
        bm = float(st["bending_moment_Nm"])

        # t/c lookup with fallback
        tc_ratio, tc_fallback = _get_tc(tc_by_y, y_m)
        if tc_fallback:
            tc_fallback_ys.append(y_m)

        # Design moment (always positive)
        m_design = abs(bm) * g_limit * params.safety_factor_j

        # Required section modulus
        erf_w = required_section_modulus(m_design, sigma_allow)

        # Outer dimension (mm) = chord (m → mm) · t/c · packing
        chord_mm = chord_m * 1000.0
        profile_thickness_mm = chord_mm * tc_ratio
        outer_mm = profile_thickness_mm * params.packing_factor

        # Solve free dimension
        sol = solve_dimension(
            shape=params.shape,
            erf_w=erf_w,
            outer_mm=outer_mm,
            cap_width_mm=params.cap_width_mm,
        )

        sized_stations.append(
            SparSizingStation(
                y_m=y_m,
                chord_m=chord_m,
                profile_thickness_mm=profile_thickness_mm,
                outer_mm=outer_mm,
                tc_ratio=tc_ratio,
                tc_fallback=tc_fallback,
                m_design_Nm=m_design,
                required_W_mm3=erf_w,
                solved_mm=sol.get("solved_mm"),
                feasible=sol["feasible"],
                infeasibility_reason=sol.get("infeasibility_reason"),
                cross_section_area_mm2=sol.get("cross_section_area_mm2"),
            )
        )

    # Root station = innermost (last in outboard-first list)
    root_station = sized_stations[-1] if sized_stations else _zero_station()

    # Spar mass — trapezoidal over the half-span
    ys = [s.y_m for s in sized_stations]
    areas = [
        s.cross_section_area_mm2 if s.cross_section_area_mm2 is not None else 0.0
        for s in sized_stations
    ]
    half_mass = spar_mass_half_kg(ys_m=ys, areas_mm2=areas, density_kg_m3=density)

    # t/c fallback warning
    tc_warn: str | None = None
    if tc_fallback_ys:
        ys_str = ", ".join(f"{y:.2f}" for y in tc_fallback_ys)
        tc_warn = (
            f"t/c=0.12 fallback applied at y={ys_str} m — no airfoil thickness data available."
        )

    return SparSizingResult(
        surface_name=surface_name,
        shape=params.shape,
        material_name=material_name,
        sigma_allow_mpa=sigma_allow,
        density_kg_m3=density,
        g_limit=g_limit,
        g_limit_fallback=g_limit_fallback,
        safety_factor_j=params.safety_factor_j,
        packing_factor=params.packing_factor,
        stations=sized_stations,
        root_station=root_station,
        spar_mass_half_kg=half_mass,
        spar_mass_full_kg=half_mass * 2.0,
        tc_fallback_warning=tc_warn,
    )


def _get_tc(tc_by_y: dict[float, float], y_m: float) -> tuple[float, bool]:
    """Return (tc_ratio, is_fallback) for a given spanwise position.

    Tries exact match then nearest key within 1 cm tolerance.
    Falls back to 0.12 with warning when nothing is found.
    """
    if y_m in tc_by_y:
        return tc_by_y[y_m], False

    # Nearest-key lookup (within 10 mm)
    nearest = min(tc_by_y.keys(), key=lambda k: abs(k - y_m), default=None)
    if nearest is not None and abs(nearest - y_m) < 0.01:
        return tc_by_y[nearest], False

    logger.warning("No t/c data for y=%.3f m — using fallback t/c=%.2f", y_m, _TC_FALLBACK)
    return _TC_FALLBACK, True


def _zero_station() -> SparSizingStation:
    """Return a zeroed station for the edge case of no stations."""
    return SparSizingStation(
        y_m=0.0,
        chord_m=0.0,
        profile_thickness_mm=0.0,
        outer_mm=0.0,
        tc_ratio=_TC_FALLBACK,
        tc_fallback=True,
        m_design_Nm=0.0,
        required_W_mm3=0.0,
        solved_mm=None,
        feasible=False,
        infeasibility_reason="No stations provided",
        cross_section_area_mm2=None,
    )
