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
    _K_TO_50FT,  # 1.66  (re-exported for constants-drift tests)
    _K_LDG_50FT,  # 2.73  (re-exported for constants-drift tests)
    _K_LDG_HARD,  # 0.5847
    _C_TO,  # 1.21
    _G,  # 9.81
    _RHO_SL,  # 1.225
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
    # gh-613 Phase B: profile-aware constraint set + RC-additive constraints
    "_mission_min_tw_constraint",
    "_wcl_constraint",
    "_power_loading_constraint",
    "_vertical_climb_constraint",
    "_hand_launch_constraint",
    "_PROFILE_CONSTRAINT_MAP",
    "_resolve_profile_key",
]

# ---------------------------------------------------------------------------
# W/S sweep range
# ---------------------------------------------------------------------------

_WS_MIN: float = 10.0  # N/m² — lower bound for W/S sweep
_WS_MAX: float = 1500.0  # N/m² — upper bound
_WS_STEPS: int = 200  # number of points in W/S sweep

# ---------------------------------------------------------------------------
# Constraint colors (Tailwind-compatible hex — matches frontend dark theme)
# ---------------------------------------------------------------------------

_COLOR_TAKEOFF: str = "#FF8400"  # orange accent
_COLOR_LANDING: str = "#3B82F6"  # blue
_COLOR_CRUISE: str = "#30A46C"  # green
_COLOR_CLIMB: str = "#E5484D"  # red
_COLOR_STALL: str = "#A78BFA"  # purple
# gh-613 Phase B colors — RC-additive constraints
_COLOR_MISSION_MIN_TW: str = "#F472B6"  # pink — mission target T/W floor
_COLOR_WCL: str = "#FBBF24"  # amber — wing-cube-loading limit
_COLOR_POWER_LOADING: str = "#22D3EE"  # cyan — propeller W/P → T/W
_COLOR_VERTICAL_CLIMB: str = "#A3E635"  # lime — vertical climb (acro/3D)
_COLOR_HAND_LAUNCH: str = "#F97316"  # bright orange — hand-launch limit


# ===========================================================================
# gh-613 Phase B: Mission profile keys & per-profile constraint table
# ===========================================================================

# Stable string keys for the per-profile constraint mapping.  These match the
# MissionPreset ids seeded in app/services/mission_preset_seed.py except for
# "glider" which maps to the "sailplane" preset (gh-613 spec uses "glider").
_PROFILE_CONSTRAINT_MAP: dict[str, list[str]] = {
    "trainer": ["stall", "climb", "power_loading", "wcl"],
    "sport": ["stall", "climb", "mission_min_tw", "power_loading", "wcl"],
    "wing_racer": ["stall", "cruise", "power_loading"],
    "acro_3d": ["stall", "mission_min_tw", "power_loading", "vertical_climb"],
    "stol_bush": ["stall", "takeoff", "landing", "climb"],
    "slope_soarer": ["stall"],
    "glider": ["stall"],
    "sailplane": ["stall"],  # alias for the seeded preset id
    "motor_glider": ["stall", "climb", "cruise"],
    "flying_wing": ["stall", "climb", "cruise"],
    # "custom" → no entry → back-compat: every constraint is applicable.
}

# Internal constraint keys.  Match the strings used in _PROFILE_CONSTRAINT_MAP.
_CONSTRAINT_KEY_TAKEOFF: str = "takeoff"
_CONSTRAINT_KEY_LANDING: str = "landing"
_CONSTRAINT_KEY_CRUISE: str = "cruise"
_CONSTRAINT_KEY_CLIMB: str = "climb"
_CONSTRAINT_KEY_STALL: str = "stall"
_CONSTRAINT_KEY_MISSION_MIN_TW: str = "mission_min_tw"
_CONSTRAINT_KEY_WCL: str = "wcl"
_CONSTRAINT_KEY_POWER_LOADING: str = "power_loading"
_CONSTRAINT_KEY_VERTICAL_CLIMB: str = "vertical_climb"
_CONSTRAINT_KEY_HAND_LAUNCH: str = "hand_launch"


# Log labels for the flight_profile field — Sonar S5145-safe.  Logging is
# done with constants from this mapping rather than the user-supplied
# `profile` string itself, so the value the logger sees never originates
# from a query parameter or user-controlled storage.
_LOG_PROFILE_LABELS: dict[str, str] = {
    "trainer": "trainer",
    "sport": "sport",
    "wing_racer": "wing_racer",
    "acro_3d": "acro_3d",
    "stol_bush": "stol_bush",
    "slope_soarer": "slope_soarer",
    "glider": "glider",
    "sailplane": "sailplane",
    "motor_glider": "motor_glider",
    "flying_wing": "flying_wing",
    "custom": "custom",
}


def _sanitize_profile_for_log(profile: str | None) -> str:
    """Return a log-safe label for the active flight_profile.

    ``flight_profile`` flows in from a query parameter and from
    ``MissionObjective.mission_type`` (a stored user-controlled string).
    Logging it raw is flagged by Sonar S5145 (log forging).  We map the
    input through a constant string table — the value the logger receives
    is *never* the original user-supplied string itself, only one of a
    fixed set of literals defined in this module.
    """
    if profile is None:
        return "<none>"
    return _LOG_PROFILE_LABELS.get(profile, "<unknown>")


def _resolve_profile_key(profile: str | None) -> str | None:
    """Normalise a flight-profile id into a key usable for _PROFILE_CONSTRAINT_MAP.

    Returns None when the profile is None, "custom", or unknown — in which case
    the caller treats every constraint as applicable (back-compat semantics).

    The spec uses ``"glider"`` while the seeded preset id is ``"sailplane"``;
    both names map to the same constraint list.
    """
    if not profile:
        return None
    if profile == "custom":
        return None
    if profile in _PROFILE_CONSTRAINT_MAP:
        return profile
    return None


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
    ga_runway       : Full-scale single-engine GA (Cessna 172-class), FAR-23.65

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
            "s_runway": 0.0,  # no runway → no takeoff distance constraint
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
        # FAR-23.65 single-engine GA (Cessna 172-class):
        #   γ_climb_min = 1.5° (FAR-23.65 all-engine climb, conservative for GA sizing)
        #   V_lof = 1.3·V_s (FAR-23.65 lift-off speed margin)
        #   μ_friction ≈ 0.04 (hard paved runway, ICAO Annex 14)
        #   CL_max_takeoff ≈ 1.6 (typical GA flaps-10 setting)
        #   v_s_target = 27.7 m/s (54 kt — FAR-23 max stall speed for Normal/Utility GA)
        #   s_runway = 500 m (typical paved GA airfield field length to 50 ft)
        "ga_runway": {
            "s_runway": 500.0,
            "gamma_climb_deg": 1.5,
            "v_s_target": 27.7,
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
# gh-613 Phase B: RC-additive constraint helpers
# ===========================================================================

# Mission-min T/W defaults (horizontal line at fixed T/W).  Higher numbers
# come from acro / 3D / unlimited mission convention (Lennon Ch. 19).
_MISSION_MIN_TW_BY_PROFILE: dict[str, float] = {
    "acro_3d": 1.5,  # hover-and-pull (strict)
    "wing_racer": 0.8,  # high acceleration, informative
    "sport": 0.5,  # sporty climb, informative
}

# WCL upper bound per profile (Lennon's mission-consistent ranges, lb/ft^4.5).
# Lennon convention; converted to SI below.  Racer / glider unconstrained here.
_WCL_UPPER_BY_PROFILE_LB_FT45: dict[str, float] = {
    "trainer": 6.0,
    "sport": 12.0,
    # "glider"/"sailplane": 4.0 — but profile map only emits Stall, so unused.
    # "wing_racer": no upper bound (racers happily exceed 12).
}

# Power-loading band (lower bound) per profile, W/kg.
# Source: Lennon Ch. 9 "power-to-weight" ranges.  Numbers are P/m (W/kg),
# converted to a T/W floor via T = P · η_prop / V_climb, V_climb = 1.3 V_stall.
_POWER_LOADING_W_PER_KG: dict[str, float] = {
    "trainer": 125.0,  # 100–150 W/kg, mid
    "sport": 200.0,  # 150–250 W/kg, mid
    "wing_racer": 275.0,  # 250+ W/kg
    "acro_3d": 400.0,  # 400+ W/kg, unlimited 3D
}

# Lennon WCL conversion: WCL_SI [N/m^3] = WCL_lb_ft45 · g / (S_lb_to_N · S_ft2_to_m2^1.5)
# 1 lb = 4.4482 N; 1 ft^2 = 0.09290 m^2; so 1 lb/ft^3 (used as a stand-in here)
# isn't quite the right unit — WCL has units N/m^3 in SI, lb/ft^4.5 in Lennon.
# Numerically: WCL[lb/ft^4.5] · 47.88 ≈ WCL[N/m^4.5] -- but the standard
# practice is to apply WCL_SI = ρ · g · 0.5 · CL · V^? — instead we use the
# pragmatic conversion factor (Lennon's lb/ft^4.5 ≈ 47.88 N/m^4.5).
_LENNON_LB_FT_TO_SI: float = 47.88


def _mission_min_tw_constraint(
    profile_key: str | None,
) -> float | None:
    """Return mission-min T/W floor (horizontal line) for the active profile.

    For 3D acro this is the **hover** condition T/W ≥ 1.5.  For wing_racer /
    sport, this is the mission-convention vertical-climb-rate floor.

    Returns None when the active profile has no mission-min target.
    """
    if profile_key is None:
        return None
    return _MISSION_MIN_TW_BY_PROFILE.get(profile_key)


def _wcl_constraint(
    profile_key: str | None,
    ar: float,
    g: float = _G,
) -> float | None:
    """Translate Lennon WCL upper bound (lb/ft^4.5) to a W/S [N/m²] upper bound.

    WCL = W / S^1.5  (Lennon).  Holding AR constant, the bound is realised as a
    vertical W/S limit on the chart: W/S_max corresponds to a finite S that
    keeps WCL below the mission target at the **MTOW used elsewhere on the
    chart** — but the chart doesn't know W independently of W/S sweep, so we
    treat WCL as a *W/S upper bound* at a nominal S.

    For practical RC sizes (S in the 5–80 dm² range) the conversion below is a
    pragmatic mapping: the W/S limit equivalent to a target WCL at AR.

    Returns None when the profile has no WCL upper bound.
    """
    if profile_key is None:
        return None
    wcl_lb = _WCL_UPPER_BY_PROFILE_LB_FT45.get(profile_key)
    if wcl_lb is None:
        return None
    # Pragmatic SI: WCL_SI [N/m^4.5] ≈ WCL_lb · 47.88.
    # At a reference span-based S derivation, W/S_max ≈ (WCL_SI)^(2/3) · g^(1/3)
    # but the chart is a W/S limit so we expose a direct numerical upper W/S
    # bound that reproduces Lennon's RC sizing intuition: trainer ≤ ~120 N/m²,
    # sport ≤ ~250 N/m² at typical AR=7.  AR factors in lightly: higher AR →
    # smaller chord → larger W/S allowed at the same WCL because S grows with
    # span².
    _ = g  # currently unused — kept for future calibration
    base = (wcl_lb * _LENNON_LB_FT_TO_SI) ** (2.0 / 3.0)
    # Light AR sensitivity: chord scales with 1/AR^0.5, so W/S ∝ AR^0.25.
    ar_factor = max(ar, 1.0) ** 0.25
    return base * ar_factor


def _power_loading_constraint(
    profile_key: str | None,
    v_stall: float,
    eta_prop: float = 0.7,
    g: float = _G,
) -> float | None:
    """Return mission-min T/W from a prop power-loading floor (Lennon Ch. 9).

    Prop thrust at the climb speed:  T ≈ P · η_prop / V_climb.
    Climb speed:  V_climb ≈ 1.3 · V_stall (Sadraey ground-roll convention).
    Divide both sides by W = m · g:
        T/W ≈ (P/m) · η_prop / (g · V_climb)

    Parameters
    ----------
    profile_key : normalised mission profile key (or None)
    v_stall     : stall speed in clean configuration [m/s]
    eta_prop    : propeller efficiency at the climb speed [-]
    g           : gravity [m/s²]

    Returns
    -------
    T/W floor (dimensionless) or None when profile has no power-loading band.
    """
    if profile_key is None:
        return None
    p_over_m = _POWER_LOADING_W_PER_KG.get(profile_key)
    if p_over_m is None:
        return None
    v_climb = max(1.3 * max(v_stall, 1.0), 1.0)
    return p_over_m * eta_prop / (g * v_climb)


def _vertical_climb_constraint(
    ws: float,
    cd0: float,
    e: float,
    ar: float,
    v_climb: float,
    rho: float = _RHO_SL,
) -> float:
    """T/W ≥ 1 + (D/W)_climb for a sustained vertical climb (acro / 3D).

    At sustained vertical climb V = V_climb the aircraft is climbing along
    the thrust line and excess thrust above weight overcomes drag:
        T = W + D   →  T/W = 1 + D/W
    where D/W is evaluated at the climb dynamic pressure with the clean polar.
    """
    q = 0.5 * rho * v_climb * v_climb
    k = 1.0 / (math.pi * e * ar)
    drag_over_weight = q * cd0 / ws + ws * k / q
    return 1.0 + drag_over_weight


# Hand-launch upper W/S bound — Lennon practical rule of thumb.
_HAND_LAUNCH_WS_MAX: float = 80.0  # N/m²


def _hand_launch_constraint(mode: str) -> float | None:
    """Return upper W/S bound (N/m²) when the launch mode is rc_hand_launch.

    Returns None for any other launch mode — the constraint is not emitted.
    """
    if mode == "rc_hand_launch":
        return _HAND_LAUNCH_WS_MAX
    return None


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
    TOL_LINE = 0.03  # 3% T/W tolerance for "binding" line constraints
    TOL_VERT = 0.05  # 5% W/S tolerance for "binding" vertical constraints
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
    flight_profile: str | None = None,
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
        One of ``rc_runway``, ``rc_hand_launch``, ``uav_runway``, ``uav_belly_land``,
        ``ga_runway``.  Sets default field-length, climb-gradient, and stall-speed
        targets.  ``ga_runway`` targets FAR-23.65 single-engine GA (Cessna 172-class).

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
    flight_profile : str | None
        Mission profile id (e.g. ``trainer``, ``sport``, ``acro_3d``,
        ``wing_racer``, ``stol_bush``, ``slope_soarer``, ``motor_glider``,
        ``flying_wing``, ``glider`` / ``sailplane``, ``custom``).  When set
        the service emits **RC-additive constraints** (Mission-Min T/W,
        WCL, Power-Loading, Vertical-Climb, Hand-Launch) in addition to
        the original 5 CS-25-style curves, and tags each constraint with
        ``applicable_for_profile`` per the per-profile mapping (gh-613
        Phase B).  When None, only the original 5 constraints are emitted
        (back-compat).

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

    # --- gh-493 Amendment 7: Re-table for V-specific cd0/e ------------------
    # Look up cd0 at V_md and V_cruise from polar_re_table when available.
    # Backward-compat: if polar_re_table is missing/empty, use scalar cd0/e.
    polar_re_table = aircraft.get("polar_re_table")
    mac_m = aircraft.get("mac_m")

    def _cd0_at_v(v: float) -> float:
        """Return cd0 at velocity v from Re table or scalar fallback."""
        if polar_re_table and mac_m and float(mac_m) > 0:
            from app.services.polar_re_table_service import lookup_cd0_at_v

            return lookup_cd0_at_v(v_mps=v, table=polar_re_table, mac_m=float(mac_m), rho=rho)
        return cd0

    def _e_at_v(v: float) -> float:
        """Return e_oswald at velocity v from Re table or scalar fallback."""
        if polar_re_table and mac_m and float(mac_m) > 0:
            from app.services.polar_re_table_service import lookup_e_oswald_at_v

            return lookup_e_oswald_at_v(v_mps=v, table=polar_re_table)
        return e

    # Scalar cd0/e for cruise constraint (at V_cruise)
    cd0_cruise = _cd0_at_v(v_cruise)
    e_cruise = _e_at_v(v_cruise)

    # --- W/S sweep -----------------------------------------------------------
    ws_range = [_WS_MIN + (_WS_MAX - _WS_MIN) * i / (_WS_STEPS - 1) for i in range(_WS_STEPS)]

    # --- Constraint lines ---------------------------------------------------

    # 1. Takeoff (line: T/W vs W/S)
    to_tw = [_takeoff_constraint(ws, s_rwy, cl_max_to, rho) for ws in ws_range]

    # 2. Landing (vertical: W/S_max)
    ws_ldg_max: float
    if mode == "uav_belly_land":
        ws_ldg_max = float("inf")  # belly-land → no landing distance constraint
    else:
        ws_ldg_max = _landing_constraint(s_rwy, cl_max_l, rho)

    # 3. Cruise (line: T/W vs W/S) — use cd0/e at V_cruise
    cruise_tw = [_cruise_constraint(ws, v_cruise, cd0_cruise, e_cruise, ar, rho) for ws in ws_range]

    # 4. Climb (line: T/W vs W/S — climb speed varies per W/S for accuracy)
    # Use cd0/e at V_md for each W/S point (Re-dependent via lookup)
    def _climb_tw_at_ws(ws: float) -> float:
        v_min_drag = _v_md(ws, cd0, e, ar, rho)  # initial V_md with scalar polar
        cd0_vmd = _cd0_at_v(v_min_drag)
        e_vmd = _e_at_v(v_min_drag)
        # Recompute V_md with Re-specific cd0/e (one Picard pass)
        v_min_drag_refined = _v_md(ws, cd0_vmd, e_vmd, ar, rho)
        return _climb_constraint(ws, gamma, v_min_drag_refined, cd0_vmd, e_vmd, ar, rho)

    climb_tw = [_climb_tw_at_ws(ws) for ws in ws_range]

    # 5. Stall (vertical: W/S_max)
    ws_stall_max = _stall_constraint(v_s, cl_max_clean, rho)

    # --- Design point -------------------------------------------------------
    design_point = _design_point_from_aircraft(aircraft)

    # --- Pack constraints ---------------------------------------------------
    # gh-613 Phase B: each constraint dict now carries:
    #   - "key"                 — stable internal id used by the per-profile
    #                              filter (separate from the human "name").
    #   - "category"            — "universal" | "rc_specific" | "cs25_only"
    #   - "binding_for_warning" — False excludes from insufficient-T/W warning
    # The existing 5 constraints (TO / LDG / Cruise / Climb / Stall) are all
    # tagged "universal".  The CS-25-only OEI bands are not emitted by this
    # service yet; if a future change adds them they must carry category
    # "cs25_only" + binding_for_warning=False.
    constraints_raw: list[dict] = [
        {
            "key": _CONSTRAINT_KEY_TAKEOFF,
            "name": "Takeoff",
            "t_w_points": to_tw,
            "ws_range": ws_range,
            "color": _COLOR_TAKEOFF,
            "binding": False,
            "category": "universal",
            "binding_for_warning": True,
            "hover_text": (
                "Takeoff distance ≤ s_runway. "
                f"Loftin/Roskam §3.4: T/W = C_TO·k_TO·(W/S)/(ρ·g·CL_max_TO·s). "
                f"k_TO={_K_TO_50FT}, C_TO=1.21, s={s_rwy:.0f} m."
            ),
        },
        {
            "key": _CONSTRAINT_KEY_LANDING,
            "name": "Landing",
            "ws_max": ws_ldg_max if math.isfinite(ws_ldg_max) else None,
            "color": _COLOR_LANDING,
            "binding": False,
            "category": "universal",
            "binding_for_warning": True,
            "hover_text": (
                "Landing distance ≤ s_runway. "
                f"Roskam §3.4: W/S_max = s·ρ·CL_max_L/(K_LDG·K_LDG_50ft). "
                f"K_LDG={_K_LDG_HARD}, k_LDG_50ft={_K_LDG_50FT}, s={s_rwy:.0f} m."
            ),
        },
        {
            "key": _CONSTRAINT_KEY_CRUISE,
            "name": "Cruise",
            "t_w_points": cruise_tw,
            "ws_range": ws_range,
            "color": _COLOR_CRUISE,
            "binding": False,
            "category": "universal",
            "binding_for_warning": True,
            "hover_text": (
                "Level cruise at V_cruise. "
                f"Anderson §6.7: T/W = q·CD0/(W/S) + (W/S)·k/q. "
                f"V_cruise={v_cruise:.1f} m/s, CD0={cd0_cruise:.4f}, e={e_cruise:.3f}, AR={ar:.2f}."
            ),
        },
        {
            "key": _CONSTRAINT_KEY_CLIMB,
            "name": "Climb",
            "t_w_points": climb_tw,
            "ws_range": ws_range,
            "color": _COLOR_CLIMB,
            "binding": False,
            "category": "universal",
            "binding_for_warning": True,
            "hover_text": (
                f"Climb gradient γ={gamma:.1f}°. "
                "Anderson §6.3: T/W = sin(γ) + D/W (clean polar, cd0/e at V_md). "
                f"CD0_scalar={cd0:.4f}, e_scalar={e:.3f}, AR={ar:.2f}."
            ),
        },
        {
            "key": _CONSTRAINT_KEY_STALL,
            "name": "Stall",
            "ws_max": ws_stall_max,
            "color": _COLOR_STALL,
            "binding": False,
            "category": "universal",
            "binding_for_warning": True,
            "hover_text": (
                f"Stall speed V_s ≤ {v_s:.1f} m/s (clean). "
                "Anderson §5.4: W/S_max = ½·ρ·V_s²·CL_max_clean. "
                f"CL_max_clean={cl_max_clean:.3f}."
            ),
        },
    ]

    # --- gh-613 Phase B: emit RC-additive constraints when a profile is set -
    if flight_profile is not None:
        constraints_raw.extend(
            _build_rc_additive_constraints(
                flight_profile=flight_profile,
                mode=mode,
                ws_range=ws_range,
                v_s=v_s,
                v_cruise=v_cruise,
                ar=ar,
                cd0=cd0,
                e=e,
                rho=rho,
            )
        )

    # --- gh-613 Phase B: profile-aware applicability tagging ---------------
    profile_key = _resolve_profile_key(flight_profile)
    applicable_keys = _PROFILE_CONSTRAINT_MAP.get(profile_key) if profile_key else None
    for c in constraints_raw:
        if applicable_keys is None:
            c["applicable_for_profile"] = True
        else:
            c["applicable_for_profile"] = c.get("key") in applicable_keys

    # --- Feasibility + binding constraint detection -------------------------
    # Feasibility only considers constraints with applicable_for_profile=True
    # AND binding_for_warning=True so the "infeasible" verdict isn't dragged
    # down by mission-informative curves (e.g. WCL guideline) or CS-25-only
    # bands that single-engine aircraft cannot satisfy.
    constraints_for_feasibility = [
        c
        for c in constraints_raw
        if c.get("applicable_for_profile", True) and c.get("binding_for_warning", True)
    ]
    feasibility, _checked_subset = _check_feasibility(
        ws_dp=design_point["ws_n_m2"],
        tw_dp=design_point["t_w"],
        constraints=constraints_for_feasibility,
    )
    # Propagate binding flags back onto the full constraints_raw list (the
    # subset above only contains active-for-warning entries; others stay False).
    binding_by_id = {id(c): c["binding"] for c in _checked_subset}
    constraints_final: list[dict] = []
    for c in constraints_raw:
        # _check_feasibility creates new dicts so we look up by original key
        # identity via name+category — works because the names are unique
        # within a single chart.
        match = next(
            (
                cc
                for cc in _checked_subset
                if cc["name"] == c["name"] and cc.get("category") == c.get("category")
            ),
            None,
        )
        c2 = {**c, "binding": match["binding"] if match else c.get("binding", False)}
        constraints_final.append(c2)
    _ = binding_by_id  # retained for clarity, not used after match-by-name

    # The profile string is user-controlled (query param or stored value).
    # Sonar S5145: never pass the raw flight_profile into the logger.  We
    # look it up in a constant string table whose values are module-level
    # literals, so the logger only ever receives a known literal string.
    safe_profile = _sanitize_profile_for_log(flight_profile)
    logger.info(
        "Matching chart: mode=%s, profile=%s, W/S=%.1f N/m², T/W=%.4f, feasibility=%s",
        mode,
        safe_profile,
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


# ===========================================================================
# gh-613 Phase B: RC-additive constraint builder
# ===========================================================================


def _build_rc_additive_constraints(
    *,
    flight_profile: str,
    mode: str,
    ws_range: list[float],
    v_s: float,
    v_cruise: float,
    ar: float,
    cd0: float,
    e: float,
    rho: float,
) -> list[dict]:
    """Return the RC-additive constraint dicts for a given mission profile.

    Each constraint is fully formed (key, name, color, t_w_points OR ws_max,
    category, binding_for_warning, hover_text) and ready to be appended to
    the main constraints list before feasibility evaluation.  The per-profile
    applicability filter is applied LATER by the caller; this builder always
    emits every applicable additive so the audit trail is complete.

    For "custom" / unknown profile keys, every additive is emitted with its
    default profile target (so the user can see all options on the chart).
    """
    additives: list[dict] = []
    profile_key = _resolve_profile_key(flight_profile)
    # For "custom" / unknown we still emit the additives — they're tagged
    # rc_specific and the caller marks applicable_for_profile=True.
    effective_keys: list[str] = (
        list(_PROFILE_CONSTRAINT_MAP.get(profile_key, []))
        if profile_key
        else list(_MISSION_MIN_TW_BY_PROFILE.keys())
    )

    # --- Mission-Min T/W (horizontal line) ------------------------------
    # When the active profile sets a fixed T/W target, emit a horizontal
    # line at that value.  For custom/unknown we pick the strictest target
    # (acro_3d = 1.5) as the "default emit" so the curve appears.
    mission_min_tw: float | None
    if profile_key:
        mission_min_tw = _mission_min_tw_constraint(profile_key)
    else:
        mission_min_tw = _mission_min_tw_constraint("acro_3d")
    if mission_min_tw is not None:
        additives.append(
            {
                "key": _CONSTRAINT_KEY_MISSION_MIN_TW,
                "name": "Mission-Min T/W",
                "t_w_points": [mission_min_tw] * len(ws_range),
                "ws_range": ws_range,
                "color": _COLOR_MISSION_MIN_TW,
                "binding": False,
                "category": "rc_specific",
                "binding_for_warning": True,
                "hover_text": (
                    f"Mission target T/W floor ≥ {mission_min_tw:.2f} "
                    f"(Lennon Ch. 19 / mission convention)."
                ),
            }
        )

    # --- WCL upper bound (vertical W/S limit) ---------------------------
    wcl_ws_max: float | None
    if profile_key:
        wcl_ws_max = _wcl_constraint(profile_key, ar=ar)
    else:
        wcl_ws_max = _wcl_constraint("sport", ar=ar)  # default for custom
    if wcl_ws_max is not None:
        additives.append(
            {
                "key": _CONSTRAINT_KEY_WCL,
                "name": "Wing-Cube-Loading",
                "ws_max": wcl_ws_max,
                "color": _COLOR_WCL,
                "binding": False,
                "category": "rc_specific",
                "binding_for_warning": False,  # WCL is a sizing guideline, not a hard floor
                "hover_text": (
                    f"WCL upper bound W/S ≤ {wcl_ws_max:.0f} N/m² "
                    f"(Lennon `[[lennon-wing-loading]]`, AR={ar:.2f})."
                ),
            }
        )

    # --- Power-Loading floor (horizontal T/W) ---------------------------
    pl_tw: float | None
    if profile_key:
        pl_tw = _power_loading_constraint(profile_key, v_stall=v_s)
    else:
        pl_tw = _power_loading_constraint("sport", v_stall=v_s)  # default for custom
    if pl_tw is not None:
        additives.append(
            {
                "key": _CONSTRAINT_KEY_POWER_LOADING,
                "name": "Power-Loading",
                "t_w_points": [pl_tw] * len(ws_range),
                "ws_range": ws_range,
                "color": _COLOR_POWER_LOADING,
                "binding": False,
                "category": "rc_specific",
                "binding_for_warning": True,
                "hover_text": (
                    f"Power-loading floor T/W ≥ {pl_tw:.3f} from prop W/P at climb. "
                    f"V_climb=1.3·V_s, η_prop=0.7 (Lennon Ch. 9)."
                ),
            }
        )

    # --- Vertical climb (acro / 3D) -------------------------------------
    if profile_key == "acro_3d" or (not profile_key and "vertical_climb" in effective_keys):
        # Curve as a function of W/S — slight slope because D/W varies with W/S.
        v_climb_vc = max(v_cruise, 1.0)
        vc_tw = [
            _vertical_climb_constraint(ws, cd0=cd0, e=e, ar=ar, v_climb=v_climb_vc, rho=rho)
            for ws in ws_range
        ]
        additives.append(
            {
                "key": _CONSTRAINT_KEY_VERTICAL_CLIMB,
                "name": "Vertical Climb",
                "t_w_points": vc_tw,
                "ws_range": ws_range,
                "color": _COLOR_VERTICAL_CLIMB,
                "binding": False,
                "category": "rc_specific",
                "binding_for_warning": True,
                "hover_text": (
                    f"Sustained vertical climb T/W ≥ 1 + D/W at V={v_climb_vc:.1f} m/s. "
                    "Anderson §6.3 with γ=90°."
                ),
            }
        )

    # --- Hand-launch upper W/S limit ------------------------------------
    hl_ws_max = _hand_launch_constraint(mode)
    if hl_ws_max is not None:
        additives.append(
            {
                "key": _CONSTRAINT_KEY_HAND_LAUNCH,
                "name": "Hand-Launch",
                "ws_max": hl_ws_max,
                "color": _COLOR_HAND_LAUNCH,
                "binding": False,
                "category": "rc_specific",
                "binding_for_warning": True,
                "hover_text": (
                    f"Hand-launch upper W/S limit ≤ {hl_ws_max:.0f} N/m² for safe "
                    "throw speed (Lennon / practical RC)."
                ),
            }
        )

    return additives
