"""Electric endurance / range service — gh-490.

Implements energy-balance model for electric propulsion following:
  - Anderson 6e §6.4–6.5: P_req(V), V_md (min drag), V_min_sink (min power)
  - Hepperle 2012: Electric endurance with constant mass
  - Traub 2011: Range and endurance estimates for battery-powered aircraft

Public API
----------
compute_endurance(db, aircraft) -> dict

Helpers (exposed for unit testing)
-----------------------------------
_power_required(rho, v, cd0, e, ar, mass, s_ref, eta_total)
_classify_p_margin(p_motor, p_req)
_check_battery_mass_consistency(capacity_wh, specific_energy_wh_per_kg, battery_mass_kg, warnings)

Explicit assumptions (Class-I approximation)
--------------------------------------------
1. Constant η over speed range (no J-dependent η_prop) — Class-I
2. Constant m_TO over discharge (electric aircraft, battery mass is constant)
3. Peukert effect neglected (valid for moderate C-rates < 2C)
4. Pack-level E* (≈ 180 Wh/kg LiPo) not cell-level (220 Wh/kg)
5. Linear polar valid for entire speed sweep (C_D = C_D0 + C_L²/(π·e·AR))

Out of scope
------------
- Fossil / IC engine model
- Peukert / high-C-rate correction
- η_prop(J) variation with advance ratio
- Climb power budget
- Solid-state / future battery chemistry (use E* override via design assumption)
"""

from __future__ import annotations

import logging
import math
import types
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Physical constants
G = 9.80665  # m/s²
RHO_SEA_LEVEL = 1.225  # kg/m³

# Default propulsion efficiencies (gh-490 AC spec)
DEFAULT_ETA_PROP = 0.65  # APC/Folding RC-Scale, Drela/Hepperle
DEFAULT_ETA_MOTOR = 0.85  # Brushless outrunner
DEFAULT_ETA_ESC = 0.94  # Modern ESC

# Default battery energy density (pack-level LiPo)
DEFAULT_BATTERY_SPECIFIC_ENERGY_WH_PER_KG = 180.0

# Fallback Oswald efficiency when polar fit fails
FALLBACK_E_OSWALD = 0.8

# p_margin thresholds
P_MARGIN_COMFORTABLE = 0.20  # > 20% → comfortable
# > 0% but ≤ 20% → feasible but tight
# ≤ 0% → infeasible

# Battery mass cross-check threshold
BATTERY_MASS_DEVIATION_THRESHOLD = 0.30  # 30%


# ---------------------------------------------------------------------------
# Core aerodynamics helpers
# ---------------------------------------------------------------------------


def _power_required(
    rho: float,
    v: float,
    cd0: float,
    e: float,
    ar: float,
    mass: float,
    s_ref: float,
    eta_total: float,
) -> float:
    """Shaft-to-battery power required for level flight.

    P_req(V) = D(V) · V / η_total
             = (½·ρ·V²·S·C_D(V)) · V / η_total

    with C_D(V) = C_D0 + C_L(V)² / (π·e·AR)
    and  C_L(V) = 2·m·g / (ρ·V²·S)

    Parameters
    ----------
    rho       Air density [kg/m³]
    v         True airspeed [m/s]  (must be > 0)
    cd0       Zero-lift drag coefficient
    e         Oswald efficiency factor
    ar        Wing aspect ratio
    mass      Total aircraft mass [kg]
    s_ref     Wing reference area [m²]
    eta_total Combined propulsion efficiency η_prop × η_motor × η_esc

    Returns
    -------
    Power in Watts [W]

    Raises
    ------
    ZeroDivisionError  if v == 0 (C_L → ∞)
    """
    if v <= 0:
        # v=0 → induced drag infinite; return very large number for callers
        # that may not check v beforehand
        return float("inf")

    q = 0.5 * rho * v * v  # dynamic pressure [Pa]
    cl = (mass * G) / (q * s_ref)  # level-flight lift coefficient
    k = 1.0 / (math.pi * e * ar)  # induced drag factor
    cd = cd0 + k * cl * cl  # total drag coefficient
    drag = q * s_ref * cd  # drag force [N]
    p_aero = drag * v  # aerodynamic power [W]
    if eta_total <= 0:
        return float("inf")
    return p_aero / eta_total  # battery power [W]


# ---------------------------------------------------------------------------
# p_margin classification
# ---------------------------------------------------------------------------


def _classify_p_margin(p_motor: float, p_req: float) -> dict[str, Any]:
    """Classify the power margin of the propulsion system.

    p_margin = (P_motor_continuous - P_req) / P_motor_continuous

    Returns a dict with keys: p_margin, p_margin_class
    """
    if p_motor <= 0:
        return {"p_margin": float("-inf"), "p_margin_class": "infeasible — motor underpowered"}

    margin = (p_motor - p_req) / p_motor
    if margin > P_MARGIN_COMFORTABLE:
        cls = "comfortable"
    elif margin > 0.0:
        cls = "feasible but tight"
    else:
        cls = "infeasible — motor underpowered"

    return {"p_margin": round(margin, 4), "p_margin_class": cls}


# ---------------------------------------------------------------------------
# Battery mass cross-check
# ---------------------------------------------------------------------------


def _check_battery_mass_consistency(
    capacity_wh: float,
    specific_energy_wh_per_kg: float,
    battery_mass_kg: float | None,
    warnings: list[str],
) -> float:
    """Compare capacity-implied battery mass with user-supplied component mass.

    Emits a warning (not an error) when the deviation exceeds 30 %.
    Always returns the predicted mass in grams.

    m_battery_predicted_g = capacity_wh / specific_energy_wh_per_kg * 1000

    Parameters
    ----------
    capacity_wh               Battery capacity in Wh (from design assumption)
    specific_energy_wh_per_kg Pack-level specific energy in Wh/kg
    battery_mass_kg           User-supplied battery component mass in kg (may be None)
    warnings                  Mutable list; warning strings appended in-place

    Returns
    -------
    Predicted battery mass in grams [g]
    """
    predicted_kg = capacity_wh / specific_energy_wh_per_kg
    predicted_g = predicted_kg * 1000.0

    if battery_mass_kg is not None and battery_mass_kg > 0:
        deviation = abs(predicted_kg - battery_mass_kg) / battery_mass_kg
        if deviation > BATTERY_MASS_DEVIATION_THRESHOLD:
            pct = round(deviation * 100, 1)
            warnings.append(
                f"Battery component mass deviates {pct} % from capacity-implied mass "
                f"(predicted {predicted_g:.0f} g from {capacity_wh:.1f} Wh / "
                f"{specific_energy_wh_per_kg:.0f} Wh/kg; "
                f"user component {battery_mass_kg * 1000:.0f} g). "
                "Using component mass for total weight."
            )

    return predicted_g


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_endurance(db: Session, aircraft: Any) -> dict[str, Any]:
    """Compute electric endurance and range for an aircraft.

    Reads from aircraft.assumption_computation_context (cached by
    assumption_compute_service, gh-486) for polar-derived quantities:
      - e_oswald, e_oswald_quality, e_oswald_fallback_used
      - v_md_mps, v_min_sink_mps, s_ref_m2, aspect_ratio

    Reads propulsion parameters from aircraft._design_assumptions dict
    (populated by the caller / service layer):
      - battery_capacity_wh
      - battery_specific_energy_wh_per_kg  (default 180)
      - propulsion_eta_prop                (default 0.65)
      - propulsion_eta_motor               (default 0.85)
      - propulsion_eta_esc                 (default 0.94)
      - motor_continuous_power_w
      - mass (total aircraft mass, includes battery)
      - cd0

    aircraft._battery_mass_kg is the user-set battery component mass
    (category='battery' weight item, in kg).

    Returns
    -------
    dict with keys:
      t_endurance_max_s        Maximum endurance [s] at V_min_sink
      range_max_m              Maximum range [m] at V_md
      p_req_at_v_md_w          Power required at V_md [W]
      p_req_at_v_min_sink_w    Power required at V_min_sink [W]
      p_margin                 (P_motor - P_req(V_md)) / P_motor
      p_margin_class           Classification string
      battery_mass_g_predicted Capacity-implied battery mass [g]
      confidence               'computed' | 'estimated'
      warnings                 list[str]
    """
    warnings: list[str] = []

    # --- Read computation context -------------------------------------------
    ctx = getattr(aircraft, "assumption_computation_context", None) or {}
    da = getattr(aircraft, "_design_assumptions", None) or {}

    e_oswald_raw: float | None = ctx.get("e_oswald")
    e_oswald_quality: str = ctx.get("e_oswald_quality", "unknown")
    e_oswald_fallback_used: bool = ctx.get("e_oswald_fallback_used", True)

    v_md: float | None = ctx.get("v_md_mps")
    v_min_sink: float | None = ctx.get("v_min_sink_mps")
    s_ref: float | None = ctx.get("s_ref_m2")
    ar: float | None = ctx.get("aspect_ratio")

    # Resolve mass — must be explicitly provided; 2.0 kg silent default removed (gh-490)
    _mass_raw = da.get("mass")
    if _mass_raw is None:
        raise ValueError(
            "aircraft mass is required for endurance computation but was not supplied. "
            "Set the 'mass' design assumption and call seed_defaults first."
        )
    mass: float = float(_mass_raw)
    cd0: float = float(da.get("cd0", 0.03))

    # Propulsion efficiencies
    eta_prop: float = float(da.get("propulsion_eta_prop", DEFAULT_ETA_PROP))
    eta_motor: float = float(da.get("propulsion_eta_motor", DEFAULT_ETA_MOTOR))
    eta_esc: float = float(da.get("propulsion_eta_esc", DEFAULT_ETA_ESC))
    eta_total: float = eta_prop * eta_motor * eta_esc

    # Battery
    capacity_wh: float | None = da.get("battery_capacity_wh")
    specific_energy: float = float(
        da.get("battery_specific_energy_wh_per_kg", DEFAULT_BATTERY_SPECIFIC_ENERGY_WH_PER_KG)
    )
    motor_w: float | None = da.get("motor_continuous_power_w")

    # Battery component mass from weight items
    battery_mass_kg: float | None = getattr(aircraft, "_battery_mass_kg", None)

    # --- Confidence determination -------------------------------------------
    # If polar fit was unreliable (fallback used or quality poor/unknown),
    # we mark the result as 'estimated'.
    is_estimated = e_oswald_fallback_used or e_oswald_quality in ("poor", "unknown")
    confidence = "estimated" if is_estimated else "computed"

    if is_estimated:
        warnings.append(
            "Endurance derived from fallback e=0.8 — polar fit unreliable. "
            "Run assumption recompute to improve accuracy."
        )

    # --- Resolve Oswald efficiency ------------------------------------------
    e_oswald: float = e_oswald_raw if e_oswald_raw is not None else FALLBACK_E_OSWALD

    # --- Validate required inputs -------------------------------------------
    missing = []
    if v_md is None:
        missing.append("v_md_mps")
    if v_min_sink is None:
        missing.append("v_min_sink_mps")
    if s_ref is None:
        missing.append("s_ref_m2")
    if ar is None:
        missing.append("aspect_ratio")
    if capacity_wh is None:
        missing.append("battery_capacity_wh")

    if missing:
        warnings.append(
            f"Cannot compute endurance — missing inputs: {', '.join(missing)}. "
            "Run assumption recompute first."
        )
        return {
            "t_endurance_max_s": None,
            "range_max_m": None,
            "p_req_at_v_md_w": None,
            "p_req_at_v_min_sink_w": None,
            "p_margin": None,
            "p_margin_class": None,
            "battery_mass_g_predicted": None,
            "confidence": confidence,
            "warnings": warnings,
        }

    # --- Battery mass cross-check -------------------------------------------
    battery_mass_g_predicted = _check_battery_mass_consistency(
        capacity_wh=capacity_wh,
        specific_energy_wh_per_kg=specific_energy,
        battery_mass_kg=battery_mass_kg,
        warnings=warnings,
    )

    # --- Power required at V_md and V_min_sink ------------------------------
    p_req_vmd = _power_required(
        rho=RHO_SEA_LEVEL,
        v=float(v_md),
        cd0=cd0,
        e=e_oswald,
        ar=float(ar),
        mass=mass,
        s_ref=float(s_ref),
        eta_total=eta_total,
    )
    p_req_vmin = _power_required(
        rho=RHO_SEA_LEVEL,
        v=float(v_min_sink),
        cd0=cd0,
        e=e_oswald,
        ar=float(ar),
        mass=mass,
        s_ref=float(s_ref),
        eta_total=eta_total,
    )

    # --- Endurance at V_min_sink (max endurance speed) ----------------------
    # t_endurance(V) = E_battery [Wh] × 3600 [s/h] / P_req(V) [W]
    capacity_wh_val = float(capacity_wh)
    if math.isfinite(p_req_vmin) and p_req_vmin > 0:
        t_endurance_max_s = (capacity_wh_val * 3600.0) / p_req_vmin
    else:
        t_endurance_max_s = float("inf")
        warnings.append("P_req at V_min_sink is non-finite; endurance undefined.")

    # --- Range at V_md (max range speed) ------------------------------------
    # range(V_md) = t_endurance(V_md) × V_md
    if math.isfinite(p_req_vmd) and p_req_vmd > 0:
        t_at_vmd_s = (capacity_wh_val * 3600.0) / p_req_vmd
        range_max_m = t_at_vmd_s * float(v_md)
    else:
        range_max_m = float("inf")
        warnings.append("P_req at V_md is non-finite; range undefined.")

    # --- Power margin -------------------------------------------------------
    p_margin_result: dict[str, Any]
    if motor_w is not None and motor_w > 0:
        p_margin_result = _classify_p_margin(
            p_motor=float(motor_w),
            p_req=p_req_vmd,
        )
    else:
        p_margin_result = {
            "p_margin": None,
            "p_margin_class": "unknown — no motor power specified",
        }
        warnings.append("motor_continuous_power_w not set; p_margin cannot be classified.")

    logger.info(
        "Endurance compute: t=%.0f s (%.1f min), range=%.0f m, confidence=%s, warnings=%d",
        t_endurance_max_s,
        t_endurance_max_s / 60.0,
        range_max_m,
        confidence,
        len(warnings),
    )

    return {
        "t_endurance_max_s": round(t_endurance_max_s, 1),
        "range_max_m": round(range_max_m, 1),
        "p_req_at_v_md_w": round(p_req_vmd, 2),
        "p_req_at_v_min_sink_w": round(p_req_vmin, 2),
        "p_margin": p_margin_result["p_margin"],
        "p_margin_class": p_margin_result["p_margin_class"],
        "battery_mass_g_predicted": round(battery_mass_g_predicted, 1),
        "confidence": confidence,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# DB-integrated entry point (for REST endpoint)
# ---------------------------------------------------------------------------


def compute_endurance_for_aeroplane(db: Session, aeroplane_uuid: Any) -> dict[str, Any]:
    """Load aeroplane from DB and compute electric endurance.

    Reads design assumptions (mass, cd0, propulsion efficiencies,
    battery_capacity_wh, motor_continuous_power_w) from the aeroplane's
    persisted DesignAssumptionModel rows (seeded by seed_defaults / gh-490).

    Battery mass is taken from the first weight item with category='battery'.
    m_TO always uses the user-component mass, not the capacity-implied value.

    Raises NotFoundError if the aeroplane UUID does not exist.
    """
    from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, WeightItemModel
    from app.schemas.design_assumption import PARAMETER_DEFAULTS

    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)

    # --- Load effective design assumptions from DB --------------------------
    def _load_effective_assumption(param: str) -> float | None:
        """Return the effective value for a design assumption row.

        Falls back to PARAMETER_DEFAULTS when no row exists.
        Returns None if the param has no default (unknown parameter).
        """
        row = (
            db.query(DesignAssumptionModel)
            .filter(
                DesignAssumptionModel.aeroplane_id == aeroplane.id,
                DesignAssumptionModel.parameter_name == param,
            )
            .first()
        )
        if row is None:
            return PARAMETER_DEFAULTS.get(param)
        if row.active_source == "CALCULATED" and row.calculated_value is not None:
            return row.calculated_value
        return row.estimate_value

    # Battery weight item (first item with category='battery')
    battery_item = (
        db.query(WeightItemModel)
        .filter(
            WeightItemModel.aeroplane_id == aeroplane.id,
            WeightItemModel.category == "battery",
        )
        .first()
    )
    battery_mass_kg: float | None = battery_item.mass_kg if battery_item else None

    # --- Resolve mass and cd0 with explicit None-checks ---------------------
    _mass_raw = _load_effective_assumption("mass")
    if _mass_raw is None:
        raise ValueError(
            "mass design assumption is missing — run seed_defaults first "
            "(compute_endurance_for_aeroplane requires a mass value)"
        )
    mass_val: float = float(_mass_raw)

    _cd0_raw = _load_effective_assumption("cd0")
    cd0_val: float = float(_cd0_raw) if _cd0_raw is not None else PARAMETER_DEFAULTS["cd0"]

    # --- Resolve propulsion efficiencies (explicit None-checks) -------------
    _eta_prop_raw = _load_effective_assumption("prop_efficiency")
    eta_prop_val: float = float(_eta_prop_raw) if _eta_prop_raw is not None else DEFAULT_ETA_PROP

    _eta_motor_raw = _load_effective_assumption("propulsion_eta_motor")
    eta_motor_val: float = (
        float(_eta_motor_raw) if _eta_motor_raw is not None else DEFAULT_ETA_MOTOR
    )

    _eta_esc_raw = _load_effective_assumption("propulsion_eta_esc")
    eta_esc_val: float = float(_eta_esc_raw) if _eta_esc_raw is not None else DEFAULT_ETA_ESC

    # --- Resolve battery parameters -----------------------------------------
    _specific_energy_raw = _load_effective_assumption("battery_specific_energy_wh_per_kg")
    specific_energy_val: float = (
        float(_specific_energy_raw)
        if _specific_energy_raw is not None
        else DEFAULT_BATTERY_SPECIFIC_ENERGY_WH_PER_KG
    )

    # battery_capacity_wh: 0.0 default means "not yet configured"
    _capacity_raw = _load_effective_assumption("battery_capacity_wh")
    capacity_val: float | None = (
        float(_capacity_raw) if (_capacity_raw is not None and _capacity_raw > 0.0) else None
    )

    # motor_continuous_power_w: 0.0 default means "not yet configured"
    _motor_w_raw = _load_effective_assumption("motor_continuous_power_w")
    motor_w_val: float | None = (
        float(_motor_w_raw) if (_motor_w_raw is not None and _motor_w_raw > 0.0) else None
    )

    # Build the _design_assumptions dict that compute_endurance expects
    da: dict[str, Any] = {
        "mass": mass_val,
        "cd0": cd0_val,
        "propulsion_eta_prop": eta_prop_val,
        "propulsion_eta_motor": eta_motor_val,
        "propulsion_eta_esc": eta_esc_val,
        "battery_capacity_wh": capacity_val,
        "battery_specific_energy_wh_per_kg": specific_energy_val,
        "motor_continuous_power_w": motor_w_val,
    }

    # Computation context supplies polar-derived geometry (e_oswald, v_md, etc.)
    ctx = aeroplane.assumption_computation_context or {}

    # Build a lightweight namespace aircraft that compute_endurance can read
    aircraft_ns = types.SimpleNamespace()
    aircraft_ns.assumption_computation_context = ctx
    aircraft_ns._design_assumptions = da
    aircraft_ns._battery_mass_kg = battery_mass_kg

    return compute_endurance(db=db, aircraft=aircraft_ns)
