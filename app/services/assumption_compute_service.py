"""Assumption compute service — gh-465.

Single public entry point: recompute_assumptions(db, aeroplane_uuid).

Runs a two-phase AeroSandbox AeroBuildup sweep:
  Phase 1 — stability run at cruise → (x_np, MAC, CD0)
  Phase 2 — coarse alpha sweep → stall_alpha; fine alpha×velocity sweep → CL_max

Writes cl_max, cd0, cg_x back to the design_assumptions table and caches
the computation context (v_cruise, Re, MAC, NP, SM, CG_agg) on the
aeroplane row for the UI Info Chip Row.

This is a sync function. Callers from async context MUST wrap with
asyncio.to_thread().
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.api.utils import analyse_aerodynamics
from app.converters.model_schema_converters import (
    aeroplane_model_to_aeroplane_schema_async,
    aeroplane_schema_to_asb_airplane_async,
)
from app.core.events import AssumptionChanged, event_bus
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, WeightItemModel
from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.services.design_assumptions_service import (
    _get_aeroplane,
    seed_defaults,
    update_calculated_value,
)
from app.services.mass_cg_service import aggregate_weight_items
from app.services.stability_service import _scalar

logger = logging.getLogger(__name__)


def recompute_assumptions(db: Session, aeroplane_uuid) -> None:
    """Recompute cl_max, cd0, cg_x from geometry via AeroSandbox.

    Sync function — caller MUST wrap in asyncio.to_thread() when invoked
    from async context (see app/main.py recompute wrapper).

    Skips silently if aircraft has no wings.
    """
    aircraft = _get_aeroplane(db, aeroplane_uuid)
    asb_airplane = _build_asb_airplane(aircraft)

    if not asb_airplane.wings:
        logger.info(
            "No wings on aircraft %s — skipping assumption recompute", aeroplane_uuid
        )
        return

    # Override ASB's reference area / chord / span so all CL/CD numbers
    # produced by AeroBuildup are normalised by the MAIN WING. ASB's
    # default is the first wing in the list, which may be a tail or
    # rudder for unusual orderings — that produces wildly inflated CL_max.
    main_wing = _select_main_wing(asb_airplane)
    if main_wing is not None:
        asb_airplane.s_ref = float(main_wing.area())
        asb_airplane.c_ref = float(main_wing.mean_aerodynamic_chord())
        asb_airplane.b_ref = float(main_wing.span())

    # Ensure assumption rows + computation config exist (idempotent).
    # Wings can be created before the user opens the Assumptions tab,
    # so we cannot rely on the user having seeded them already.
    seed_defaults(db, aeroplane_uuid)

    config = _load_or_create_config(db, aircraft.id)
    v_cruise, v_max = _load_flight_profile_speeds(db, aircraft)

    try:
        x_np, mac, cd0, s_ref = _stability_run_at_cruise(asb_airplane, v_cruise)
        stall_alpha = _coarse_alpha_sweep(asb_airplane, v_cruise, config)
        cl_max = _fine_sweep_cl_max(asb_airplane, stall_alpha, v_cruise, v_max, config)
    except Exception:
        logger.exception(
            "AeroBuildup failed during recompute for aircraft %s — aborting", aeroplane_uuid
        )
        return

    target_sm = _load_effective_assumption(db, aircraft.id, "target_static_margin")
    cg_x = x_np - target_sm * mac

    old_cg = _get_current_calculated_value(db, aircraft.id, "cg_x")

    update_calculated_value(
        db, aeroplane_uuid, "cl_max", round(cl_max, 4), "aerobuildup",
        auto_switch_source=True,
    )
    update_calculated_value(
        db, aeroplane_uuid, "cd0", round(cd0, 5), "aerobuildup",
        auto_switch_source=True,
    )
    update_calculated_value(
        db, aeroplane_uuid, "cg_x", round(cg_x, 4), "aerobuildup",
        auto_switch_source=True,
    )

    cg_agg = _load_cg_agg(db, aircraft.id)
    re = _reynolds_number(v_cruise, mac)
    mass = _load_effective_assumption(db, aircraft.id, "mass")
    v_stall = _stall_speed(mass, s_ref, cl_max)

    _cache_context(db, aircraft, {
        "v_cruise_mps": v_cruise,
        "v_max_mps": round(v_max, 1),
        "v_stall_mps": round(v_stall, 1) if v_stall is not None else None,
        "reynolds": round(re),
        "mac_m": round(mac, 4),
        "s_ref_m2": round(s_ref, 4),
        "x_np_m": round(x_np, 4),
        "target_static_margin": target_sm,
        "cg_agg_m": round(cg_agg, 4) if cg_agg is not None else None,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    })

    if old_cg is None or abs(cg_x - old_cg) > 1e-6:
        # Mirror update_assumption: mark OPs DIRTY in the same transaction
        # before emitting AssumptionChanged. Otherwise the retrim handler
        # finds no DIRTY ops and does nothing.
        from app.services.invalidation_service import mark_ops_dirty

        mark_ops_dirty(db, aircraft.id)
        event_bus.publish(
            AssumptionChanged(aeroplane_id=aircraft.id, parameter_name="cg_x")
        )


def _build_asb_airplane(aircraft: AeroplaneModel):
    schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
    return aeroplane_schema_to_asb_airplane_async(plane_schema=schema)


def _load_or_create_config(
    db: Session, aeroplane_id: int
) -> AircraftComputationConfigModel:
    config = (
        db.query(AircraftComputationConfigModel)
        .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
        .first()
    )
    if config is None:
        config = AircraftComputationConfigModel(
            aeroplane_id=aeroplane_id, **COMPUTATION_CONFIG_DEFAULTS
        )
        db.add(config)
        db.flush()
    return config


def _load_flight_profile_speeds(
    db: Session, aircraft: AeroplaneModel
) -> tuple[float, float]:
    from app.services.operating_point_generator_service import (
        _load_effective_flight_profile,
    )

    profile, _ = _load_effective_flight_profile(db, aircraft)
    goals = profile.get("goals", {})
    cruise = float(goals.get("cruise_speed_mps", 18.0))
    v_max = float(
        goals.get("max_level_speed_mps") or max(1.35 * cruise, cruise + 8.0)
    )
    return cruise, v_max


def _select_main_wing(asb_airplane):
    """Pick the main wing — the wing with the largest planform area.

    A typical configuration has main wing + horizontal tail + vertical
    tail. ASB's `reference.Cref` defaults to the FIRST wing in the list,
    which may not be the main wing for the user's geometry. Picking by
    planform area is robust across user-defined wing orderings.
    """
    if not asb_airplane.wings:
        return None
    return max(asb_airplane.wings, key=lambda w: float(w.area()))


def _stability_run_at_cruise(
    asb_airplane, v_cruise: float
) -> tuple[float, float, float, float]:
    """Returns (x_np, MAC, CD0, S_ref).

    Uses analyse_aerodynamics → AnalysisModel for x_np and CD0 (same
    path as stability_service, keeps NP consistent across the app).

    For MAC and S_ref, takes the **main wing** (largest planform area)
    rather than ASB's reference. The reference may point at a tail or
    rudder for unusual wing orderings.
    """
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    op_schema = OperatingPointSchema(velocity=v_cruise, alpha=0.0, xyz_ref=xyz_ref)
    result, _ = analyse_aerodynamics(
        AnalysisToolUrlType.AEROBUILDUP, op_schema, asb_airplane
    )
    x_np = _scalar(result.reference.Xnp)
    cd0 = _scalar(result.coefficients.CD)

    main_wing = _select_main_wing(asb_airplane)
    if main_wing is None:
        raise ValueError("Cannot compute MAC: no wings on aircraft")
    mac = float(main_wing.mean_aerodynamic_chord())
    s_ref = float(main_wing.area())

    if x_np is None or cd0 is None or mac <= 0 or s_ref <= 0:
        raise ValueError("AeroBuildup returned NULL or non-positive values")
    return float(x_np), mac, float(cd0), s_ref


def _coarse_alpha_sweep(
    asb_airplane, v_cruise: float, config: AircraftComputationConfigModel
) -> float:
    """Returns approximate stall_alpha_deg (alpha where CL peaks)."""
    import aerosandbox as asb

    alphas = np.arange(
        config.coarse_alpha_min_deg,
        config.coarse_alpha_max_deg + 0.01,
        config.coarse_alpha_step_deg,
    )
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    cls: list[float] = []
    for a in alphas:
        op = asb.OperatingPoint(velocity=v_cruise, alpha=float(a))
        abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
        r = abu.run()
        cls.append(_extract_scalar(r, "CL", default=0.0))
    return float(alphas[int(np.argmax(cls))])


def _fine_sweep_cl_max(
    asb_airplane,
    stall_alpha_deg: float,
    v_cruise: float,
    v_max: float,
    config: AircraftComputationConfigModel,
) -> float:
    """Returns CL_max from a fine alpha × velocity sweep."""
    import aerosandbox as asb

    alpha_min = stall_alpha_deg - config.fine_alpha_margin_deg
    alpha_max = stall_alpha_deg + config.fine_alpha_margin_deg
    alphas = np.arange(alpha_min, alpha_max + 0.01, config.fine_alpha_step_deg)

    v_stall_approx = max(v_cruise * 0.5, 3.0)
    velocities = np.linspace(v_stall_approx, v_max, config.fine_velocity_count)

    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    cl_max = -float("inf")
    for v in velocities:
        for a in alphas:
            op = asb.OperatingPoint(velocity=float(v), alpha=float(a))
            abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
            r = abu.run()
            cl = _extract_scalar(r, "CL", default=0.0)
            if cl > cl_max:
                cl_max = cl
    return float(cl_max)


def _extract_scalar(result: Any, key: str, *, default: float) -> float:
    """Extract a CL/CD scalar from raw AeroBuildup result (dict or object)."""
    if isinstance(result, dict):
        val = result.get(key)
    else:
        val = getattr(result, key, None)
    scalar = _scalar(val)
    return float(scalar) if scalar is not None else default


def _load_effective_assumption(
    db: Session, aeroplane_id: int, param_name: str
) -> float:
    """Return the effective value of a design assumption (calculated or estimate)."""
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        return PARAMETER_DEFAULTS.get(param_name, 0.0)
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return row.calculated_value
    return row.estimate_value


def _get_current_calculated_value(
    db: Session, aeroplane_id: int, param_name: str
) -> float | None:
    """Return the current calculated_value for a design assumption, or None."""
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    return row.calculated_value if row else None


def _load_cg_agg(db: Session, aeroplane_id: int) -> float | None:
    """Return mass-weighted CG x from weight items, or None if no items exist."""
    rows = (
        db.query(WeightItemModel)
        .filter(WeightItemModel.aeroplane_id == aeroplane_id)
        .all()
    )
    if not rows:
        return None
    items = [
        {"mass_kg": r.mass_kg, "x_m": r.x_m, "y_m": r.y_m, "z_m": r.z_m}
        for r in rows
    ]
    _, cg_x, _, _ = aggregate_weight_items(items)
    return cg_x


def _reynolds_number(
    velocity: float, mac: float, rho: float = 1.225, mu: float = 1.81e-5
) -> float:
    """Sea-level standard atmosphere Reynolds number.

    Sufficient for the UI chip; not altitude-aware. Operating points use
    their own atmosphere model.
    """
    return rho * velocity * mac / mu


def _stall_speed(
    mass_kg: float,
    s_ref_m2: float,
    cl_max: float,
    rho: float = 1.225,
    g: float = 9.81,
) -> float | None:
    """Sea-level stall speed: V_stall = sqrt(2 W / (rho S CL_max)).

    Returns None when CL_max or S_ref is non-positive. The 0.5 floor on
    CL_max prevents wildly inflated stall speeds when AeroBuildup
    misjudges stall on degenerate geometry.
    """
    if s_ref_m2 <= 0 or cl_max <= 0:
        return None
    cl_max_safe = max(cl_max, 0.5)
    weight_n = mass_kg * g
    return float(np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_max_safe)))


def _cache_context(
    db: Session, aircraft: AeroplaneModel, context: dict[str, Any]
) -> None:
    """Write computation context JSON to the aeroplane row."""
    aircraft.assumption_computation_context = context
    db.flush()
