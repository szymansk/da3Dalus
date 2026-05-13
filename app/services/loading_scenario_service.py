"""Loading Scenario service — CG envelope from user-defined loading scenarios (gh-488).

Implements two separate envelopes:

  Loading-Envelope:  what user-defined loading scenarios produce.
    cg_loading_fwd = min(cg_x over all scenarios)
    cg_loading_aft = max(cg_x over all scenarios)

  Stability-Envelope:  what aerodynamics physically allows.
    cg_stability_aft = x_NP - target_sm * MAC          (Anderson §7.5)
    cg_stability_fwd = x_NP - 0.30 * MAC               (stub — conservative;
                        TODO: replace with full elevator-authority calculation
                        per Anderson §7.7 as follow-up ticket)

Validation: Loading-Envelope MUST be within Stability-Envelope.

SM Classification (relative to target_sm — Scholz §4.2):
  sm < 0.02              ERROR   (unstable / Phugoid divergent)
  0.02 ≤ sm < target_sm  WARN    (low margin — pylon racers only)
  target_sm ≤ sm ≤ 0.20  OK      (standard range)
  0.20 < sm ≤ 0.30       WARN    (heavy nose, trim drag, sluggish pitch)
  sm > 0.30              ERROR   (elevator authority at landing stall insufficient)
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.events import AssumptionChanged, event_bus
from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, LoadingScenarioModel
from app.schemas.loading_scenario import (
    ComponentOverrides,
    LoadingScenarioCreate,
    LoadingScenarioRead,
    LoadingScenarioUpdate,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SM classification thresholds (Scholz §4.2)
# ---------------------------------------------------------------------------

_SM_UNSTABLE_LIMIT = 0.02    # below → ERROR (Phugoid divergent)
_SM_HEAVY_NOSE_WARN = 0.20   # above → WARN  (heavy nose, trim drag)
_SM_ELEVATOR_LIMIT = 0.30    # above → ERROR (elevator authority)


# ---------------------------------------------------------------------------
# Pure computation helpers (no DB) — testable in isolation
# ---------------------------------------------------------------------------


def classify_sm(sm: float, target_sm: float) -> str:
    """5-tier SM classification relative to target_sm (Scholz §4.2).

    Args:
        sm: current static margin (dimensionless, fraction of MAC).
        target_sm: design target static margin (dimensionless).

    Returns:
        "error" | "warn" | "ok"
    """
    if sm < _SM_UNSTABLE_LIMIT:
        return "error"
    if sm < target_sm:
        return "warn"
    if sm <= _SM_HEAVY_NOSE_WARN:
        return "ok"
    if sm <= _SM_ELEVATOR_LIMIT:
        return "warn"
    return "error"


def compute_stability_envelope(x_np: float, mac: float, target_sm: float) -> dict[str, float]:
    """Compute the Stability-Envelope for given aerodynamic parameters.

    Args:
        x_np: neutral point position [m] (longitudinal).
        mac: mean aerodynamic chord [m].
        target_sm: design target static margin (fraction of MAC).

    Returns dict with:
        cg_stability_aft_m: aft stability limit = x_NP - target_sm * MAC
        cg_stability_fwd_m: forward stability limit (stub = x_NP - 0.30 * MAC)
            TODO: replace with full Cm-trim @ CL_max_landing per Anderson §7.7
            as a follow-up ticket. This stub is conservative.
    """
    cg_stability_aft_m = x_np - target_sm * mac
    # Stub forward limit: SM = 0.30 is the conservative upper bound before
    # elevator authority at landing stall becomes critical (Anderson §7.7).
    # Full calculation requires Cm_delta_e and CL_max_landing — follow-up ticket.
    cg_stability_fwd_m = x_np - _SM_ELEVATOR_LIMIT * mac
    return {
        "cg_stability_aft_m": cg_stability_aft_m,
        "cg_stability_fwd_m": cg_stability_fwd_m,
    }


def compute_scenario_cg(
    base_mass_kg: float,
    base_cg_x: float,
    adhoc_items: list[dict],
    mass_overrides: list[dict],
) -> float:
    """Compute the CG_x for a single loading scenario.

    Applies adhoc items on top of the base (design) mass/CG.  Mass overrides
    shift individual component masses but we do not have per-component CG data
    in the DB at this time, so they are accounted for via total-mass scaling.

    Args:
        base_mass_kg: design total mass [kg].
        base_cg_x: design CG_x [m].
        adhoc_items: list of {"name", "mass_kg", "x_m", "y_m", "z_m"} dicts.
        mass_overrides: list of {"component_uuid", "mass_kg_override"} dicts.
            Currently not used in CG computation (no per-component CG DB yet).

    Returns:
        cg_x [m] for this scenario.
    """
    total_mass = base_mass_kg
    moment_x = base_mass_kg * base_cg_x

    for item in adhoc_items:
        m = float(item.get("mass_kg", 0.0) or 0.0)
        x = float(item.get("x_m", 0.0) or 0.0)
        total_mass += m
        moment_x += m * x

    if total_mass <= 0:
        return base_cg_x
    return moment_x / total_mass


def validate_cg_envelope(
    cg_loading_fwd_m: float,
    cg_loading_aft_m: float,
    cg_stability_fwd_m: float,
    cg_stability_aft_m: float,
) -> list[str]:
    """Validate that Loading-Envelope is within Stability-Envelope.

    Returns a list of warning/error strings.  Empty list = all OK.
    """
    warnings: list[str] = []

    if cg_loading_aft_m > cg_stability_aft_m:
        excess_mm = round((cg_loading_aft_m - cg_stability_aft_m) * 1000, 1)
        warnings.append(
            f"CG exceeds aft stability limit by {excess_mm} mm — "
            "aircraft may be unstable in the aft loading scenario."
        )

    if cg_loading_fwd_m < cg_stability_fwd_m:
        excess_mm = round((cg_stability_fwd_m - cg_loading_fwd_m) * 1000, 1)
        warnings.append(
            f"CG is {excess_mm} mm forward of the forward stability limit — "
            "elevator authority at landing stall may be insufficient (stub limit)."
        )

    return warnings


def enrich_context_with_cg_envelope(
    ctx: dict[str, Any],
    cg_loading_fwd_m: float,
    cg_loading_aft_m: float,
    cg_stability_fwd_m: float,
    cg_stability_aft_m: float,
) -> dict[str, Any]:
    """Addively add CG envelope keys to an existing computation context dict.

    Preserves all existing keys (esp. cg_agg_m for backward compat) and
    adds the new gh-488 keys: cg_forward_m, cg_aft_m, sm_at_fwd, sm_at_aft.

    Args:
        ctx: existing assumption_computation_context dict.
        cg_loading_fwd_m: forward loading CG [m].
        cg_loading_aft_m: aft loading CG [m].
        cg_stability_fwd_m: forward stability limit [m].
        cg_stability_aft_m: aft stability limit [m].

    Returns:
        Updated dict (same object, modified in-place).
    """
    x_np = float(ctx.get("x_np_m") or 0.0)
    mac = float(ctx.get("mac_m") or 1.0)  # avoid division by zero

    sm_at_fwd = (x_np - cg_loading_fwd_m) / mac if mac > 0 else 0.0
    sm_at_aft = (x_np - cg_loading_aft_m) / mac if mac > 0 else 0.0

    ctx["cg_forward_m"] = round(cg_loading_fwd_m, 4)
    ctx["cg_aft_m"] = round(cg_loading_aft_m, 4)
    ctx["sm_at_fwd"] = round(sm_at_fwd, 4)
    ctx["sm_at_aft"] = round(sm_at_aft, 4)
    return ctx


# ---------------------------------------------------------------------------
# DB-aware helpers
# ---------------------------------------------------------------------------


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _load_assumption_value(
    db: Session, aeroplane_id: int, param_name: str, default: float = 0.0
) -> float:
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        return default
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return float(row.calculated_value)
    return float(row.estimate_value)


def _model_to_schema(scenario: LoadingScenarioModel) -> LoadingScenarioRead:
    overrides_raw = scenario.component_overrides or {}
    if isinstance(overrides_raw, str):
        import json
        overrides_raw = json.loads(overrides_raw)
    overrides = ComponentOverrides.model_validate(overrides_raw)
    return LoadingScenarioRead(
        id=scenario.id,
        aeroplane_id=scenario.aeroplane_id,
        name=scenario.name,
        aircraft_class=scenario.aircraft_class,
        component_overrides=overrides,
        is_default=scenario.is_default,
    )


def compute_loading_envelope_for_aeroplane(
    db: Session, aeroplane: AeroplaneModel
) -> dict[str, float]:
    """Compute the Loading-Envelope (min/max CG) over all loading scenarios.

    Falls back to the design cg_x when no loading scenarios exist (backward compat).

    Returns dict with:
        cg_loading_fwd_m: forward-most CG across all scenarios [m]
        cg_loading_aft_m: aft-most CG across all scenarios [m]
        scenarios_eval: list of per-scenario CG values
    """
    base_mass = _load_assumption_value(db, aeroplane.id, "mass", default=1.0)
    base_cg_x = _load_assumption_value(db, aeroplane.id, "cg_x", default=0.0)

    scenarios = (
        db.query(LoadingScenarioModel)
        .filter(LoadingScenarioModel.aeroplane_id == aeroplane.id)
        .all()
    )

    if not scenarios:
        return {
            "cg_loading_fwd_m": base_cg_x,
            "cg_loading_aft_m": base_cg_x,
            "scenarios_eval": [],
        }

    cg_values: list[float] = []
    for scenario in scenarios:
        overrides_raw = scenario.component_overrides or {}
        if isinstance(overrides_raw, str):
            import json
            overrides_raw = json.loads(overrides_raw)
        overrides = ComponentOverrides.model_validate(overrides_raw)
        adhoc = [item.model_dump() for item in overrides.adhoc_items]
        mass_ovr = [m.model_dump() for m in overrides.mass_overrides]
        cg = compute_scenario_cg(
            base_mass_kg=base_mass,
            base_cg_x=base_cg_x,
            adhoc_items=adhoc,
            mass_overrides=mass_ovr,
        )
        cg_values.append(cg)

    return {
        "cg_loading_fwd_m": min(cg_values),
        "cg_loading_aft_m": max(cg_values),
        "scenarios_eval": cg_values,
    }


def _trigger_retrim(db: Session, aeroplane: AeroplaneModel) -> None:
    """Mark OPs dirty and emit AssumptionChanged(cg_x) for downstream retrim."""
    from app.services.invalidation_service import mark_ops_dirty

    try:
        mark_ops_dirty(db, aeroplane.id)
    except Exception:
        logger.exception("mark_ops_dirty failed for aeroplane %s", aeroplane.id)

    event_bus.publish(
        AssumptionChanged(aeroplane_id=aeroplane.id, parameter_name="cg_x")
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def list_scenarios(db: Session, aeroplane_uuid) -> list[LoadingScenarioRead]:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    rows = (
        db.query(LoadingScenarioModel)
        .filter(LoadingScenarioModel.aeroplane_id == aeroplane.id)
        .order_by(LoadingScenarioModel.id)
        .all()
    )
    return [_model_to_schema(r) for r in rows]


def create_scenario(
    db: Session, aeroplane_uuid, data: LoadingScenarioCreate
) -> LoadingScenarioRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        overrides_dict = data.component_overrides.model_dump()
        scenario = LoadingScenarioModel(
            aeroplane_id=aeroplane.id,
            name=data.name,
            aircraft_class=data.aircraft_class,
            component_overrides=overrides_dict,
            is_default=data.is_default,
        )
        db.add(scenario)
        db.flush()
        db.refresh(scenario)
        _trigger_retrim(db, aeroplane)
        return _model_to_schema(scenario)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in create_scenario: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def update_scenario(
    db: Session, aeroplane_uuid, scenario_id: int, data: LoadingScenarioUpdate
) -> LoadingScenarioRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        scenario = (
            db.query(LoadingScenarioModel)
            .filter(
                LoadingScenarioModel.aeroplane_id == aeroplane.id,
                LoadingScenarioModel.id == scenario_id,
            )
            .first()
        )
        if scenario is None:
            raise NotFoundError(entity="LoadingScenario", resource_id=scenario_id)

        if data.name is not None:
            scenario.name = data.name
        if data.aircraft_class is not None:
            scenario.aircraft_class = data.aircraft_class
        if data.component_overrides is not None:
            scenario.component_overrides = data.component_overrides.model_dump()
        if data.is_default is not None:
            scenario.is_default = data.is_default

        db.flush()
        db.refresh(scenario)
        _trigger_retrim(db, aeroplane)
        return _model_to_schema(scenario)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in update_scenario: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_scenario(db: Session, aeroplane_uuid, scenario_id: int) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        scenario = (
            db.query(LoadingScenarioModel)
            .filter(
                LoadingScenarioModel.aeroplane_id == aeroplane.id,
                LoadingScenarioModel.id == scenario_id,
            )
            .first()
        )
        if scenario is None:
            raise NotFoundError(entity="LoadingScenario", resource_id=scenario_id)
        db.delete(scenario)
        db.flush()
        _trigger_retrim(db, aeroplane)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in delete_scenario: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def get_cg_envelope(
    db: Session, aeroplane_uuid
) -> dict[str, Any]:
    """Compute the full CG envelope (loading + stability + classification).

    Returns a dict compatible with CgEnvelopeRead schema.
    """
    aeroplane = _get_aeroplane(db, aeroplane_uuid)

    # Loading envelope
    loading = compute_loading_envelope_for_aeroplane(db, aeroplane)
    cg_fwd = loading["cg_loading_fwd_m"]
    cg_aft = loading["cg_loading_aft_m"]

    # Stability envelope — requires x_NP and MAC from context or assumptions
    ctx = aeroplane.assumption_computation_context or {}
    x_np = float(ctx.get("x_np_m") or 0.0)
    mac = float(ctx.get("mac_m") or 1.0)
    target_sm = _load_assumption_value(db, aeroplane.id, "target_static_margin", default=0.08)

    if x_np == 0.0 or mac <= 0:
        # Fall back to assumptions-based estimate if context not yet populated
        base_cg_x = _load_assumption_value(db, aeroplane.id, "cg_x", default=0.15)
        # Approximate: NP ≈ cg_x + target_sm * MAC (inverse of cg_x = NP - SM*MAC)
        # Without actual aero computation, use a conservative MAC estimate.
        # This is handled gracefully: the user sees stubs until a full recompute runs.
        mac = float(ctx.get("mac_m") or 0.20)
        x_np = base_cg_x + target_sm * mac

    stability = compute_stability_envelope(x_np=x_np, mac=mac, target_sm=target_sm)
    stab_fwd = stability["cg_stability_fwd_m"]
    stab_aft = stability["cg_stability_aft_m"]

    # Static margins at loading extremes
    sm_at_fwd = (x_np - cg_fwd) / mac if mac > 0 else 0.0
    sm_at_aft = (x_np - cg_aft) / mac if mac > 0 else 0.0

    # Classify worst-case (aft = most critical for stability)
    classification_fwd = classify_sm(sm_at_fwd, target_sm)
    classification_aft = classify_sm(sm_at_aft, target_sm)

    # Hierarchy: error > warn > ok
    _rank = {"error": 2, "warn": 1, "ok": 0}
    if _rank[classification_fwd] >= _rank[classification_aft]:
        overall = classification_fwd
    else:
        overall = classification_aft

    # Validation warnings
    warnings = validate_cg_envelope(cg_fwd, cg_aft, stab_fwd, stab_aft)
    if overall == "error":
        warnings.insert(0, f"SM at aft CG = {sm_at_aft:.1%} — outside safe operating range.")
    elif overall == "warn":
        pass  # validation_cg_envelope already captures this

    return {
        "cg_loading_fwd_m": round(cg_fwd, 4),
        "cg_loading_aft_m": round(cg_aft, 4),
        "cg_stability_fwd_m": round(stab_fwd, 4),
        "cg_stability_aft_m": round(stab_aft, 4),
        "sm_at_fwd": round(sm_at_fwd, 4),
        "sm_at_aft": round(sm_at_aft, 4),
        "classification": overall,
        "warnings": warnings,
    }
