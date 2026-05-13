"""Matching chart service — T/W vs W/S constraint diagram (gh-492).

Implements the classical aircraft sizing matching chart (Loftin 1980, Scholz §5.2–5.4):
a 2D plot where each flight phase is expressed as a constraint line T/W(W/S).
The design point is chosen where all constraints are satisfied simultaneously — i.e.,
in the feasible region above/left of all constraint lines.

Sources
-------
- Scholz HAW *Flugzeugentwurf I* §5.2–5.4 (primary, SI units)
- Raymer 6e §5.3–5.4 (cross-check)
- Anderson 6e §6.3 (climb gradient), §6.7 (max L/D / cruise)
- Loftin 1980 (statistical k_TO, k_LDG regression coefficients)
- Roskam Vol I §3.4 (takeoff/landing ground-roll constants)

Convention
----------
T/W = T_static_SL / W_MTOW  (static thrust at sea level over maximum take-off weight)
AR held constant during drag; S = W / (W/S), b = √(AR · S).

Constants from field_length_service
-------------------------------------
``_K_TO_50FT = 1.66``  and  ``_K_LDG_50FT = 2.73``  are **imported** (not re-defined)
from field_length_service to guarantee identical values and zero drift.
The takeoff ground-roll Roskam constant ``_C_TO = 1.21`` is used directly.
"""

from __future__ import annotations

import math
import logging
from typing import Any

# Import shared Loftin/Roskam constants — no local re-definition
from app.services.field_length_service import (
    _K_TO_50FT,    # 1.66  (re-exported for constants-drift tests)
    _K_LDG_50FT,   # 2.73  (re-exported for constants-drift tests)
    _K_LDG_HARD,   # 0.5847
    _C_TO,         # 1.21
    _G,            # 9.81
    _RHO_SL,       # 1.225
)

logger = logging.getLogger(__name__)

__all__ = [
    "compute_chart",
    "_takeoff_constraint",
    "_landing_constraint",
    "_cruise_constraint",
    "_climb_constraint",
    "_stall_constraint",
    "_v_md",
    "_mode_defaults",
    "_K_TO_50FT",
    "_K_LDG_50FT",
]

# ---------------------------------------------------------------------------
# W/S sweep range
# ---------------------------------------------------------------------------

_WS_MIN: float = 10.0       # N/m² — lower bound for W/S sweep
_WS_MAX: float = 1500.0     # N/m² — upper bound
_WS_STEPS: int = 200        # number of points in W/S sweep

# ---------------------------------------------------------------------------
# Constraint colors (Tailwind-compatible hex — matches frontend dark theme)
# ---------------------------------------------------------------------------

_COLOR_TAKEOFF: str = "#FF8400"   # orange accent
_COLOR_LANDING: str = "#3B82F6"   # blue
_COLOR_CRUISE: str = "#30A46C"    # green
_COLOR_CLIMB: str = "#E5484D"     # red
_COLOR_STALL: str = "#A78BFA"     # purple


# ===========================================================================
# Mode defaults
# ===========================================================================


def _mode_defaults(mode: str) -> dict[str, float]:
    """Return default parameter set for a given aircraft mode.

    Modes
    -----
    rc_runway       : RC park-flyer / sport with a short grass strip
    rc_hand_launch  : RC hand-launched (no runway takeoff constraint)
    uav_runway      : Fixed-wing UAV with a proper runway
    uav_belly_land  : UAV with belly-land recovery (no runway landing constraint)

    Returns
    -------
    dict with keys:
      s_runway         : float  — field length target [m] (0 = unconstrained)
      gamma_climb_deg  : float  — climb gradient target [°]
      v_s_target       : float  — max acceptable stall speed [m/s]
    """
    defaults: dict[str, dict[str, float]] = {
        "rc_runway": {
            "s_runway": 50.0,
            "gamma_climb_deg": 5.0,
            "v_s_target": 7.0,
        },
        "rc_hand_launch": {
            "s_runway": 0.0,    # no runway → no takeoff distance constraint
            "gamma_climb_deg": 5.0,
            "v_s_target": 7.0,
        },
        "uav_runway": {
            "s_runway": 200.0,
            "gamma_climb_deg": 4.0,
            "v_s_target": 12.0,
        },
        "uav_belly_land": {
            "s_runway": 200.0,
            "gamma_climb_deg": 4.0,
            "v_s_target": 12.0,
        },
    }
    if mode not in defaults:
        logger.warning("Unknown matching-chart mode '%s'; using 'uav_runway' defaults.", mode)
        return defaults["uav_runway"]
    return dict(defaults[mode])


# ===========================================================================
# Aerodynamics helper
# ===========================================================================


def _v_md(ws: float, cd0: float, e: float, ar: float, rho: float = _RHO_SL) -> float:
    """Speed for minimum drag (best L/D) — Anderson 6e §6.7.

    V_md = [ 2·(W/S) / (ρ · √(CD0 · π·e·AR)) ]^0.5

    Parameters
    ----------
    ws    : float — wing loading W/S [N/m²]
    cd0   : float — zero-lift drag coefficient
    e     : float — Oswald efficiency factor
    ar    : float — wing aspect ratio
    rho   : float — air density [kg/m³]

    Returns
    -------
    V_md in m/s
    """
    k = 1.0 / (math.pi * e * ar)
    # q at min drag: q_opt = sqrt(cd0 / k) * 0.5
    # V_md² = 2·(W/S) / (ρ · √(cd0/k))
    return math.sqrt(2.0 * ws / (rho * math.sqrt(cd0 / k)))


# ===========================================================================
# Individual constraint helpers
# ===========================================================================


def _takeoff_constraint(
    ws: float,
    s_runway: float,
    cl_max_to: float,
    rho: float = _RHO_SL,
    g: float = _G,
) -> float:
    """Minimum T/W required to meet takeoff field length target (Scholz §5.2.3).

    Derived from Roskam §3.4 simplified ground-roll:
        s_TO_ground = C_TO · (W/S) / (ρ · g · CL_max_TO · (T/W))
        s_TO_50ft   = K_TO_50FT · s_TO_ground

    Inverted for T/W:
        T/W = C_TO · (W/S) / (ρ · g · CL_max_TO · s_TO_ground)
            = C_TO · K_TO_50FT · (W/S) / (ρ · g · CL_max_TO · s_TO_50ft)

    Parameters
    ----------
    ws         : float — wing loading W/S [N/m²]
    s_runway   : float — field length target to 50 ft [m];  0 → no constraint (returns 0)
    cl_max_to  : float — max lift coefficient at takeoff configuration
    rho        : float — air density [kg/m³]
    g          : float — gravitational acceleration [m/s²]

    Returns
    -------
    T/W minimum (dimensionless); 0.0 when s_runway == 0 (hand-launch / unconstrained)
    """
    if s_runway <= 0.0:
        return 0.0
    # T/W = C_TO · K_TO_50FT · (W/S) / (ρ · g · CL_max_TO · s_TO_50ft)
    return (_C_TO * _K_TO_50FT * ws) / (rho * g * cl_max_to * s_runway)


def _landing_constraint(
    s_runway: float,
    cl_max_l: float,
    rho: float = _RHO_SL,
    g: float = _G,
) -> float:
    """Maximum W/S to meet landing field length target (vertical line on chart).

    From Roskam §3.4:
        s_LDG_ground = K_LDG_HARD · (W/S) / (ρ · CL_max_LDG)
        s_LDG_50ft   = K_LDG_50FT · s_LDG_ground

    Inverted for W/S:
        W/S_max = s_LDG_50ft · ρ · CL_max_LDG / (K_LDG_HARD · K_LDG_50FT)

    Parameters
    ----------
    s_runway  : float — field length target from 50 ft [m]
    cl_max_l  : float — max lift coefficient in landing configuration
    rho       : float — air density [kg/m³]
    g         : float — (unused; kept for symmetry with other helpers)

    Returns
    -------
    W/S_max [N/m²] — design point must be LEFT of this value
    """
    if s_runway <= 0.0:
        return float("inf")
    return (s_runway * rho * cl_max_l) / (_K_LDG_HARD * _K_LDG_50FT)


def _cruise_constraint(
    ws: float,
    v_cruise: float,
    cd0: float,
    e: float,
    ar: float,
    rho: float = _RHO_SL,
) -> float:
    """T/W required for level cruise at V_cruise — Anderson 6e §6.7 / Scholz §5.4.

    T/W = q·CD0/(W/S) + (W/S)/(q·π·e·AR)
        = D/W  where D = ½ρV²·S·CD,  L=W in cruise

    with q = ½·ρ·V_cruise²  and  k = 1/(π·e·AR).

    Parameters
    ----------
    ws       : float — wing loading W/S [N/m²]
    v_cruise : float — cruise speed [m/s]
    cd0      : float — zero-lift drag coefficient
    e        : float — Oswald efficiency factor
    ar       : float — wing aspect ratio
    rho      : float — air density [kg/m³]

    Returns
    -------
    T/W (dimensionless)
    """
    q = 0.5 * rho * v_cruise * v_cruise
    k = 1.0 / (math.pi * e * ar)
    return q * cd0 / ws + ws * k / q


def _climb_constraint(
    ws: float,
    gamma_deg: float,
    v_climb: float,
    cd0: float,
    e: float,
    ar: float,
    rho: float = _RHO_SL,
) -> float:
    """T/W required to sustain a climb gradient γ — Anderson 6e §6.3.

    T/W = sin(γ) + D/W  (clean polar)

    where D/W at the climb speed V_climb:
        D/W = q·CD0/(W/S) + (W/S)·k/q

    This uses the **clean** drag polar (no flap deployed).

    Parameters
    ----------
    ws        : float — wing loading [N/m²]
    gamma_deg : float — climb gradient [°]
    v_climb   : float — climb speed [m/s]
    cd0       : float — zero-lift drag coefficient (clean)
    e         : float — Oswald efficiency factor (clean)
    ar        : float — wing aspect ratio
    rho       : float — air density [kg/m³]

    Returns
    -------
    T/W (dimensionless); always ≥ sin(γ)
    """
    gamma_rad = math.radians(gamma_deg)
    q = 0.5 * rho * v_climb * v_climb
    k = 1.0 / (math.pi * e * ar)
    drag_over_weight = q * cd0 / ws + ws * k / q
    return math.sin(gamma_rad) + drag_over_weight


def _stall_constraint(
    v_s_target: float,
    cl_max_clean: float,
    rho: float = _RHO_SL,
) -> float:
    """Maximum W/S to meet stall-speed target (vertical line on chart).

    At stall speed V_s the lift equation in level flight gives:
        L = ½·ρ·V_s²·S·CL_max_clean = W
        → W/S_max = ½·ρ·V_s²·CL_max_clean

    **Uses CL_max_clean** (clean polar, not landing-flaps CL_max) per spec.

    Parameters
    ----------
    v_s_target   : float — maximum acceptable stall speed [m/s]
    cl_max_clean : float — CL_max in clean configuration (from #486 polar fit)
    rho          : float — air density [kg/m³]

    Returns
    -------
    W/S_max [N/m²]
    """
    return 0.5 * rho * v_s_target * v_s_target * cl_max_clean


# ===========================================================================
# Design-point from aircraft dict
# ===========================================================================


def _design_point_from_aircraft(aircraft: dict[str, Any]) -> dict[str, float]:
    """Derive the design point {ws_n_m2, t_w} from an aircraft parameter dict.

    Reads:
      - mass_kg, t_static_N  → T/W = T_static / W_MTOW
      - mass_kg, s_ref_m2    → W/S = W_MTOW / S  (if s_ref_m2 present)
      - OR directly ws_n_m2 if provided

    Falls back to (0, 0) when data is insufficient.
    """
    g = aircraft.get("g", _G)
    mass_kg: float = float(aircraft.get("mass_kg", 0.0))
    weight_n = mass_kg * g

    t_static = float(aircraft.get("t_static_N", 0.0))
    t_w = t_static / weight_n if weight_n > 0 else 0.0

    # W/S from geometry
    if "ws_n_m2" in aircraft:
        ws = float(aircraft["ws_n_m2"])
    elif "s_ref_m2" in aircraft and float(aircraft["s_ref_m2"]) > 0:
        ws = weight_n / float(aircraft["s_ref_m2"])
    else:
        ws = 0.0

    return {"ws_n_m2": round(ws, 2), "t_w": round(t_w, 5)}


# ===========================================================================
# Feasibility check
# ===========================================================================


def _check_feasibility(
    ws_dp: float,
    tw_dp: float,
    constraints: list[dict],
) -> tuple[str, list[dict]]:
    """Determine whether the design point is feasible and which constraints bind.

    A line constraint (t_w_points) is binding if the design point lies within
    a small tolerance of its upper-bound line.

    A vertical constraint (ws_max) is binding if ws_dp ≈ ws_max.

    Returns
    -------
    (feasibility_str, constraints_with_binding_set)
    """
    TOL_LINE = 0.03   # 3% T/W tolerance for "binding" line constraints
    TOL_VERT = 0.05   # 5% W/S tolerance for "binding" vertical constraints
    infeasible = False

    updated: list[dict] = []
    for c in constraints:
        binding = False
        if "t_w_points" in c and "ws_range" in c:
            ws_range = c["ws_range"]
            tw_pts = c["t_w_points"]
            # Interpolate constraint T/W at the design point W/S
            if ws_range and ws_dp >= ws_range[0] and ws_dp <= ws_range[-1]:
                idx = min(
                    range(len(ws_range)),
                    key=lambda i: abs(ws_range[i] - ws_dp),
                )
                tw_req = tw_pts[idx]
                if tw_dp < tw_req * (1.0 - TOL_LINE):
                    infeasible = True
                elif abs(tw_dp - tw_req) / max(tw_req, 1e-9) <= TOL_LINE:
                    binding = True
        elif "ws_max" in c:
            ws_max = c["ws_max"]
            if ws_max is not None and math.isfinite(ws_max):
                if ws_dp > ws_max * (1.0 + TOL_VERT):
                    infeasible = True
                elif abs(ws_dp - ws_max) / max(ws_max, 1e-9) <= TOL_VERT:
                    binding = True

        updated.append({**c, "binding": binding})

    feasibility = "infeasible_below_constraints" if infeasible else "feasible"
    return feasibility, updated


# ===========================================================================
# Main entry point
# ===========================================================================


def compute_chart(
    aircraft: dict[str, Any],
    mode: str = "uav_runway",
    *,
    s_runway: float | None = None,
    v_s_target: float | None = None,
    gamma_climb_deg: float | None = None,
    v_cruise_mps: float | None = None,
    rho: float = _RHO_SL,
) -> dict[str, Any]:
    """Compute the T/W vs W/S matching chart for an aircraft.

    Computes all constraint lines analytically — no numerical inverse of
    field_length_service.  Constants are imported directly from that service.

    Parameters
    ----------
    aircraft : dict
        Aircraft parameters.  Required keys:
          ``mass_kg``, ``t_static_N``, ``ar`` (or ``b_ref_m`` + ``s_ref_m2``),
          ``cd0``, ``e_oswald``, ``cl_max_clean``, ``cl_max_takeoff``,
          ``cl_max_landing``, ``v_cruise_mps``

        Optional (from assumption_computation_context):
          ``v_md_mps``, ``v_stall_mps``, ``s_ref_m2``, ``b_ref_m``

    mode : str
        One of ``rc_runway``, ``rc_hand_launch``, ``uav_runway``, ``uav_belly_land``.
        Sets default field-length, climb-gradient, and stall-speed targets.

    s_runway : float | None
        Override field length target [m] (to 50 ft for TO; from 50 ft for LDG).
    v_s_target : float | None
        Override max acceptable stall speed [m/s].
    gamma_climb_deg : float | None
        Override climb gradient target [°].
    v_cruise_mps : float | None
        Override cruise speed [m/s].
    rho : float
        Air density [kg/m³], default sea-level ISA.

    Returns
    -------
    dict with keys:
      ws_range_n_m2   : list[float]  — W/S sweep [N/m²]
      constraints     : list[dict]   — each has name, color, binding,
                                       and either t_w_points+ws_range or ws_max
      design_point    : dict         — {ws_n_m2, t_w}
      feasibility     : str          — "feasible" | "infeasible_below_constraints"
      warnings        : list[str]
    """
    warnings: list[str] = []
    defaults = _mode_defaults(mode)

    # --- Resolve parameters -------------------------------------------------
    s_rwy: float = s_runway if s_runway is not None else defaults["s_runway"]
    v_s: float = v_s_target if v_s_target is not None else defaults["v_s_target"]
    gamma: float = gamma_climb_deg if gamma_climb_deg is not None else defaults["gamma_climb_deg"]

    # Resolve cruise speed from aircraft dict or override
    if v_cruise_mps is not None:
        v_cruise = v_cruise_mps
    elif "v_cruise_mps" in aircraft and aircraft["v_cruise_mps"]:
        v_cruise = float(aircraft["v_cruise_mps"])
    elif "v_md_mps" in aircraft and aircraft["v_md_mps"]:
        v_cruise = float(aircraft["v_md_mps"])
    else:
        # Estimate cruise as V_md from polar parameters
        cd0 = float(aircraft.get("cd0", 0.03))
        e = float(aircraft.get("e_oswald", 0.8))
        ar = float(aircraft.get("ar", 7.0))
        # V_md at an approximate midpoint W/S = 500 N/m²
        v_cruise = _v_md(500.0, cd0=cd0, e=e, ar=ar, rho=rho)
        warnings.append(
            f"v_cruise_mps not specified — estimated from polar as {v_cruise:.1f} m/s. "
            "Set v_cruise_mps in aircraft dict for accurate cruise constraint."
        )

    # --- Extract polar parameters -------------------------------------------
    cd0: float = float(aircraft.get("cd0", 0.03))
    e: float = float(aircraft.get("e_oswald", aircraft.get("e", 0.8)))
    ar: float = float(aircraft.get("ar", aircraft.get("aspect_ratio", 7.0)))

    cl_max_clean: float = float(aircraft.get("cl_max_clean", aircraft.get("cl_max", 1.4)))
    cl_max_to: float = float(aircraft.get("cl_max_takeoff", cl_max_clean))
    cl_max_l: float = float(aircraft.get("cl_max_landing", cl_max_clean))

    # --- W/S sweep -----------------------------------------------------------
    ws_range = [
        _WS_MIN + (_WS_MAX - _WS_MIN) * i / (_WS_STEPS - 1)
        for i in range(_WS_STEPS)
    ]

    # --- Constraint lines ---------------------------------------------------

    # 1. Takeoff (line: T/W vs W/S)
    to_tw = [_takeoff_constraint(ws, s_rwy, cl_max_to, rho) for ws in ws_range]

    # 2. Landing (vertical: W/S_max)
    ws_ldg_max: float
    if mode == "uav_belly_land":
        ws_ldg_max = float("inf")  # belly-land → no landing distance constraint
    else:
        ws_ldg_max = _landing_constraint(s_rwy, cl_max_l, rho)

    # 3. Cruise (line: T/W vs W/S)
    cruise_tw = [_cruise_constraint(ws, v_cruise, cd0, e, ar, rho) for ws in ws_range]

    # 4. Climb (line: T/W vs W/S — climb speed varies per W/S for accuracy)
    climb_tw = [
        _climb_constraint(ws, gamma, _v_md(ws, cd0, e, ar, rho), cd0, e, ar, rho)
        for ws in ws_range
    ]

    # 5. Stall (vertical: W/S_max)
    ws_stall_max = _stall_constraint(v_s, cl_max_clean, rho)

    # --- Design point -------------------------------------------------------
    design_point = _design_point_from_aircraft(aircraft)

    # --- Pack constraints ---------------------------------------------------
    constraints_raw: list[dict] = [
        {
            "name": "Takeoff",
            "t_w_points": to_tw,
            "ws_range": ws_range,
            "color": _COLOR_TAKEOFF,
            "binding": False,
            "hover_text": (
                "Takeoff distance ≤ s_runway. "
                f"Loftin/Roskam §3.4: T/W = C_TO·k_TO·(W/S)/(ρ·g·CL_max_TO·s). "
                f"k_TO={_K_TO_50FT}, C_TO=1.21, s={s_rwy:.0f} m."
            ),
        },
        {
            "name": "Landing",
            "ws_max": ws_ldg_max if math.isfinite(ws_ldg_max) else None,
            "color": _COLOR_LANDING,
            "binding": False,
            "hover_text": (
                "Landing distance ≤ s_runway. "
                f"Roskam §3.4: W/S_max = s·ρ·CL_max_L/(K_LDG·K_LDG_50ft). "
                f"K_LDG={_K_LDG_HARD}, k_LDG_50ft={_K_LDG_50FT}, s={s_rwy:.0f} m."
            ),
        },
        {
            "name": "Cruise",
            "t_w_points": cruise_tw,
            "ws_range": ws_range,
            "color": _COLOR_CRUISE,
            "binding": False,
            "hover_text": (
                "Level cruise at V_cruise. "
                f"Anderson §6.7: T/W = q·CD0/(W/S) + (W/S)·k/q. "
                f"V_cruise={v_cruise:.1f} m/s, CD0={cd0:.4f}, e={e:.3f}, AR={ar:.2f}."
            ),
        },
        {
            "name": "Climb",
            "t_w_points": climb_tw,
            "ws_range": ws_range,
            "color": _COLOR_CLIMB,
            "binding": False,
            "hover_text": (
                f"Climb gradient γ={gamma:.1f}°. "
                "Anderson §6.3: T/W = sin(γ) + D/W (clean polar). "
                f"CD0={cd0:.4f}, e={e:.3f}, AR={ar:.2f}."
            ),
        },
        {
            "name": "Stall",
            "ws_max": ws_stall_max,
            "color": _COLOR_STALL,
            "binding": False,
            "hover_text": (
                f"Stall speed V_s ≤ {v_s:.1f} m/s (clean). "
                "Anderson §5.4: W/S_max = ½·ρ·V_s²·CL_max_clean. "
                f"CL_max_clean={cl_max_clean:.3f}."
            ),
        },
    ]

    # --- Feasibility + binding constraint detection -------------------------
    feasibility, constraints_final = _check_feasibility(
        ws_dp=design_point["ws_n_m2"],
        tw_dp=design_point["t_w"],
        constraints=constraints_raw,
    )

    logger.info(
        "Matching chart: mode=%s, W/S=%.1f N/m², T/W=%.4f, feasibility=%s",
        mode,
        design_point["ws_n_m2"],
        design_point["t_w"],
        feasibility,
    )

    return {
        "ws_range_n_m2": ws_range,
        "constraints": constraints_final,
        "design_point": design_point,
        "feasibility": feasibility,
        "warnings": warnings,
    }
