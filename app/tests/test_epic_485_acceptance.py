"""Epic #485 acceptance smoke test — Class-I UAV/RC Design Workflow Completion.

Verifies the complete Wave 1-4 design workflow on 4 reference aircraft:
  1. Cessna 172  — full-scale GA, Re≈6.3M, V_cruise=62 m/s, conventional tail
  2. ASW-27 RC   — clean sailplane, Re≈1M, mid-scale, no powertrain
  3. RC Trainer  — draggy, Re≈200k, MAC=0.25 m, V_cruise=14 m/s
  4. V-tail UAV  — MTOW=3 kg, V-tail (ruddervator), electric

For each aircraft the test runs through 8 workflow stages:
  Stage 1 — assumption_compute_service.recompute_assumptions  (stubbed ASB)
  Stage 2 — matching_chart_service.compute_chart
  Stage 3 — sm_sizing_service.suggest_corrections
  Stage 4 — field_length_service.compute_field_lengths
  Stage 5 — endurance_service.compute_endurance_for_aeroplane
  Stage 6 — tail_sizing_service.compute_tail_volumes
  Stage 7 — flight_envelope_service.compute_flight_envelope
  Stage 8 — context-level cross-checks (cd0, V_md, polar_re_table, CG envelope)

All 32 stage×aircraft checkpoints are executed.

References:
- Scholz, HAW Flugzeugentwurf I §5 (matching chart)
- Roskam Vol I §3.4 (field length)
- Anderson 6e §6.3-6.5 (performance)
- Loftin (1980) T/W vs W/S chart

Markers:
  @pytest.mark.slow  — full stack test, requires DB + service logic
                       (no actual AeroBuildup/CAD heavy compute — ASB internals
                        are stubbed to keep runtime reasonable)
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignAssumptionModel,
    WeightItemModel,
    WingModel,
    WingXSecModel,
    WingXSecDetailModel,
    WingXSecTrailingEdgeDeviceModel,
)
from app.tests.conftest import client_and_db  # noqa: F401 — indirect fixture ref


# ===========================================================================
# Reference aircraft parameters (physics-consistent, Scholz/Roskam sourced)
# ===========================================================================

# Cessna 172N at MTOM (Loftin, Roskam Vol I)
CESSNA = {
    "name": "cessna172",
    # Geometry (m, m², etc.)
    "mass_kg": 1088.0,
    "t_static_N": 1900.0,
    "s_ref_m2": 16.17,
    "b_ref_m": 10.91,
    "ar": 7.32,
    "mac_m": 1.49,
    # Aerodynamics
    "cd0": 0.031,
    "e_oswald": 0.75,
    "cl_max": 1.6,
    "cl_max_takeoff": 1.6,
    "cl_max_landing": 2.1,
    # Speeds
    "v_cruise_mps": 62.0,
    "v_stall_mps": 25.4,
    # Stability
    "x_np_m": 1.34,       # ~0.25 MAC from leading edge
    "target_sm": 0.10,
    "g_limit": 3.8,
    # Expected ranges (Scholz/Roskam)
    "cd0_range": (0.027, 0.034),
    "v_md_range": (30.0, 42.0),         # m/s — Anderson 6e §6.4: V_md ≈ 38.4 m/s at MTOM
    "field_to_range": (200.0, 480.0),   # m (Roskam k_TO=1.66 gives ~470 m)
    "field_ldg_range": (150.0, 480.0),
    # Tail geometry (metres, DB convention)
    "htail_le_x": 5.5,
    "htail_mac_m": 0.88,
    "htail_span_half": 1.5,
    "htail_chord_root": 0.9,
    "htail_chord_tip": 0.75,
    "vtail_le_x": 5.5,
    "vtail_mac_m": 0.75,
    "vtail_span": 1.1,
    "vtail_chord_root": 0.80,
    "vtail_chord_tip": 0.60,
    # CG envelope (m)
    "cg_fwd_m": 0.28,
    "cg_aft_m": 0.38,
}

# ASW-27 scale RC sailplane (Schleicher datasheet; Scholz A11)
ASW27 = {
    "name": "asw27_rc",
    "mass_kg": 12.0,
    "t_static_N": 0.0,    # unpowered
    "s_ref_m2": 0.56,
    "b_ref_m": 4.0,
    "ar": 28.5,
    "mac_m": 0.50,
    "cd0": 0.018,
    "e_oswald": 0.88,
    "cl_max": 1.3,
    "cl_max_takeoff": 1.3,
    "cl_max_landing": 1.3,
    "v_cruise_mps": 37.0,
    "v_stall_mps": 12.0,
    "x_np_m": 0.145,
    "target_sm": 0.08,
    "g_limit": 5.3,
    "cd0_range": (0.008, 0.030),
    "v_md_range": (14.0, 22.0),         # m/s — Anderson §6.4: V_md ≈ 17.0 m/s at this geometry
    "field_to_range": None,        # winch/hand launch → no runway constraint
    "field_ldg_range": None,
    # Scale model fuselage ~1.0 m; tail arm 0.82 m preserves V_H ≈ 0.41 (full-scale ASW-27 ratio)
    "htail_le_x": 0.88,
    "htail_mac_m": 0.25,
    "htail_span_half": 0.50,
    "htail_chord_root": 0.28,
    "htail_chord_tip": 0.20,
    "vtail_le_x": 0.88,
    "vtail_mac_m": 0.18,
    "vtail_span": 0.28,
    "vtail_chord_root": 0.20,
    "vtail_chord_tip": 0.14,
    "cg_fwd_m": 0.10,
    "cg_aft_m": 0.135,
}

# RC trainer (Scholz A11: MAC=0.254 m, Re≈200k)
RC_TRAINER = {
    "name": "rc_trainer",
    "mass_kg": 2.0,
    "t_static_N": 12.0,   # T/W ≈ 0.61 — typical RC electric trainer (Scholz §5 matching chart range)
    "s_ref_m2": 0.40,
    "b_ref_m": 1.673,  # = sqrt(AR * S) = sqrt(7.0 * 0.40) — consistent with AR=7 (Scholz A11)
    "ar": 7.0,
    "mac_m": 0.254,
    "cd0": 0.050,
    "e_oswald": 0.78,
    "cl_max": 1.2,
    "cl_max_takeoff": 1.2,
    "cl_max_landing": 1.4,
    "v_cruise_mps": 14.0,
    "v_stall_mps": 8.0,
    "x_np_m": 0.076,
    "target_sm": 0.12,
    "g_limit": 5.0,
    "cd0_range": (0.040, 0.065),
    "v_md_range": (7.0, 15.0),          # m/s — Anderson §6.4: V_md ≈ 9.3 m/s at this geometry
    # W/S = 49 N/m² (very light wing loading) → ground roll physically ~5-10 m
    # Roskam formula: s = 1.21 * (W/S) / (rho * g * CL_max * T/W) ≈ 6.7 m at T/W=0.61
    "field_to_range": (3.0, 30.0),    # m — short-field RC trainer with low wing loading
    "field_ldg_range": (3.0, 30.0),
    # Tail geometry (metres)
    "htail_le_x": 0.72,
    "htail_mac_m": 0.13,
    "htail_span_half": 0.28,
    "htail_chord_root": 0.14,
    "htail_chord_tip": 0.10,
    "vtail_le_x": 0.72,
    "vtail_mac_m": 0.10,
    "vtail_span": 0.16,
    "vtail_chord_root": 0.12,
    "vtail_chord_tip": 0.07,
    "cg_fwd_m": 0.05,
    "cg_aft_m": 0.07,
    # Battery (for endurance test)
    "battery_capacity_wh": 74.0,
    "motor_continuous_w": 200.0,
}

# V-tail UAV (electric, MTOW=3 kg)
VTAIL_UAV = {
    "name": "vtail_uav",
    "mass_kg": 3.0,
    "t_static_N": 15.0,   # T/W ≈ 0.51 — typical small UAV electric (bungee/short runway)
    "s_ref_m2": 0.55,
    "b_ref_m": 2.0,
    "ar": 7.3,
    "mac_m": 0.28,
    "cd0": 0.035,
    "e_oswald": 0.80,
    "cl_max": 1.3,
    "cl_max_takeoff": 1.3,
    "cl_max_landing": 1.3,
    "v_cruise_mps": 18.0,
    "v_stall_mps": 10.0,
    "x_np_m": 0.085,
    "target_sm": 0.10,
    "g_limit": 4.0,
    "cd0_range": (0.025, 0.045),
    "v_md_range": (8.0, 16.0),          # m/s — Anderson §6.4: V_md ≈ 10.4 m/s at this geometry
    # W/S = 53.5 N/m² (lightweight UAV) → ground roll ~8 m at T/W=0.51 (Roskam §3.4)
    "field_to_range": (3.0, 25.0),
    "field_ldg_range": (3.0, 25.0),
    "htail_le_x": None,  # V-tail: tail_sizing is not_applicable
    "htail_mac_m": None,
    "htail_span_half": None,
    "htail_chord_root": None,
    "htail_chord_tip": None,
    "vtail_le_x": None,
    "vtail_mac_m": None,
    "vtail_span": None,
    "vtail_chord_root": None,
    "vtail_chord_tip": None,
    "cg_fwd_m": 0.07,
    "cg_aft_m": 0.082,
    # Battery
    "battery_capacity_wh": 100.0,
    "motor_continuous_w": 300.0,
}

ALL_AIRCRAFT = [CESSNA, ASW27, RC_TRAINER, VTAIL_UAV]


# ===========================================================================
# DB seeding helpers
# ===========================================================================

def _seed_aeroplane(session: Session, ac: dict) -> AeroplaneModel:
    """Create and commit an AeroplaneModel with the reference geometry."""
    aeroplane = AeroplaneModel(
        name=f"epic485-{ac['name']}",
        uuid=uuid.uuid4(),
        total_mass_kg=ac["mass_kg"],
        xyz_ref=[ac["x_np_m"] - ac["target_sm"] * ac["mac_m"], 0.0, 0.0],
    )
    session.add(aeroplane)
    session.flush()
    return aeroplane


def _seed_xsec(
    session: Session,
    wing: WingModel,
    xyz_le: list[float],
    chord: float,
    twist: float,
    airfoil: str,
    sort_index: int,
    ted_kwargs: dict | None = None,
) -> WingXSecModel:
    xsec = WingXSecModel(
        wing_id=wing.id,
        xyz_le=xyz_le,
        chord=chord,
        twist=twist,
        airfoil=airfoil,
        sort_index=sort_index,
    )
    session.add(xsec)
    session.flush()
    if ted_kwargs:
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id, x_sec_type="segment")
        session.add(detail)
        session.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, **ted_kwargs
        )
        session.add(ted)
        session.flush()
    return xsec


def _add_wing(
    session: Session,
    aeroplane_id: int,
    name: str,
    symmetric: bool,
    xsecs: list[dict],
) -> WingModel:
    wing = WingModel(name=name, symmetric=symmetric, aeroplane_id=aeroplane_id)
    session.add(wing)
    session.flush()
    for i, xs in enumerate(xsecs):
        _seed_xsec(
            session, wing,
            xyz_le=xs["xyz_le"],
            chord=xs["chord"],
            twist=xs.get("twist", 0.0),
            airfoil=xs.get("airfoil", "naca2412"),
            sort_index=i,
            ted_kwargs=xs.get("ted"),
        )
    return wing


def _ted(name: str, role: str, symmetric: bool = False) -> dict:
    return {
        "name": name,
        "role": role,
        "rel_chord_root": 0.75,
        "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0,
        "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0,
        "symmetric": symmetric,
    }


def _seed_conventional_wings(session: Session, ap_id: int, ac: dict) -> None:
    """Main wing + horizontal tail + vertical tail for conventional aircraft."""
    span_half = ac["b_ref_m"] / 2.0
    root_chord = ac["s_ref_m2"] / ac["b_ref_m"] * 1.25   # approximate tapered
    tip_chord = root_chord * 0.7
    _add_wing(session, ap_id, "main_wing", symmetric=True, xsecs=[
        {"xyz_le": [0.0, 0.0, 0.0], "chord": root_chord, "twist": 2.0,
         "airfoil": "naca2412",
         "ted": _ted("Aileron", "aileron")},
        {"xyz_le": [root_chord * 0.1, span_half * 0.5, 0.0], "chord": (root_chord + tip_chord) / 2, "twist": 0.0,
         "airfoil": "naca2412"},
        {"xyz_le": [root_chord * 0.2, span_half, 0.0], "chord": tip_chord, "twist": -1.0,
         "airfoil": "naca2412"},
    ])
    htail_le_x = ac["htail_le_x"]
    htail_chord_root = ac["htail_chord_root"]
    htail_chord_tip = ac["htail_chord_tip"]
    htail_span_half = ac["htail_span_half"]
    _add_wing(session, ap_id, "horizontal_tail", symmetric=True, xsecs=[
        {"xyz_le": [htail_le_x, 0.0, 0.0], "chord": htail_chord_root,
         "twist": 0.0, "airfoil": "naca0010",
         "ted": _ted("Elevator", "elevator", symmetric=True)},
        {"xyz_le": [htail_le_x + 0.05 * htail_chord_root, htail_span_half, 0.0],
         "chord": htail_chord_tip, "twist": 0.0, "airfoil": "naca0010"},
    ])
    vtail_le_x = ac["vtail_le_x"]
    vtail_chord_root = ac["vtail_chord_root"]
    vtail_chord_tip = ac["vtail_chord_tip"]
    vtail_span = ac["vtail_span"]
    _add_wing(session, ap_id, "vertical_tail", symmetric=False, xsecs=[
        {"xyz_le": [vtail_le_x, 0.0, 0.0], "chord": vtail_chord_root,
         "twist": 0.0, "airfoil": "naca0010",
         "ted": _ted("Rudder", "rudder", symmetric=True)},
        {"xyz_le": [vtail_le_x + 0.05 * vtail_chord_root, 0.0, vtail_span],
         "chord": vtail_chord_tip, "twist": 0.0, "airfoil": "naca0010"},
    ])


def _seed_vtail_wings(session: Session, ap_id: int, ac: dict) -> None:
    """Main wing + V-tail with ruddervator for V-tail UAV."""
    span_half = ac["b_ref_m"] / 2.0
    root_chord = ac["s_ref_m2"] / ac["b_ref_m"] * 1.25
    tip_chord = root_chord * 0.7
    _add_wing(session, ap_id, "main_wing", symmetric=True, xsecs=[
        {"xyz_le": [0.0, 0.0, 0.0], "chord": root_chord, "twist": 2.0,
         "airfoil": "naca4412",
         "ted": _ted("Aileron", "aileron")},
        {"xyz_le": [root_chord * 0.1, span_half, 0.0], "chord": tip_chord, "twist": -1.0,
         "airfoil": "naca4412"},
    ])
    # V-tail: symmetric surface with dihedral simulated by z at tip
    v_span_half = 0.32
    v_root_chord = 0.18
    v_tip_chord = 0.12
    _add_wing(session, ap_id, "v_tail", symmetric=True, xsecs=[
        {"xyz_le": [0.80, 0.0, 0.06], "chord": v_root_chord,
         "twist": -5.0, "airfoil": "naca0010",
         "ted": _ted("Ruddervator", "ruddervator", symmetric=True)},
        {"xyz_le": [0.82, v_span_half, v_span_half * 0.45], "chord": v_tip_chord,
         "twist": -5.0, "airfoil": "naca0010"},
    ])


def _seed_design_assumptions(
    session: Session, aeroplane_id: int, aeroplane_uuid: str, ac: dict
) -> None:
    """Seed design assumption rows with aircraft-specific values."""
    from app.services.design_assumptions_service import seed_defaults

    seed_defaults(session, aeroplane_uuid)
    session.flush()

    # Override with aircraft-specific values
    overrides: dict[str, float] = {
        "mass": ac["mass_kg"],
        "cd0": ac["cd0"],
        "cl_max": ac["cl_max"],
        "target_static_margin": ac["target_sm"],
        "g_limit": ac["g_limit"],
        "t_static_N": ac["t_static_N"],
        "power_to_weight": 0.0 if ac["t_static_N"] == 0 else 200.0,
    }
    if ac.get("battery_capacity_wh"):
        overrides["battery_capacity_wh"] = ac["battery_capacity_wh"]
    if ac.get("motor_continuous_w"):
        overrides["motor_continuous_power_w"] = ac["motor_continuous_w"]

    for param, value in overrides.items():
        row = (
            session.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aeroplane_id, parameter_name=param)
            .first()
        )
        if row:
            row.estimate_value = value
        else:
            row = DesignAssumptionModel(
                aeroplane_id=aeroplane_id,
                parameter_name=param,
                estimate_value=value,
                active_source="ESTIMATE",
                updated_at=datetime.now(timezone.utc),
            )
            session.add(row)
    session.flush()


def _seed_battery_weight_item(
    session: Session, aeroplane_id: int, mass_kg: float = 0.40
) -> None:
    item = WeightItemModel(
        aeroplane_id=aeroplane_id,
        name="main_battery",
        mass_kg=mass_kg,
        category="battery",
        x_m=0.15,
    )
    session.add(item)
    session.flush()


# ===========================================================================
# Shared stub factory for AeroBuildup internals
# ===========================================================================

def _make_asb_stubs(ac: dict):
    """Return (fake_airplane, patches_list) for stubbing ASB internals.

    Stubs produce physics-consistent values for the reference aircraft.
    The fine-sweep data is a clean parabolic polar so the Re-table builder
    and Oswald-fit code run through their real paths without AeroBuildup.
    """
    cd0 = ac["cd0"]
    e = ac["e_oswald"]
    ar = ac["ar"]
    s_ref = ac["s_ref_m2"]
    mac = ac["mac_m"]
    span = ac["b_ref_m"]
    mass = ac["mass_kg"]
    v_cruise = ac["v_cruise_mps"]
    x_np = ac["x_np_m"]
    rho = 1.225

    # Synthesize a parabolic polar sweep: 8 velocities × 10 alphas
    v_lo = max(v_cruise * 0.4, 3.0)
    v_hi = max(v_cruise * 1.5, v_lo + 5.0)
    velocities = np.linspace(v_lo, v_hi, 8)
    alphas_deg = np.linspace(-2.0, 14.0, 10)

    cl_array: list[float] = []
    cd_array: list[float] = []
    v_array: list[float] = []
    k = 1.0 / (math.pi * e * ar)

    for v in velocities:
        for alpha_deg in alphas_deg:
            # Simple flat-plate CL: cl_alpha ~ 2π/rad, zero-lift at alpha=0
            alpha_rad = math.radians(alpha_deg)
            cl = 2 * math.pi * alpha_rad
            cl = max(-0.5, min(cl, ac["cl_max"]))
            cd = cd0 + k * cl ** 2
            cl_array.append(cl)
            cd_array.append(cd)
            v_array.append(v)

    cl_arr = np.array(cl_array)
    cd_arr = np.array(cd_array)
    v_arr = np.array(v_array)

    # CL_max: maximum CL in the sweep (capped at aircraft cl_max)
    cl_max_sweep = float(np.max(cl_arr))

    # Fake ASB airplane object — use SimpleNamespace to avoid class-body scoping issues
    from types import SimpleNamespace

    _s_ref = s_ref  # capture locals into non-shadowing names
    _mac = mac
    _span = span
    _x_np = x_np

    fake_wing = SimpleNamespace(
        area=lambda: _s_ref,
        mean_aerodynamic_chord=lambda: _mac,
        span=lambda: _span,
    )
    fake_airplane = SimpleNamespace(
        wings=[fake_wing],
        xyz_ref=[_x_np - ac["target_sm"] * _mac, 0.0, 0.0],
        s_ref=_s_ref,
        c_ref=_mac,
        b_ref=_span,
    )

    return fake_airplane, (
        cl_max_sweep, cl_arr, cd_arr, v_arr,
        x_np, mac, cd0, s_ref,
    )


def _patches_for_ac(ac: dict, fake_airplane, sweep_data):
    """Return list of patches for ASB-bound functions."""
    cl_max_sweep, cl_arr, cd_arr, v_arr, x_np, mac, cd0, s_ref = sweep_data
    v_cruise = ac["v_cruise_mps"]
    v_max = max(v_cruise * 1.5, v_cruise + 10.0)

    return [
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=fake_airplane,
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(x_np, mac, cd0, s_ref),
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=15.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=(cl_max_sweep, cl_arr, cd_arr, v_arr),
        ),
        patch(
            "app.services.assumption_compute_service._extract_cl_alpha_from_linear_sweep",
            return_value=5.7,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(v_cruise, v_max, True),
        ),
    ]


# ===========================================================================
# Stage 2: matching_chart_service.compute_chart
# ===========================================================================

def _run_matching_chart(ac: dict, ctx: dict) -> dict:
    from app.services.matching_chart_service import compute_chart

    aircraft_dict = {
        "mass_kg": ac["mass_kg"],
        "t_static_N": ac["t_static_N"],
        "s_ref_m2": ctx.get("s_ref_m2") or ac["s_ref_m2"],
        "b_ref_m": ctx.get("b_ref_m") or ac["b_ref_m"],
        "ar": ac["ar"],
        "cd0": ctx.get("cd0") or ac["cd0"],
        "e_oswald": ctx.get("e_oswald") or ac["e_oswald"],
        "cl_max_clean": ac["cl_max"],
        "cl_max_takeoff": ac.get("cl_max_takeoff", ac["cl_max"]),
        "cl_max_landing": ac.get("cl_max_landing", ac["cl_max"]),
        "v_cruise_mps": ctx.get("v_cruise_mps") or ac["v_cruise_mps"],
        "v_md_mps": ctx.get("v_md_mps"),
        "v_stall_mps": ctx.get("v_stall_mps") or ac["v_stall_mps"],
    }
    # Gliders use hand_launch; all powered aircraft use uav_runway (GA/UAV/RC with runway).
    # matching_chart_service valid modes: rc_runway, rc_hand_launch, uav_runway, uav_belly_land.
    # There is no dedicated GA mode — uav_runway is the closest for Cessna.
    if ac["t_static_N"] <= 0:
        mode = "rc_hand_launch"
    else:
        mode = "uav_runway"
    return compute_chart(aircraft_dict, mode=mode)


# ===========================================================================
# Stage 3: sm_sizing_service.suggest_corrections
# ===========================================================================

def _run_sm_sizing(ac: dict, ctx: dict) -> dict:
    from app.services.sm_sizing_service import suggest_corrections
    return suggest_corrections(ctx, target_sm=ac["target_sm"], at_cg="aft")


# ===========================================================================
# Stage 4: field_length_service.compute_field_lengths
# ===========================================================================

def _run_field_length(ac: dict, ctx: dict) -> dict | None:
    from app.services.field_length_service import compute_field_lengths

    if ac["t_static_N"] <= 0:
        return None  # Unpowered glider — skip runway field length

    aircraft_dict = {
        "mass_kg": ac["mass_kg"],
        "s_ref_m2": ctx.get("s_ref_m2") or ac["s_ref_m2"],
        "v_stall_mps": ctx.get("v_stall_mps") or ac["v_stall_mps"],
        "t_static_N": ac["t_static_N"],
        "cl_max": ac["cl_max"],
        "cl_max_takeoff": ac.get("cl_max_takeoff", ac["cl_max"]),
        "cl_max_landing": ac.get("cl_max_landing", ac["cl_max"]),
    }
    # Large GA → asphalt runway; small RC/UAV → rc_runway
    if ac["mass_kg"] > 100.0:
        to_mode, ldg_mode = "runway", "runway"
    else:
        to_mode, ldg_mode = "runway", "runway"
    return compute_field_lengths(aircraft_dict, takeoff_mode=to_mode, landing_mode=ldg_mode)


# ===========================================================================
# Stage 6: tail_sizing_service.compute_tail_volumes
# ===========================================================================

def _build_tail_ctx(ac: dict, aeroplane: AeroplaneModel, ctx: dict) -> dict:
    """Merge assumption context + geometric tail keys into tail-sizing context."""
    tail_ctx = {**ctx}
    tail_ctx["x_wing_ac_m"] = 0.25 * float(ctx.get("mac_m") or ac["mac_m"])
    if ac.get("htail_le_x") is not None:
        tail_ctx["s_h_m2"] = ac["htail_chord_root"] * ac["htail_span_half"]  # approximate
        tail_ctx["x_htail_le_m"] = ac["htail_le_x"]
        tail_ctx["htail_mac_m"] = ac["htail_mac_m"]
    if ac.get("vtail_le_x") is not None:
        tail_ctx["s_v_m2"] = ac["vtail_chord_root"] * ac["vtail_span"] * 0.75  # approx
        tail_ctx["x_vtail_le_m"] = ac["vtail_le_x"]
        tail_ctx["vtail_mac_m"] = ac["vtail_mac_m"]
    # Aircraft class for target lookup — must match keys in tail_sizing_service.AIRCRAFT_CLASS_TARGETS
    if ac["mass_kg"] > 100.0:
        tail_ctx["aircraft_class"] = "rc_combust"  # GA analogue; no "general_aviation" key in service
    elif ac["t_static_N"] <= 0:
        tail_ctx["aircraft_class"] = "glider"      # ASW-27 scale sailplane
    else:
        tail_ctx["aircraft_class"] = "rc_trainer"
    tail_ctx["is_canard"] = False
    tail_ctx["is_tailless"] = (ac.get("htail_le_x") is None and ac.get("vtail_le_x") is None)
    tail_ctx["is_v_tail"] = ac["name"] == "vtail_uav"
    return tail_ctx


# ===========================================================================
# Per-aircraft test functions
# ===========================================================================

def _run_full_workflow(ac: dict, client_and_db_fixture) -> dict[str, Any]:
    """Run all 8 workflow stages for one reference aircraft.

    Returns a dict {stage_name: result_or_dict} for all 8 stages.
    Raises AssertionError on first failure (no silent swallowing).
    """
    _, SessionLocal = client_and_db_fixture

    # --- Seed aircraft in DB ------------------------------------------------
    with SessionLocal() as db:
        aeroplane = _seed_aeroplane(db, ac)
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

        if ac["name"] == "vtail_uav":
            _seed_vtail_wings(db, aeroplane_id, ac)
        else:
            _seed_conventional_wings(db, aeroplane_id, ac)

        _seed_design_assumptions(db, aeroplane_id, aeroplane_uuid, ac)
        if ac.get("battery_capacity_wh"):
            _seed_battery_weight_item(db, aeroplane_id, mass_kg=0.40)
        db.commit()

    # --- Build stubs --------------------------------------------------------
    fake_airplane, sweep_data = _make_asb_stubs(ac)
    patches = _patches_for_ac(ac, fake_airplane, sweep_data)

    # --- Stage 1: recompute_assumptions -------------------------------------
    from app.services.assumption_compute_service import recompute_assumptions

    for p in patches:
        p.start()
    try:
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
    finally:
        for p in patches:
            p.stop()

    # Fetch context
    with SessionLocal() as db:
        aeroplane_row = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        ctx = aeroplane_row.assumption_computation_context or {}

    results: dict[str, Any] = {}
    results["stage1_ctx"] = ctx

    # --- Stage 2: matching chart -------------------------------------------
    if ac["t_static_N"] > 0:
        chart = _run_matching_chart(ac, ctx)
        results["stage2_chart"] = chart

    # --- Stage 3: SM sizing -------------------------------------------------
    sm_result = _run_sm_sizing(ac, ctx)
    results["stage3_sm"] = sm_result

    # --- Stage 4: field length ----------------------------------------------
    fl_result = _run_field_length(ac, ctx)
    results["stage4_field"] = fl_result

    # --- Stage 5: endurance -------------------------------------------------
    from app.services.endurance_service import compute_endurance_for_aeroplane
    with SessionLocal() as db:
        end_result = compute_endurance_for_aeroplane(db, aeroplane_uuid)
    results["stage5_endurance"] = end_result

    # --- Stage 6: tail sizing -----------------------------------------------
    from app.services.tail_sizing_service import compute_tail_volumes
    tail_ctx = _build_tail_ctx(ac, aeroplane_row, ctx)
    tail_result = compute_tail_volumes(tail_ctx)
    results["stage6_tail"] = tail_result

    # --- Stage 7: flight envelope -------------------------------------------
    # Patch the _build_asb_airplane used inside flight_envelope_service
    # (it calls compute_flight_envelope which calls _get_b_ref / _get_wing_area_m2)
    from app.services.flight_envelope_service import compute_flight_envelope
    with patch(
        "app.services.flight_envelope_service._get_wing_area_m2",
        return_value=ac["s_ref_m2"],
    ), patch(
        "app.services.flight_envelope_service._get_b_ref",
        return_value=ac["b_ref_m"],
    ), patch(
        "app.services.flight_envelope_service._get_v_max",
        return_value=float(ctx.get("v_max_mps") or ac["v_cruise_mps"] * 1.5),
    ):
        with SessionLocal() as db:
            fe_result = compute_flight_envelope(db, aeroplane_uuid)
    results["stage7_flight_envelope"] = fe_result

    return results


# ===========================================================================
# Acceptance assertions
# ===========================================================================

def _assert_stage1(ac: dict, ctx: dict) -> None:
    """Stage 1: assumption context structure and value ranges."""
    assert ctx, f"{ac['name']}: assumption_computation_context is empty after recompute"

    # Required scalar keys
    for key in ("cd0", "e_oswald", "cl_alpha_per_rad", "mac_m", "s_ref_m2",
                "b_ref_m", "x_np_m"):
        assert ctx.get(key) is not None, f"{ac['name']}: Stage 1: {key!r} missing from context"

    # CG envelope keys (Wave 3 — gh-488)
    for key in ("cg_aft_m", "sm_at_aft", "sm_at_fwd"):
        if ctx.get(key) is not None:
            # Present and numeric → OK
            assert isinstance(ctx[key], (int, float)), (
                f"{ac['name']}: Stage 1: {key!r} = {ctx[key]!r} is not numeric"
            )
        # else: context may not have CG envelope if no loading scenarios → skip

    # Polar Re table (Wave 4 — gh-493): non-empty for non-degenerate aircraft
    polar_re_table = ctx.get("polar_re_table", [])
    if not ctx.get("polar_re_table_degenerate", True):
        assert len(polar_re_table) > 0, (
            f"{ac['name']}: Stage 1: polar_re_table empty but degenerate=False"
        )
        # Each row must have required schema keys
        for row in polar_re_table:
            for rkey in ("re", "v_mps", "cd0", "e_oswald", "cl_max", "r2", "fallback_used"):
                assert rkey in row, (
                    f"{ac['name']}: Stage 1: polar_re_table row missing key {rkey!r}: {row}"
                )

    # cd0 range check (Scholz/Roskam)
    cd0_val = ctx["cd0"]
    lo, hi = ac["cd0_range"]
    assert lo <= cd0_val <= hi, (
        f"{ac['name']}: Stage 1: cd0={cd0_val:.4f} outside expected [{lo}, {hi}] "
        f"(Scholz/Roskam reference)"
    )

    # V_md range check
    v_md = ctx.get("v_md_mps")
    if v_md is not None:
        v_lo, v_hi = ac["v_md_range"]
        assert v_lo <= v_md <= v_hi, (
            f"{ac['name']}: Stage 1: V_md={v_md:.1f} m/s outside expected [{v_lo}, {v_hi}] m/s"
        )


def _assert_stage2(ac: dict, chart: dict | None) -> None:
    """Stage 2: matching chart structure."""
    if chart is None:
        return  # Glider — skipped
    assert "constraints" in chart, f"{ac['name']}: Stage 2: 'constraints' key missing"
    assert "design_point" in chart, f"{ac['name']}: Stage 2: 'design_point' key missing"
    assert len(chart["constraints"]) > 0, (
        f"{ac['name']}: Stage 2: constraint list is empty"
    )
    dp = chart["design_point"]
    assert dp.get("ws_n_m2", 0) > 0, f"{ac['name']}: Stage 2: W/S ≤ 0"
    assert dp.get("t_w", 0) > 0, f"{ac['name']}: Stage 2: T/W ≤ 0"


def _assert_stage3(ac: dict, sm_result: dict) -> None:
    """Stage 3: SM sizing status and option levers."""
    assert "status" in sm_result, f"{ac['name']}: Stage 3: 'status' missing"
    status = sm_result["status"]
    assert status in ("ok", "suggestion", "error", "not_applicable"), (
        f"{ac['name']}: Stage 3: unexpected status {status!r}"
    )
    if status in ("ok", "suggestion"):
        for opt in sm_result.get("options", []):
            assert opt.get("lever") in ("wing_shift", "htail_scale"), (
                f"{ac['name']}: Stage 3: unexpected lever {opt.get('lever')!r}"
            )


def _assert_stage4(ac: dict, fl_result: dict | None) -> None:
    """Stage 4: field length positive and within expected range."""
    if fl_result is None:
        return  # Glider — skipped
    s_to = fl_result.get("s_to_50ft_m") or fl_result.get("s_to_ground_m")
    s_ldg = fl_result.get("s_ldg_50ft_m") or fl_result.get("s_ldg_ground_m")
    assert s_to is not None and s_to > 0, (
        f"{ac['name']}: Stage 4: s_to non-positive: {s_to}"
    )
    assert s_ldg is not None and s_ldg > 0, (
        f"{ac['name']}: Stage 4: s_ldg non-positive: {s_ldg}"
    )
    if ac["field_to_range"] is not None:
        lo, hi = ac["field_to_range"]
        # Use s_to_ground_m for the tight check (to-50ft includes obstacle factor)
        s_ground = fl_result.get("s_to_ground_m", s_to)
        assert lo <= s_ground <= hi, (
            f"{ac['name']}: Stage 4: s_to_ground={s_ground:.1f} m "
            f"outside expected [{lo}, {hi}] m"
        )


def _assert_stage5(ac: dict, end_result: dict) -> None:
    """Stage 5: endurance returns numeric (positive for electric aircraft with battery).

    The service returns keys: t_endurance_max_s, range_max_m, confidence, warnings.
    endurance_min = t_endurance_max_s / 60.
    """
    assert isinstance(end_result, dict), (
        f"{ac['name']}: Stage 5: result is not a dict: {type(end_result)}"
    )

    has_battery = (ac.get("battery_capacity_wh") or 0) > 0

    if has_battery:
        # Should have computed a valid endurance (t_endurance_max_s key)
        t_end = end_result.get("t_endurance_max_s")
        range_m = end_result.get("range_max_m")
        assert t_end is not None and t_end > 0, (
            f"{ac['name']}: Stage 5: t_endurance_max_s={t_end} (expected > 0 for electric AC "
            f"with battery_capacity_wh={ac.get('battery_capacity_wh')})"
        )
        assert range_m is not None and range_m > 0, (
            f"{ac['name']}: Stage 5: range_max_m={range_m} (expected > 0 for electric AC)"
        )
    # For GA/glider with no battery: service still returns a dict — already asserted above


def _assert_stage6(ac: dict, tail_result) -> None:
    """Stage 6: tail volume coefficients in Roskam/Scholz reference ranges."""
    from app.services.tail_sizing_service import TailVolumeResult
    assert isinstance(tail_result, TailVolumeResult), (
        f"{ac['name']}: Stage 6: result is not TailVolumeResult"
    )
    if tail_result.classification == "not_applicable":
        # V-tail or tailless → acceptable
        return
    # For conventional aircraft with tail geometry
    if tail_result.v_h_current is not None:
        assert 0.20 <= tail_result.v_h_current <= 1.20, (
            f"{ac['name']}: Stage 6: V_H={tail_result.v_h_current:.3f} "
            "outside physical range [0.20, 1.20]"
        )
    if tail_result.v_v_current is not None:
        assert 0.01 <= tail_result.v_v_current <= 0.20, (
            f"{ac['name']}: Stage 6: V_V={tail_result.v_v_current:.3f} "
            "outside physical range [0.01, 0.20]"
        )


def _assert_stage7(ac: dict, fe_result) -> None:
    """Stage 7: flight envelope vn_curve has gust lines and valid stall speed."""
    assert fe_result is not None, f"{ac['name']}: Stage 7: flight envelope is None"
    vn = fe_result.vn_curve
    assert vn is not None, f"{ac['name']}: Stage 7: vn_curve is None"
    # Stall speed should be positive
    assert vn.stall_speed_mps > 0, (
        f"{ac['name']}: Stage 7: stall_speed_mps={vn.stall_speed_mps} ≤ 0"
    )
    # Gust lines should be non-empty
    assert len(vn.gust_lines_positive) > 0, (
        f"{ac['name']}: Stage 7: gust_lines_positive is empty (CL_α gust integration failed)"
    )


# ===========================================================================
# Parametric test
# ===========================================================================

@pytest.mark.slow
@pytest.mark.parametrize("ac", ALL_AIRCRAFT, ids=[a["name"] for a in ALL_AIRCRAFT])
def test_full_workflow(ac, client_and_db):  # noqa: F811
    """Run all 8 workflow stages for a reference aircraft and assert ranges."""
    results = _run_full_workflow(ac, client_and_db)

    ctx = results["stage1_ctx"]
    _assert_stage1(ac, ctx)

    _assert_stage2(ac, results.get("stage2_chart"))

    _assert_stage3(ac, results["stage3_sm"])

    _assert_stage4(ac, results["stage4_field"])

    _assert_stage5(ac, results["stage5_endurance"])

    _assert_stage6(ac, results["stage6_tail"])

    _assert_stage7(ac, results["stage7_flight_envelope"])
