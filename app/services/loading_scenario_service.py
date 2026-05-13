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

import json
import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.events import AssumptionChanged, event_bus
from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, LoadingScenarioModel
from app.schemas.loading_scenario import (
    CgEnvelopeRead,
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


def classify_sm(sm: float | None, target_sm: float) -> str:
    """5-tier SM classification relative to target_sm (Scholz §4.2).

    Args:
        sm: current static margin (dimensionless, fraction of MAC), or None.
        target_sm: design target static margin (dimensionless).

    Returns:
        "error" | "warn" | "ok" | "unknown"
    """
    if sm is None:
        return "unknown"
    if sm < _SM_UNSTABLE_LIMIT:
        return "error"
    if sm < target_sm:
        return "warn"
    if sm <= _SM_HEAVY_NOSE_WARN:
        return "ok"
    if sm <= _SM_ELEVATOR_LIMIT:
        return "warn"
    return "error"


def compute_stability_envelope(
    x_np: float | None, mac: float | None, target_sm: float
) -> dict[str, float | None]:
    """Compute the Stability-Envelope for given aerodynamic parameters.

    Returns None values when x_np or mac is unavailable (recompute_assumptions
    hasn't run yet).  The caller must surface those None values to the user
    instead of synthesising a deceptive fallback.

    Args:
        x_np: neutral point position [m] (longitudinal), or None.
        mac: mean aerodynamic chord [m], or None.
        target_sm: design target static margin (fraction of MAC).

    Returns dict with:
        cg_stability_aft_m: aft stability limit = x_NP - target_sm * MAC, or None.
        cg_stability_fwd_m: forward stability limit (stub = x_NP - 0.30 * MAC), or None.
            TODO: replace with full Cm-trim @ CL_max_landing per Anderson §7.7
            as a follow-up ticket. This stub is conservative.
    """
    if x_np is None or mac is None or mac <= 0:
        return {"cg_stability_aft_m": None, "cg_stability_fwd_m": None}

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
    toggles: list[dict] | None = None,
    position_overrides: list[dict] | None = None,
    components: list[dict] | None = None,
) -> float:
    """Compute the CG_x for a single loading scenario.

    Supports all four override types: toggles, mass_overrides, position_overrides,
    adhoc_items.  When ``components`` is provided (a list of per-component dicts with
    ``id``, ``mass_kg``, ``x_m`` fields), the function builds the moment sum from
    the individual components and applies overrides per-component.  When
    ``components`` is None or empty, falls back to the legacy base_mass / base_cg_x
    aggregation (backward-compat for pre-migration aeroplanes).

    Args:
        base_mass_kg: design total mass [kg] — used as fallback when no components.
        base_cg_x: design CG_x [m] — used as fallback when no components.
        adhoc_items: list of {"name", "mass_kg", "x_m", "y_m", "z_m"} dicts.
        mass_overrides: list of {"component_uuid", "mass_kg_override"} dicts.
        toggles: list of {"component_uuid", "enabled"} dicts. enabled=False removes
            the component from the CG computation.
        position_overrides: list of {"component_uuid", "x_m_override", ...} dicts.
        components: per-component weight list with fields ``id`` (str), ``mass_kg``,
            ``x_m``.  When provided, base_mass_kg/base_cg_x are ignored.

    Returns:
        cg_x [m] for this scenario.
    """
    toggles = toggles or []
    position_overrides = position_overrides or []

    # Build lookup maps for fast override access
    disabled_uuids: set[str] = {
        t["component_uuid"] for t in toggles if not t.get("enabled", True)
    }
    mass_ovr_map: dict[str, float] = {
        m["component_uuid"]: float(m["mass_kg_override"])
        for m in mass_overrides
    }
    pos_ovr_map: dict[str, float] = {
        p["component_uuid"]: float(p["x_m_override"])
        for p in position_overrides
    }

    if components:
        # Per-component path: apply all override types
        total_mass = 0.0
        moment_x = 0.0
        for comp in components:
            cid = str(comp.get("id", ""))
            if cid in disabled_uuids:
                continue  # toggle off → mass = 0
            m = mass_ovr_map.get(cid, float(comp.get("mass_kg", 0.0) or 0.0))
            x = pos_ovr_map.get(cid, float(comp.get("x_m", 0.0) or 0.0))
            total_mass += m
            moment_x += m * x
    else:
        # Legacy fallback: base_mass/base_cg_x only (pre-migration aeroplanes)
        total_mass = base_mass_kg
        moment_x = base_mass_kg * base_cg_x

    # Adhoc items are always additive on top
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
    cg_stability_fwd_m: float | None,
    cg_stability_aft_m: float | None,
) -> list[str]:
    """Validate that Loading-Envelope is within Stability-Envelope.

    Returns a list of warning/error strings.  Empty list = all OK.
    None stability limits (x_NP not yet computed) produce no validation
    warnings — the caller must add a separate 'stability unavailable' warning.
    """
    warnings: list[str] = []

    if cg_stability_aft_m is not None and cg_loading_aft_m > cg_stability_aft_m:
        excess_mm = round((cg_loading_aft_m - cg_stability_aft_m) * 1000, 1)
        warnings.append(
            f"CG exceeds aft stability limit by {excess_mm} mm — "
            "aircraft may be unstable in the aft loading scenario."
        )

    if cg_stability_fwd_m is not None and cg_loading_fwd_m < cg_stability_fwd_m:
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
    cg_stability_fwd_m: float | None,
    cg_stability_aft_m: float | None,
) -> dict[str, Any]:
    """Additively add CG envelope keys to an existing computation context dict.

    Preserves all existing keys (esp. cg_agg_m for backward compat) and
    adds the new gh-488 keys: cg_forward_m, cg_aft_m, sm_at_fwd, sm_at_aft.

    When x_np_m is not in the context (recompute hasn't run), sm_at_fwd/aft
    are stored as None to avoid deceptive stub values.

    Args:
        ctx: existing assumption_computation_context dict.
        cg_loading_fwd_m: forward loading CG [m].
        cg_loading_aft_m: aft loading CG [m].
        cg_stability_fwd_m: forward stability limit [m], or None.
        cg_stability_aft_m: aft stability limit [m], or None.

    Returns:
        Updated dict (same object, modified in-place).
    """
    x_np_raw = ctx.get("x_np_m")
    mac_raw = ctx.get("mac_m")
    x_np = float(x_np_raw) if x_np_raw else None
    mac = float(mac_raw) if mac_raw else None

    if x_np is not None and mac is not None and mac > 0:
        sm_at_fwd = round((x_np - cg_loading_fwd_m) / mac, 4)
        sm_at_aft = round((x_np - cg_loading_aft_m) / mac, 4)
    else:
        sm_at_fwd = None
        sm_at_aft = None

    ctx["cg_forward_m"] = round(cg_loading_fwd_m, 4)
    ctx["cg_aft_m"] = round(cg_loading_aft_m, 4)
    ctx["sm_at_fwd"] = sm_at_fwd
    ctx["sm_at_aft"] = sm_at_aft
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


def _load_components_as_dicts(db: Session, aeroplane_id: int) -> list[dict]:
    """Load weight items as plain dicts for use in compute_scenario_cg.

    Returns a list of {"id": str(item.id), "mass_kg": ..., "x_m": ..., ...} dicts.
    Empty list when no weight items exist (triggers legacy base_mass/base_cg_x path).
    """
    from app.models.aeroplanemodel import WeightItemModel

    rows = (
        db.query(WeightItemModel)
        .filter(WeightItemModel.aeroplane_id == aeroplane_id)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "mass_kg": float(r.mass_kg or 0.0),
            "x_m": float(r.x_m or 0.0),
            "y_m": float(r.y_m or 0.0),
            "z_m": float(r.z_m or 0.0),
        }
        for r in rows
    ]


def compute_cg_agg_for_aeroplane(db: Session, aeroplane: AeroplaneModel) -> float | None:
    """Compute the single-value CG_agg for backward-compatible clients.

    Spec (gh-488): cg_agg_m MUST equal the CG of the ``is_default`` scenario.
    Falls back to legacy weight-item aggregation when no loading scenarios exist
    (backward-compat for pre-migration aeroplanes).

    Returns:
        CG_x [m], or None when no data is available (no scenarios AND no weight items).
    """
    base_mass = _load_assumption_value(db, aeroplane.id, "mass", default=1.0)
    base_cg_x = _load_assumption_value(db, aeroplane.id, "cg_x", default=0.0)

    # Try is_default scenario first
    default_scenario = (
        db.query(LoadingScenarioModel)
        .filter(
            LoadingScenarioModel.aeroplane_id == aeroplane.id,
            LoadingScenarioModel.is_default.is_(True),
        )
        .first()
    )
    if default_scenario is not None:
        overrides_raw = default_scenario.component_overrides or {}
        if isinstance(overrides_raw, str):
            overrides_raw = json.loads(overrides_raw)
        overrides = ComponentOverrides.model_validate(overrides_raw)
        components = _load_components_as_dicts(db, aeroplane.id)
        return compute_scenario_cg(
            base_mass_kg=base_mass,
            base_cg_x=base_cg_x,
            adhoc_items=[item.model_dump() for item in overrides.adhoc_items],
            mass_overrides=[m.model_dump() for m in overrides.mass_overrides],
            toggles=[t.model_dump() for t in overrides.toggles],
            position_overrides=[p.model_dump() for p in overrides.position_overrides],
            components=components or None,
        )

    # Legacy fallback: weight-item aggregation (pre-migration aeroplanes)
    from app.models.aeroplanemodel import WeightItemModel
    from app.services.mass_cg_service import aggregate_weight_items

    rows = (
        db.query(WeightItemModel)
        .filter(WeightItemModel.aeroplane_id == aeroplane.id)
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


def compute_loading_envelope_for_aeroplane(
    db: Session, aeroplane: AeroplaneModel
) -> dict[str, Any]:
    """Compute the Loading-Envelope (min/max CG) over all loading scenarios.

    Applies all four override types (toggles, mass_overrides, position_overrides,
    adhoc_items) per scenario.  Falls back to the design cg_x when no loading
    scenarios exist (backward compat).

    Returns dict with:
        cg_loading_fwd_m: forward-most CG across all scenarios [m]
        cg_loading_aft_m: aft-most CG across all scenarios [m]
        scenarios_eval: list of per-scenario CG values
    """
    base_mass = _load_assumption_value(db, aeroplane.id, "mass", default=1.0)
    base_cg_x = _load_assumption_value(db, aeroplane.id, "cg_x", default=0.0)
    components = _load_components_as_dicts(db, aeroplane.id)

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
            overrides_raw = json.loads(overrides_raw)
        overrides = ComponentOverrides.model_validate(overrides_raw)
        cg = compute_scenario_cg(
            base_mass_kg=base_mass,
            base_cg_x=base_cg_x,
            adhoc_items=[item.model_dump() for item in overrides.adhoc_items],
            mass_overrides=[m.model_dump() for m in overrides.mass_overrides],
            toggles=[t.model_dump() for t in overrides.toggles],
            position_overrides=[p.model_dump() for p in overrides.position_overrides],
            components=components or None,
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

    mark_ops_dirty(db, aeroplane.id)
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
) -> CgEnvelopeRead:
    """Compute the full CG envelope (loading + stability + classification).

    Returns a dict compatible with CgEnvelopeRead schema.

    Stability fields (cg_stability_fwd_m, cg_stability_aft_m, sm_at_fwd, sm_at_aft)
    are None when recompute_assumptions hasn't been run yet (x_NP / MAC missing from
    assumption_computation_context).  The classification is "unknown" in that case and
    an explicit 'stability unavailable' warning is added.  This prevents the old
    deceptive pattern of synthesising x_np = cg_x + target_sm*MAC which made
    sm_at_aft == target_sm always (a false-positive "perfect" envelope).
    """
    aeroplane = _get_aeroplane(db, aeroplane_uuid)

    # Loading envelope
    loading = compute_loading_envelope_for_aeroplane(db, aeroplane)
    cg_fwd = loading["cg_loading_fwd_m"]
    cg_aft = loading["cg_loading_aft_m"]

    # Stability envelope — requires x_NP and MAC from recompute_assumptions context.
    # Do NOT synthesise fallback values: that produces a deceptively "perfect" envelope.
    ctx = aeroplane.assumption_computation_context or {}
    x_np_raw = ctx.get("x_np_m")
    mac_raw = ctx.get("mac_m")
    x_np = float(x_np_raw) if x_np_raw else None
    mac = float(mac_raw) if mac_raw else None
    target_sm = _load_assumption_value(db, aeroplane.id, "target_static_margin", default=0.08)

    stability = compute_stability_envelope(x_np=x_np, mac=mac, target_sm=target_sm)
    stab_fwd = stability["cg_stability_fwd_m"]
    stab_aft = stability["cg_stability_aft_m"]

    # Static margins — only computable when x_NP and MAC are available
    if x_np is not None and mac is not None and mac > 0:
        sm_at_fwd: float | None = (x_np - cg_fwd) / mac
        sm_at_aft: float | None = (x_np - cg_aft) / mac
    else:
        sm_at_fwd = None
        sm_at_aft = None

    # Classify worst-case (aft = most critical for stability)
    classification_fwd = classify_sm(sm_at_fwd, target_sm)
    classification_aft = classify_sm(sm_at_aft, target_sm)

    # Hierarchy: error > warn > ok > unknown
    _rank = {"error": 3, "warn": 2, "ok": 1, "unknown": 0}
    if _rank[classification_fwd] >= _rank[classification_aft]:
        overall = classification_fwd
    else:
        overall = classification_aft

    # Validation warnings
    warnings = validate_cg_envelope(cg_fwd, cg_aft, stab_fwd, stab_aft)

    if overall == "unknown":
        warnings.insert(
            0,
            "Stability envelope unavailable — recompute_assumptions hasn't been run. "
            "Run a full analysis to populate x_NP and MAC.",
        )
    elif overall == "error" and sm_at_aft is not None:
        warnings.insert(0, f"SM at aft CG = {sm_at_aft:.1%} — outside safe operating range.")

    return CgEnvelopeRead(
        cg_loading_fwd_m=round(cg_fwd, 4),
        cg_loading_aft_m=round(cg_aft, 4),
        cg_stability_fwd_m=round(stab_fwd, 4) if stab_fwd is not None else None,
        cg_stability_aft_m=round(stab_aft, 4) if stab_aft is not None else None,
        sm_at_fwd=round(sm_at_fwd, 4) if sm_at_fwd is not None else None,
        sm_at_aft=round(sm_at_aft, 4) if sm_at_aft is not None else None,
        classification=overall,
        warnings=warnings,
    )
