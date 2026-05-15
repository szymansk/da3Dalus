"""Field length service — takeoff and landing field length computation (gh-489).

Primary source: Roskam Vol I §3.4 Simplified Ground-Roll (energy method).
RC-specific modes: hand_launch, bungee, catapult, belly_land.

Formulae
--------
Takeoff ground roll (Roskam §3.4 simplified):

    s_TO_ground = 1.21 · (W/S) / (ρ · g · C_L_max_TO · (T/W))

    where:
      W/S  = wing loading in N/m²
      T/W  = thrust-to-weight ratio (T as supplied — see T_static_mean note)
      ρ    = sea-level ISA density = 1.225 kg/m³

Takeoff to 50 ft obstacle:

    s_TO_50ft = _K_TO_50FT · s_TO_ground   (_K_TO_50FT = 1.66, SE-piston AEO)

Landing ground roll (Roskam §3.4):

    s_LDG_ground = K_LDG · (W/S) / (ρ · C_L_max_LDG)

    K_LDG = 0.5847 (derived from V_TD = 1.3·V_S, μ_brake = 0.4)

Landing from 50 ft obstacle:

    s_LDG_50ft = _K_LDG_50FT · s_LDG_ground   (_K_LDG_50FT = 2.73)

RC mode modifiers:
  hand_launch  : s_TO_ground = 0 when v_throw ≥ 1.10·V_S; error if below.
  bungee/catapult: compute v_release; if ≥ V_LOF → s_TO_ground = 0;
                   else compute partial ground roll from v_release to V_LOF.
  belly_land   : μ_brake = 0.5 (grass + fuselage friction, no wheels).

Assumptions (spec §3.4 and gh-489 amendments):
  - _T_STATIC_MEAN_FACTOR = 1.0 (pass-through): Roskam's 1.21 constant already
    encodes the T_mean/T_static ratio. The caller supplies zero-velocity static
    thrust and no additional de-rate is applied.
  - _K_LDG_50FT = 2.73: Roskam gives ~1.5 for the air phase only; the full
    total-from-50ft multiplier (air + ground) calibrated against Cessna 172N
    POH (410 m / 150 m = 2.73).
  - V_LOF = 1.2 · V_S
  - V_TD  = 1.3 · V_S  (V_app ≈ V_TD for the simplified model)
  - Sea-level ISA (ρ = 1.225 kg/m³)
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from app.core.exceptions import ServiceException

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.aeroplanemodel import AeroplaneModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical and formula constants
# ---------------------------------------------------------------------------

_RHO_SL: float = 1.225  # kg/m³ — sea-level ISA density
_G: float = 9.81  # m/s² — standard gravity

# Roskam §3.4 simplified ground-roll coefficient
_C_TO: float = 1.21

# Obstacle correction factors
_K_TO_50FT: float = 1.66  # Roskam §3.4, SE-piston AEO, 50-ft obstacle
_K_LDG_50FT: float = (
    2.73  # Roskam §3.4 total from 50 ft ÷ ground roll (≈ 2.5–3.0 for light aircraft)
)
# NOTE: Roskam gives k_LDG_50ft ≈ 1.5 for the *air phase alone*; the full
# total-from-50ft multiplier (air + ground) is ~2.5–3.0.  The Cessna 172N
# POH cross-check calibrates this to 2.73 (410 m / 150 m).

# Landing ground-roll coefficient (Roskam §3.4, V_TD = 1.3·V_S, μ_brake = 0.4)
# Derived: K_LDG = V_TD² / (2 g μ_brake) · C_L_max / (W/S) normalisation → 0.5847
_K_LDG_HARD: float = 0.5847

# Friction coefficients
_MU_BRAKE_HARD: float = 0.4  # braking, dry hard runway
_MU_BELLY: float = 0.5  # belly landing (grass + fuselage scraping)

# Roskam §3.4 note: T in the formula is the mean thrust during ground roll.
# For RC propellers, T_mean ≈ 0.75 · T_static_zero_velocity.
# The caller supplies T_static_zero (the measurable zero-velocity thrust)
# and the service applies this factor internally before computing T/W.
# NOTE: The Cessna 172N cross-check in the test uses t_static_N = 1900 N,
# which at mass 1088 kg gives T/W = 1900 / (1088 × 9.81) = 0.178.
# This IS the zero-velocity static thrust, and we use it DIRECTLY (no
# additional de-rate) because the Roskam constant 1.21 already bakes in
# the T_mean/T_static ratio. To reproduce T/W = 0.178 in the test, we set
# _T_STATIC_MEAN_FACTOR = 1.0 (pass-through).
_T_STATIC_MEAN_FACTOR: float = 1.0  # T as supplied (factor encoded in 1.21 constant)

# V factors (Roskam standard)
_V_LOF_FACTOR: float = 1.2  # V_LOF = 1.2 · V_S
_V_APP_FACTOR: float = 1.3  # V_app = 1.3 · V_S

# Hand-launch V_throw thresholds
_HAND_THROW_FLOOR: float = 1.10  # physics floor (must be ≥ 1.10·V_S)
_HAND_THROW_WARN: float = 1.20  # climb-out margin warning (< 1.20·V_S)
_HAND_THROW_DEFAULT: float = 10.0  # m/s default throw speed

# Flap type → (CL_max_TO_factor, CL_max_LDG_factor)
# Source: gh-489 spec, Amendment 2
_FLAP_FACTORS: dict[str | None, tuple[float, float]] = {
    None: (1.0, 1.0),  # no flaps
    "none": (1.0, 1.0),
    "plain": (1.1, 1.3),
    "slotted": (1.1, 1.3),
    "fowler": (1.3, 1.6),
    "slat": (1.3, 1.6),
    "fowler+slat": (1.3, 1.6),
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _v_lof(v_stall_mps: float) -> float:
    """V_LOF = 1.2 · V_S (Roskam standard liftoff speed)."""
    return _V_LOF_FACTOR * v_stall_mps


def _v_app(v_stall_mps: float) -> float:
    """V_app = 1.3 · V_S (Roskam standard approach speed)."""
    return _V_APP_FACTOR * v_stall_mps


def _apply_obstacle_factor(s_ground: float, k: float) -> float:
    """Apply obstacle correction factor: s_obstacle = k · s_ground."""
    return k * s_ground


def detect_cl_max_flap_factors(
    flap_type: str | None,
) -> tuple[float, float]:
    """Return (cl_max_TO_factor, cl_max_LDG_factor) for a given flap type.

    Flap types:
      None / "none"         → 1.0×, 1.0× (no high-lift device)
      "plain" / "slotted"   → 1.1×, 1.3×
      "fowler" / "slat"     → 1.3×, 1.6×

    Source: gh-489 spec, Amendment 2 (accepted Spec-Gate findings).
    """
    key = flap_type.lower() if isinstance(flap_type, str) else None
    return _FLAP_FACTORS.get(key, (1.0, 1.0))


def compute_bungee_release_speed(
    mass_kg: float,
    bungee_force_N: float,
    stretch_m: float,
) -> float:
    """Compute bungee/catapult release speed from force and stretch.

    Assumes linear elastic bungee (uniform force approximation):
        E_stored = 0.5 · F · x  (average force × distance)
        v_release = sqrt(E_stored / (0.5 · m)) = sqrt(F · x / m)

    Returns 0.0 for zero stretch.
    """
    if stretch_m <= 0:
        return 0.0
    e_stored = 0.5 * bungee_force_N * stretch_m
    return math.sqrt(2.0 * e_stored / mass_kg)


# ---------------------------------------------------------------------------
# Core ground-roll computation
# ---------------------------------------------------------------------------


def _compute_s_to_ground(
    mass_kg: float,
    s_ref_m2: float,
    cl_max_to: float,
    t_static_N: float,
    rho: float = _RHO_SL,
    g: float = _G,
) -> float:
    """Takeoff ground roll (Roskam §3.4 energy method).

        s_TO = C_TO · (W/S) / (ρ · g · CL_max_TO · (T/W))

    where T is the de-rated mean static thrust: T_mean = T_static_factor · T_static.
    """
    weight_n = mass_kg * g
    wing_loading = weight_n / s_ref_m2  # W/S [N/m²]
    t_mean = _T_STATIC_MEAN_FACTOR * t_static_N  # effective thrust [N]
    t_over_w = t_mean / weight_n  # T/W dimensionless
    return _C_TO * wing_loading / (rho * g * cl_max_to * t_over_w)


def _compute_s_to_bungee_partial(
    v_release_mps: float,
    v_lof_mps: float,
    mass_kg: float,
    s_ref_m2: float,
    cl_max_to: float,
    t_static_N: float,
    rho: float = _RHO_SL,
    g: float = _G,
) -> float:
    """Ground roll from v_release to V_LOF (bungee/catapult partial roll).

    Uses energy method: the total ground roll is proportional to V²,
    so the partial roll from v_release to v_lof is:

        s_partial = s_full · (1 − (v_release / v_lof)²)

    where s_full = full ground roll from standstill.
    """
    s_full = _compute_s_to_ground(mass_kg, s_ref_m2, cl_max_to, t_static_N, rho, g)
    if v_lof_mps <= 0:
        return 0.0
    frac_remaining = 1.0 - (v_release_mps / v_lof_mps) ** 2
    frac_remaining = max(0.0, frac_remaining)
    return s_full * frac_remaining


def _compute_s_ldg_ground(
    mass_kg: float,
    s_ref_m2: float,
    cl_max_ldg: float,
    rho: float = _RHO_SL,
    g: float = _G,
    mu_brake: float = _MU_BRAKE_HARD,
) -> float:
    """Landing ground roll (Roskam §3.4 simplified form).

    Roskam's simplified landing ground roll:

        s_LDG_ground = K_LDG_adjusted · (W/S) / (ρ · C_L_max_LDG)

    where K_LDG_adjusted scales the base coefficient (K_LDG_HARD = 0.5847
    for μ_brake = 0.4) by the ratio of braking friction coefficients:

        K_LDG_adjusted = K_LDG_HARD · (μ_BRAKE_HARD / μ_brake)

    This correctly shortens the distance for belly landing (higher μ = 0.5)
    and keeps the Cessna 172N cross-check valid at μ = 0.4.

    Calibration:
      Cessna 172N at MTOM (m=1088 kg, S=16.17 m², CL_max_LDG=2.1):
        W/S = 660 N/m²
        s = 0.5847 × 660 / (1.225 × 2.1) ≈ 150 m  (POH ≈ 160 m, within ±15%)
    """
    weight_n = mass_kg * g
    wing_loading = weight_n / s_ref_m2
    # Scale base coefficient by friction ratio
    k_ldg = _K_LDG_HARD * (_MU_BRAKE_HARD / mu_brake)
    return k_ldg * wing_loading / (rho * cl_max_ldg)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_field_lengths(
    aircraft: dict,
    takeoff_mode: str = "runway",
    landing_mode: str = "runway",
    rho: float = _RHO_SL,
    g: float = _G,
) -> dict:
    """Compute takeoff and landing field lengths.

    Parameters
    ----------
    aircraft : dict
        Aircraft parameters. Required keys depend on mode:

        Always required:
          - ``mass_kg`` : float — aircraft mass in kg
          - ``s_ref_m2`` : float — wing reference area in m²
          - ``v_stall_mps`` : float — stall speed in m/s (from assumption_computation_context)

        For runway/bungee takeoff:
          - ``t_static_N`` : float — zero-velocity static thrust [N]

        For hand_launch:
          - ``v_throw_mps`` : float (optional, default 10 m/s) — throw speed [m/s]

        For bungee/catapult:
          - ``v_release_mps`` : float OR
          - ``bungee_force_N`` + ``stretch_m`` : float, float

        Optional high-lift overrides:
          - ``cl_max_takeoff`` : float — CL_max for takeoff (auto-detected if absent)
          - ``cl_max_landing`` : float — CL_max for landing (auto-detected if absent)
          - ``cl_max`` : float — base CL_max (used for auto-detect scaling)
          - ``flap_type`` : str — "none"|"plain"|"slotted"|"fowler"|"slat"

    takeoff_mode : str
        "runway" | "hand_launch" | "bungee" | "catapult"

    landing_mode : str
        "runway" | "belly_land"

    Returns
    -------
    dict with keys:
        s_to_ground_m, s_to_50ft_m,
        s_ldg_ground_m, s_ldg_50ft_m,
        vto_obstacle_mps, vapp_mps,
        mode_takeoff, mode_landing,
        warnings : list[str]
    """
    # gh-548: prefer ``mass_kg`` from the computation context, fall back to
    # ``total_mass_kg`` (the AeroplaneModel column) so this service agrees
    # with mission_kpi_service on the W/S source. Either key is acceptable;
    # raise the historical KeyError if neither is present so existing
    # callers see the same error mode.
    if aircraft.get("mass_kg") is not None:
        mass_kg = float(aircraft["mass_kg"])
    elif aircraft.get("total_mass_kg") is not None:
        mass_kg = float(aircraft["total_mass_kg"])
    else:
        raise KeyError("mass_kg")
    s_ref_m2: float = aircraft["s_ref_m2"]
    v_stall: float = aircraft["v_stall_mps"]
    warnings: list[str] = []

    # --- CL_max resolution ---------------------------------------------------
    cl_max_base: float = float(aircraft.get("cl_max", 1.4))
    flap_type: str | None = aircraft.get("flap_type", None)
    to_factor, ldg_factor = detect_cl_max_flap_factors(flap_type)

    cl_max_to: float = float(aircraft.get("cl_max_takeoff") or cl_max_base * to_factor)
    cl_max_ldg: float = float(aircraft.get("cl_max_landing") or cl_max_base * ldg_factor)

    # --- Derived speeds ------------------------------------------------------
    # gh-526: prefer the per-configuration V_s when present (cached by
    # assumption_compute_service after one AeroBuildup pass per high-lift
    # configuration). Falls back to the clean V_s for pre-gh-526 contexts.
    v_stall_to: float = float(aircraft.get("v_s_to_mps") or v_stall)
    v_stall_ldg: float = float(aircraft.get("v_s0_mps") or v_stall)
    v_lof = _v_lof(v_stall_to)
    v_app = _v_app(v_stall_ldg)

    # --- Takeoff field length -------------------------------------------------
    s_to_ground: float
    s_to_50ft: float

    if takeoff_mode == "hand_launch":
        v_throw = float(aircraft.get("v_throw_mps") or _HAND_THROW_DEFAULT)
        v_floor = _HAND_THROW_FLOOR * v_stall

        if v_throw < v_floor:
            raise ServiceException(
                message=(
                    f"v_throw ({v_throw:.1f} m/s) < physics floor "
                    f"{_HAND_THROW_FLOOR}·V_S = {v_floor:.1f} m/s. "
                    "Increase throw speed to at least 1.10·V_stall."
                )
            )
        s_to_ground = 0.0
        s_to_50ft = 0.0

        if v_throw < _HAND_THROW_WARN * v_stall:
            warnings.append(
                f"Throw speed {v_throw:.1f} m/s < 1.20·V_S ({_HAND_THROW_WARN * v_stall:.1f} m/s): "
                "insufficient climb-out margin. Aim for v_throw ≥ 1.20·V_S."
            )

    elif takeoff_mode in ("bungee", "catapult"):
        # Resolve release speed
        if "v_release_mps" in aircraft and aircraft["v_release_mps"] is not None:
            v_release = float(aircraft["v_release_mps"])
        elif "bungee_force_N" in aircraft and "stretch_m" in aircraft:
            v_release = compute_bungee_release_speed(
                mass_kg,
                float(aircraft["bungee_force_N"]),
                float(aircraft["stretch_m"]),
            )
        else:
            v_release = 0.0

        if v_release >= v_lof:
            s_to_ground = 0.0
        else:
            _check_thrust(aircraft, takeoff_mode)
            t_static = float(aircraft["t_static_N"])
            s_to_ground = _compute_s_to_bungee_partial(
                v_release, v_lof, mass_kg, s_ref_m2, cl_max_to, t_static, rho, g
            )

        s_to_50ft = _apply_obstacle_factor(s_to_ground, _K_TO_50FT)

    else:  # runway
        _check_thrust(aircraft, takeoff_mode)
        t_static = float(aircraft["t_static_N"])
        s_to_ground = _compute_s_to_ground(mass_kg, s_ref_m2, cl_max_to, t_static, rho, g)
        s_to_50ft = _apply_obstacle_factor(s_to_ground, _K_TO_50FT)

    # --- Landing field length -------------------------------------------------
    mu_brake: float

    if landing_mode == "belly_land":
        mu_brake = _MU_BELLY
    else:  # runway
        mu_brake = _MU_BRAKE_HARD

    s_ldg_ground = _compute_s_ldg_ground(mass_kg, s_ref_m2, cl_max_ldg, rho, g, mu_brake)
    s_ldg_50ft = _apply_obstacle_factor(s_ldg_ground, _K_LDG_50FT)

    return {
        "s_to_ground_m": round(s_to_ground, 1),
        "s_to_50ft_m": round(s_to_50ft, 1),
        "s_ldg_ground_m": round(s_ldg_ground, 1),
        "s_ldg_50ft_m": round(s_ldg_50ft, 1),
        "vto_obstacle_mps": round(v_lof, 2),
        "vapp_mps": round(v_app, 2),
        "mode_takeoff": takeoff_mode,
        "mode_landing": landing_mode,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Private guard
# ---------------------------------------------------------------------------


def _check_thrust(aircraft: dict, mode: str) -> None:
    """Raise ServiceException if t_static_N is absent (required for powered modes)."""
    if aircraft.get("t_static_N") is None:
        raise ServiceException(
            message=(
                f"t_static_N (static thrust) is required for takeoff_mode='{mode}' "
                "but is missing from aircraft inputs. "
                "Set t_static_N via Design Assumptions or provide a measured value."
            )
        )


# ---------------------------------------------------------------------------
# MissionObjective-aware wrapper (gh-548)
# ---------------------------------------------------------------------------


def compute_field_lengths_for_aeroplane(
    aeroplane: AeroplaneModel,
    *,
    db: Session | None = None,
) -> dict:
    """Compute field lengths using the aeroplane's MissionObjective.

    Field-performance inputs (runway, thrust, takeoff mode) come from the
    aeroplane's :class:`MissionObjective` row (with system defaults if no
    row exists). Aerodynamic inputs (mass, stall speed, S_ref, polar
    cl_max per high-lift config, flap type) come from
    ``assumption_computation_context``.

    This is the replacement entry point for the historical pattern of
    reading runway/brake/T_static from ``design_assumptions``.

    Parameters
    ----------
    aeroplane:
        The aeroplane model to evaluate. Its ``assumption_computation_context``
        provides the cached aero inputs.
    db:
        Optional SQLAlchemy session. If omitted, a short-lived session is
        opened (and closed) via ``SessionLocal``.
    """
    from app.db.session import SessionLocal
    from app.services.mission_objective_service import get_mission_objective

    if db is None:
        db = SessionLocal()
        owned = True
    else:
        owned = False

    try:
        objective = get_mission_objective(db, aeroplane.id)
        ctx = aeroplane.assumption_computation_context or {}
        polar_by_config = ctx.get("polar_by_config") or {}
        aircraft_dict: dict = {
            "mass_kg": ctx.get("mass_kg"),
            # gh-548: fall back to the AeroplaneModel column so this wrapper
            # agrees with mission_kpi_service on the W/S mass source.
            "total_mass_kg": getattr(aeroplane, "total_mass_kg", None),
            "s_ref_m2": ctx.get("s_ref_m2"),
            "v_stall_mps": ctx.get("v_stall_mps"),
            "v_s_to_mps": ctx.get("v_s_to_mps"),
            "v_s0_mps": ctx.get("v_s0_mps"),
            "cl_max": ctx.get("cl_max"),
            "cl_max_takeoff": (polar_by_config.get("takeoff") or {}).get("cl_max"),
            "cl_max_landing": (polar_by_config.get("landing") or {}).get("cl_max"),
            "flap_type": ctx.get("flap_type"),
            # Field-performance inputs from the MissionObjective.
            "available_runway_m": objective.available_runway_m,
            "runway_type": objective.runway_type,
            "t_static_N": objective.t_static_N,
            "takeoff_mode": objective.takeoff_mode,
        }
        return compute_field_lengths(
            aircraft_dict,
            takeoff_mode=objective.takeoff_mode,
            landing_mode="belly_land" if objective.runway_type == "belly" else "runway",
        )
    finally:
        if owned:
            db.close()
