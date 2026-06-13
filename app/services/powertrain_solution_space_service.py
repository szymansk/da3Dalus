"""Powertrain solution-space service (gh-975).

Computes the *required* component-spec envelope from mission + aero
(reframe from the old catalog sweep).  Pure Python — no CadQuery or
AeroSandbox imports — so it runs in the CI fast tier.

Public API
----------
compute_solution_space(db, plane, assumptions) -> PowertrainSolutionSpaceResponse

Physics model (spec-exact)
--------------------------
All equations from the spec doc (2026-06-13-powertrain-solution-space-design.md):

  C_L(V) = 2·m·g / (ρ·V²·S_ref)
  C_D(V) = cd0 + C_L² / (π·e·AR)
  P_aero(V) = ½·ρ·V³·S_ref·C_D(V)
  P_elec(V) = P_aero(V) / (η_prop·η_motor·η_esc)

  Energy  E_Wh = P_elec(V_cruise) · (t_target_h) / DoD

  Per cell-count S:
    V_nom = S × 3.7  [V]
    V_sag = S × 3.5  [V]  (under load)
    I_peak  = P_top  / (V_sag · η_motor · η_esc)
    cap_mAh = E_Wh  / V_nom × 1000
    C_min   = I_peak / (cap_mAh / 1000)
    ESC_min = I_peak × esc_margin
    KV ≈ RPM_target / (V_nom × load_rpm_factor)
       where RPM_target = V_top / (prop_d_m × prop_pd) × 60   [approximate]
       and   prop_d_m   = 0.3  [m]  (fixed Phase-1 estimate — see note below)

Note on KV: Phase 1 uses a fixed prop diameter estimate (0.30 m) as a
first approximation.  This is documented as approximate in the schema.
Phase 2 (#615) will replace this with APC performance data.
"""

from __future__ import annotations

import logging
import math
from typing import Any, cast

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationDomainError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.powertrain_solution_space import (
    FeasibleRegion,
    PowertrainSolutionSpaceResponse,
    ShoppingSpec,
    SolutionRow,
    SolutionSpaceAssumptions,
)
from app.services.design_assumptions_service import get_effective_assumption

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
G_DEFAULT = 9.80665  # m/s²  (overridable via assumptions.g)
RHO_DEFAULT = 1.225  # kg/m³ (ISA sea-level, overridable via assumptions.rho)

# Nominal / sag cell voltages for LiPo
CELL_V_NOM = 3.7  # V  nominal (mid-discharge)
CELL_V_SAG = 3.5  # V  under peak load

# Phase-1 prop diameter estimate (see module docstring)
_PHASE1_PROP_DIAMETER_M = 0.30

# Number of sample points for the feasible-region C-rate hyperbola
_HYPERBOLA_SAMPLES = 40


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _p_aero(
    rho: float,
    v: float,
    mass_kg: float,
    g: float,
    cd0: float,
    e: float,
    ar: float,
    s_ref: float,
) -> float:
    """Aerodynamic power [W] in level flight at speed v [m/s].

    P_aero = ½·ρ·V³·S_ref·C_D
    C_L    = 2·m·g / (ρ·V²·S_ref)
    C_D    = cd0 + C_L² / (π·e·AR)
    """
    if v <= 0:
        return float("inf")
    q = 0.5 * rho * v * v
    cl = (mass_kg * g) / (q * s_ref)
    k = 1.0 / (math.pi * e * ar)
    cd = cd0 + k * cl * cl
    return q * s_ref * cd * v


def _p_elec(p_aero_w: float, eta_prop: float, eta_motor: float, eta_esc: float) -> float:
    """Electrical power [W] = P_aero / (η_prop · η_motor · η_esc)."""
    eta = eta_prop * eta_motor * eta_esc
    if eta <= 0:
        return float("inf")
    return p_aero_w / eta


def _per_cell(
    *,
    s: int,
    p_cruise_elec_w: float,
    p_top_elec_w: float,
    energy_wh: float,
    eta_motor: float,
    eta_esc: float,
    esc_margin: float,
    load_rpm_factor: float,
    v_top_mps: float,
    prop_pd: float,
) -> dict[str, float]:
    """Derive per-cell-count specs.  Returns a plain dict (used for both mid and band)."""
    v_nom = s * CELL_V_NOM
    v_sag = s * CELL_V_SAG

    # Peak current drawn from battery at top speed
    i_peak = p_top_elec_w / (v_sag * eta_motor * eta_esc)

    # Capacity (energy budget)
    cap_mah = energy_wh / v_nom * 1000.0

    # C-rate floor
    c_min = i_peak / (cap_mah / 1000.0) if cap_mah > 0 else float("inf")

    # ESC minimum rating
    esc_min = i_peak * esc_margin

    # KV approximation (Phase 1, documented approximate)
    # RPM_target ≈ V_top / (D × pitch/D) × 60  where D is Phase-1 estimate
    # KV = RPM_target / (V_nom × load_rpm_factor)
    prop_d = _PHASE1_PROP_DIAMETER_M
    rpm_target = (v_top_mps / (prop_d * prop_pd)) * 60.0  # rev/min
    kv_approx = rpm_target / (v_nom * load_rpm_factor) if v_nom > 0 else None

    return {
        "v_nom": v_nom,
        "v_sag": v_sag,
        "i_peak": i_peak,
        "cap_mah": cap_mah,
        "c_min": c_min,
        "esc_min": esc_min,
        "kv_approx": kv_approx,
    }


def _build_hyperbola(
    i_peak: float, cap_floor_mah: float, n: int = _HYPERBOLA_SAMPLES
) -> tuple[list[float], list[float]]:
    """Sample points on the C-rate hyperbola C = I_peak / (cap_mAh/1000).

    The x-axis starts at cap_floor_mah and extends to 4× for plotting room.
    """
    if cap_floor_mah <= 0 or i_peak <= 0:
        return [], []
    cap_max = cap_floor_mah * 4.0
    caps = [cap_floor_mah + (cap_max - cap_floor_mah) * i / (n - 1) for i in range(n)]
    c_rates = [i_peak / (c / 1000.0) for c in caps]
    return caps, c_rates


# ---------------------------------------------------------------------------
# Catalog matching helpers
# ---------------------------------------------------------------------------


def _catalog_motor_match(db: Session, motor_peak_w: float) -> bool:
    """Return True if any brushless_motor in the catalog meets motor_peak_w.

    Checks specs.max_power_w; falls back to specs.kv_rpm_v presence as an
    existence check only when max_power_w is absent.
    """
    motors = (
        db.query(ComponentModel).filter(ComponentModel.component_type == "brushless_motor").all()
    )
    for m in motors:
        specs: dict[str, Any] = m.specs or {}
        max_power = specs.get("max_power_w") or specs.get("max_continuous_power_w")
        if max_power is not None and float(max_power) >= motor_peak_w:
            return True
    return False


def _catalog_battery_match(db: Session, cap_mah_min: float, c_min: float) -> bool:
    """Return True if any battery in the catalog meets capacity AND C-rate floors."""
    batteries = db.query(ComponentModel).filter(ComponentModel.component_type == "battery").all()
    for b in batteries:
        specs: dict[str, Any] = b.specs or {}
        cap = specs.get("capacity_mah")
        c_rating = specs.get("c_rating") or specs.get("discharge_c")
        if cap is not None and c_rating is not None:
            if float(cap) >= cap_mah_min and float(c_rating) >= c_min:
                return True
    return False


def _catalog_esc_match(db: Session, esc_min_a: float) -> bool:
    """Return True if any ESC in the catalog meets the minimum current rating."""
    escs = db.query(ComponentModel).filter(ComponentModel.component_type == "esc").all()
    for e in escs:
        specs: dict[str, Any] = e.specs or {}
        max_a = specs.get("max_current_a") or specs.get("continuous_current_a")
        if max_a is not None and float(max_a) >= esc_min_a:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_solution_space(
    db: Session,
    plane: AeroplaneModel,
    assumptions: SolutionSpaceAssumptions,
) -> PowertrainSolutionSpaceResponse:
    """Compute powertrain solution space for an aeroplane.

    Parameters
    ----------
    db          : open SQLAlchemy session
    plane       : resolved AeroplaneModel (must have .id and .assumption_computation_context)
    assumptions : tunable overrides (SolutionSpaceAssumptions with defaults)

    Returns
    -------
    PowertrainSolutionSpaceResponse

    Raises
    ------
    ValidationDomainError
        When V_top ≤ V_cruise or t_target ≤ 0 (domain-level validation).
    """
    warnings: list[str] = []
    plane_id: int = cast(int, plane.id)
    ctx: dict[str, Any] = cast(dict[str, Any], plane.assumption_computation_context or {})

    # ------------------------------------------------------------------
    # 1. Read aero invariants from the gh-924 context
    # ------------------------------------------------------------------
    s_ref_m2: float | None = ctx.get("s_ref_m2")
    e_oswald: float | None = ctx.get("e_oswald")
    ar: float | None = ctx.get("aspect_ratio")
    v_cruise_ctx: float | None = ctx.get("v_cruise_mps") or ctx.get("v_md_mps")

    if s_ref_m2 is None or s_ref_m2 <= 0:
        warnings.append(
            "s_ref_m2 missing or zero in assumption_computation_context — "
            "run recompute first. Using fallback 0.25 m²."
        )
        s_ref_m2 = 0.25  # minimal RC plane fallback

    if e_oswald is None or e_oswald <= 0:
        warnings.append(
            "e_oswald missing/uncomputed in assumption_computation_context — "
            "run recompute first. Using fallback 0.75."
        )
        e_oswald = 0.75

    if ar is None or ar <= 0:
        warnings.append(
            "aspect_ratio missing/uncomputed in assumption_computation_context — "
            "run recompute first. Using fallback 7.0."
        )
        ar = 7.0

    if v_cruise_ctx is None or v_cruise_ctx <= 0:
        warnings.append(
            "v_cruise_mps / v_md_mps missing in assumption_computation_context — "
            "run recompute first. Using fallback 15.0 m/s."
        )
        v_cruise_ctx = 15.0

    # ------------------------------------------------------------------
    # 2. Read mass from design assumptions (same pattern as matching_chart)
    # ------------------------------------------------------------------
    mass_kg_raw = get_effective_assumption(db, plane_id, "mass")
    if mass_kg_raw is None or float(mass_kg_raw) <= 0:
        warnings.append("mass not set in design assumptions. Using fallback 1.5 kg.")
        mass_kg = float(PARAMETER_DEFAULTS.get("mass", 1.5))
    else:
        mass_kg = float(mass_kg_raw)

    # Also read cd0 from design assumptions (fallback to context, then default)
    cd0_raw = get_effective_assumption(db, plane_id, "cd0")
    if cd0_raw is not None and float(cd0_raw) > 0:
        cd0 = float(cd0_raw)
    else:
        cd0_ctx = ctx.get("cd0")
        if cd0_ctx is not None and float(cd0_ctx) > 0:
            cd0 = float(cd0_ctx)
        else:
            warnings.append("cd0 not set in design assumptions or context. Using fallback 0.03.")
            cd0 = float(PARAMETER_DEFAULTS.get("cd0", 0.03))

    v_cruise_mps = v_cruise_ctx

    # ------------------------------------------------------------------
    # 3. Resolve V_top and t_target from assumptions
    # ------------------------------------------------------------------
    t_target_min = assumptions.t_target_min
    if t_target_min <= 0:
        raise ValidationDomainError(f"t_target_min must be > 0, got {t_target_min}")

    v_top_mps = assumptions.v_top_mps
    if v_top_mps is None:
        v_top_mps = v_cruise_mps * 1.4  # spec default

    if v_top_mps <= v_cruise_mps:
        raise ValidationDomainError(
            f"V_top ({v_top_mps:.2f} m/s) must be greater than V_cruise ({v_cruise_mps:.2f} m/s)."
        )

    rho = assumptions.rho
    g = assumptions.g

    # ------------------------------------------------------------------
    # 4. Compute aerodynamic invariants
    # ------------------------------------------------------------------
    p_aero_cruise = _p_aero(rho, v_cruise_mps, mass_kg, g, cd0, e_oswald, ar, s_ref_m2)
    p_aero_top = _p_aero(rho, v_top_mps, mass_kg, g, cd0, e_oswald, ar, s_ref_m2)

    t_target_h = t_target_min / 60.0

    # ------------------------------------------------------------------
    # 5. Per-cell-count rows (spanning η_prop band)
    # ------------------------------------------------------------------
    eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0

    # Electrical power at mid, lo, hi (lo η_prop → hi P_elec)
    p_cruise_mid = _p_elec(p_aero_cruise, eta_mid, assumptions.eta_motor, assumptions.eta_esc)
    p_top_mid = _p_elec(p_aero_top, eta_mid, assumptions.eta_motor, assumptions.eta_esc)

    p_cruise_lo_e = _p_elec(
        p_aero_cruise, assumptions.eta_prop_lo, assumptions.eta_motor, assumptions.eta_esc
    )
    p_cruise_hi_e = _p_elec(
        p_aero_cruise, assumptions.eta_prop_hi, assumptions.eta_motor, assumptions.eta_esc
    )
    p_top_lo_e = _p_elec(
        p_aero_top, assumptions.eta_prop_lo, assumptions.eta_motor, assumptions.eta_esc
    )
    p_top_hi_e = _p_elec(
        p_aero_top, assumptions.eta_prop_hi, assumptions.eta_motor, assumptions.eta_esc
    )

    # Energy [Wh] using mid-η cruise power
    energy_wh = p_cruise_mid * t_target_h / assumptions.dod

    rows: list[SolutionRow] = []
    feasible_regions: list[FeasibleRegion] = []
    shopping_specs: list[ShoppingSpec] = []

    for s in assumptions.cell_counts:
        # Mid-η values
        mid = _per_cell(
            s=s,
            p_cruise_elec_w=p_cruise_mid,
            p_top_elec_w=p_top_mid,
            energy_wh=energy_wh,
            eta_motor=assumptions.eta_motor,
            eta_esc=assumptions.eta_esc,
            esc_margin=assumptions.esc_margin,
            load_rpm_factor=assumptions.load_rpm_factor,
            v_top_mps=v_top_mps,
            prop_pd=assumptions.prop_pd,
        )

        # Low-η band extreme (lo η_prop → higher currents/more capacity needed)
        lo_band = _per_cell(
            s=s,
            p_cruise_elec_w=p_cruise_lo_e,
            p_top_elec_w=p_top_lo_e,
            energy_wh=p_cruise_lo_e * t_target_h / assumptions.dod,
            eta_motor=assumptions.eta_motor,
            eta_esc=assumptions.eta_esc,
            esc_margin=assumptions.esc_margin,
            load_rpm_factor=assumptions.load_rpm_factor,
            v_top_mps=v_top_mps,
            prop_pd=assumptions.prop_pd,
        )

        # High-η band extreme (hi η_prop → lower currents/less capacity needed)
        hi_band = _per_cell(
            s=s,
            p_cruise_elec_w=p_cruise_hi_e,
            p_top_elec_w=p_top_hi_e,
            energy_wh=p_cruise_hi_e * t_target_h / assumptions.dod,
            eta_motor=assumptions.eta_motor,
            eta_esc=assumptions.eta_esc,
            esc_margin=assumptions.esc_margin,
            load_rpm_factor=assumptions.load_rpm_factor,
            v_top_mps=v_top_mps,
            prop_pd=assumptions.prop_pd,
        )

        # Catalog matches
        has_motor = _catalog_motor_match(db, p_aero_top)
        has_batt = _catalog_battery_match(db, mid["cap_mah"], mid["c_min"])
        has_esc = _catalog_esc_match(db, mid["esc_min"])

        row = SolutionRow(
            cell_count=s,
            v_nom_v=mid["v_nom"],
            v_sag_v=mid["v_sag"],
            p_cruise_w=p_cruise_mid,
            p_top_w=p_top_mid,
            # Band: lo band has higher power (less efficient η), hi band has lower power
            p_cruise_lo_w=p_cruise_hi_e,  # hi-η side → lower power needed (lo side of power range)
            p_cruise_hi_w=p_cruise_lo_e,  # lo-η side → higher power needed
            p_top_lo_w=p_top_hi_e,
            p_top_hi_w=p_top_lo_e,
            energy_wh=energy_wh,
            capacity_mah_min=mid["cap_mah"],
            capacity_mah_min_lo=hi_band["cap_mah"],  # hi-η → lower cap needed
            capacity_mah_min_hi=lo_band["cap_mah"],  # lo-η → more cap needed
            i_peak_a=mid["i_peak"],
            i_peak_lo_a=hi_band["i_peak"],
            i_peak_hi_a=lo_band["i_peak"],
            c_min=mid["c_min"],
            c_min_lo=hi_band["c_min"],
            c_min_hi=lo_band["c_min"],
            esc_min_a=mid["esc_min"],
            esc_min_lo_a=hi_band["esc_min"],
            esc_min_hi_a=lo_band["esc_min"],
            motor_peak_w=p_aero_top,
            motor_cont_w=p_aero_cruise,
            kv_approx=mid["kv_approx"],
            has_motor_match=has_motor,
            has_battery_match=has_batt,
            has_esc_match=has_esc,
        )
        rows.append(row)

        # Feasible region
        cap_floor = mid["cap_mah"]
        caps, c_rates = _build_hyperbola(mid["i_peak"], cap_floor)
        feasible_regions.append(
            FeasibleRegion(
                cell_count=s,
                capacity_floor_mah=cap_floor,
                i_peak_a=mid["i_peak"],
                capacity_curve_mah=caps,
                c_rate_curve=c_rates,
            )
        )

        shopping_specs.append(
            ShoppingSpec(
                cell_count=s,
                battery_min_mah=cap_floor,
                battery_min_c=mid["c_min"],
                battery_v_nom=mid["v_nom"],
                esc_min_a=mid["esc_min"],
                motor_min_peak_w=p_aero_top,
                motor_cont_w=p_aero_cruise,
                kv_approx=mid["kv_approx"],
            )
        )

    return PowertrainSolutionSpaceResponse(
        rows=rows,
        feasible_regions=feasible_regions,
        shopping_specs=shopping_specs,
        p_aero_cruise_w=p_aero_cruise,
        p_aero_top_w=p_aero_top,
        energy_wh=energy_wh,
        v_cruise_mps=v_cruise_mps,
        v_top_mps=v_top_mps,
        t_target_min=t_target_min,
        assumptions_used=assumptions,
        warnings=warnings,
    )
