"""Aggregate the seven Mission compliance KPIs (gh-547).

All values come from cached ``assumption_computation_context`` plus the
persisted ``MissionObjective`` and the static list of ``MissionPreset``
rows. **No** AeroBuildup re-run — this service is closed-form on top of
existing data.

Public surface:

- :func:`compute_mission_kpis` — bundle the Ist + Soll polygons for the
  radar chart (added in Task 2.2).

The private ``_kpi_*`` calculators are unit-tested individually so the
aggregator stays a thin orchestration layer.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.mission_kpi import (
    AxisName,
    MissionAxisKpi,
    MissionKpiSet,
    MissionTargetPolygon,
)


# ----- Helpers --------------------------------------------------------------


def _normalise_score(value: float, lo: float, hi: float) -> float:
    """Map ``value`` to ``0..1`` across ``[lo, hi]``; clip outside.

    Degenerate ranges (``hi <= lo``) collapse to ``0.0`` because there
    is no defensible interpretation of "where in the range" the value
    sits.
    """
    if hi <= lo:
        return 0.0
    score = (value - lo) / (hi - lo)
    return max(0.0, min(1.0, score))


def _missing(axis: AxisName, lo: float, hi: float, formula: str) -> MissionAxisKpi:
    """Build a ``provenance="missing"`` axis (renders as polygon gap)."""
    return MissionAxisKpi(
        axis=axis,
        value=None,
        unit=None,
        score_0_1=None,
        range_min=lo,
        range_max=hi,
        provenance="missing",
        formula=formula,
    )


def _ctx_get(ctx: dict[str, Any], key: str) -> float | None:
    """Read a strictly-positive numeric value from the context dict.

    Returns ``None`` for missing keys, non-numerics, and non-positive
    values (zero or negative inputs are nonsensical for the physical
    quantities this service consumes).
    """
    v = ctx.get(key)
    if isinstance(v, (int, float)) and v > 0:
        return float(v)
    return None


# ----- Per-axis calculators -------------------------------------------------


def _kpi_stall_safety(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    """V_cruise / V_s1 — higher is safer."""
    formula = "V_cruise / V_s1"
    v_cruise = _ctx_get(ctx, "v_cruise_mps")
    v_s1 = _ctx_get(ctx, "v_s1_mps")
    if v_cruise is None or v_s1 is None:
        return _missing("stall_safety", range_min, range_max, formula)
    value = v_cruise / v_s1
    return MissionAxisKpi(
        axis="stall_safety",
        value=value,
        unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_glide(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    """Maximum lift-to-drag ratio from the clean polar."""
    formula = "(L/D)_max = 0.5 · √(π · e · AR / C_D0)"
    polar = ctx.get("polar_by_config", {}).get("clean") if ctx.get("polar_by_config") else None
    ar = ctx.get("aspect_ratio")
    if not polar or ar is None:
        return _missing("glide", range_min, range_max, formula)
    cd0 = polar.get("cd0")
    e = polar.get("e_oswald")
    if cd0 is None or cd0 <= 0 or e is None or e <= 0 or ar <= 0:
        return _missing("glide", range_min, range_max, formula)
    value = 0.5 * math.sqrt(math.pi * e * ar / cd0)
    return MissionAxisKpi(
        axis="glide",
        value=value,
        unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_climb_energy(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    """Climb-energy figure ``(C_L^1.5 / C_D)_max`` — relevant for thermalling and ROC."""
    formula = "(C_L^1.5 / C_D)_max = (3π·e·AR)^0.75 / (4·√3·√C_D0)"
    polar = ctx.get("polar_by_config", {}).get("clean") if ctx.get("polar_by_config") else None
    ar = ctx.get("aspect_ratio")
    if not polar or ar is None:
        return _missing("climb", range_min, range_max, formula)
    cd0 = polar.get("cd0")
    e = polar.get("e_oswald")
    if cd0 is None or cd0 <= 0 or e is None or e <= 0 or ar <= 0:
        return _missing("climb", range_min, range_max, formula)
    # Closed-form maximum of CL^1.5/CD with parabolic polar
    # CD = CD0 + CL^2/(pi e AR); max at CL such that 3·CD0 = CD_i.
    value = (3.0 * math.pi * e * ar) ** 0.75 / math.sqrt(cd0) / (math.sqrt(3.0) * 4.0)
    return MissionAxisKpi(
        axis="climb",
        value=value,
        unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_cruise(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    """Cruise speed straight from ``ComputationContext``."""
    formula = "V_cruise (from ComputationContext)"
    v = _ctx_get(ctx, "v_cruise_mps")
    if v is None:
        return _missing("cruise", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="cruise",
        value=v,
        unit="m/s",
        score_0_1=_normalise_score(v, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_maneuver(
    ctx: dict[str, Any], range_min: float, range_max: float
) -> MissionAxisKpi:
    """Maximum positive load factor from the V-n diagram."""
    formula = "n_max from V-n diagram (load factor)"
    n_max = ctx.get("flight_envelope_n_max")
    if not isinstance(n_max, (int, float)) or n_max <= 0:
        return _missing("maneuver", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="maneuver",
        value=float(n_max),
        unit="g",
        score_0_1=_normalise_score(float(n_max), range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_wing_loading(
    ctx: dict[str, Any],
    mass_kg: float | None,
    range_min: float,
    range_max: float,
) -> MissionAxisKpi:
    """Wing loading ``W/S = m·g / S_ref``."""
    formula = "W/S = m·g / S_ref"
    s_ref = _ctx_get(ctx, "s_ref_m2")
    if mass_kg is None or mass_kg <= 0 or s_ref is None:
        return _missing("wing_loading", range_min, range_max, formula)
    value = mass_kg * 9.81 / s_ref
    return MissionAxisKpi(
        axis="wing_loading",
        value=value,
        unit="N/m²",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


# ----- Field Friendliness (delegates to field_length_service) ---------------


def _compute_field_length_score(
    aeroplane: AeroplaneModel,
    target_field_length_m: float,
) -> tuple[float | None, float | None]:
    """Return ``(effective_field_length_m, score_0_1)`` or ``(None, None)``.

    The score is ``target_field / effective_field`` clipped to ``[0, 1]``:
    a shorter effective field is better. Returns ``(None, None)`` when
    the field-length service can't run (e.g. it isn't wired yet — Phase
    3 adds ``compute_field_lengths_for_aeroplane``; the broad ``except``
    keeps Phase 2 unblocked).
    """
    try:
        from app.services.field_length_service import (
            compute_field_lengths_for_aeroplane,
        )

        result = compute_field_lengths_for_aeroplane(aeroplane)
        eff = max(result.get("s_to_50ft_m", 0), result.get("s_ldg_50ft_m", 0))
        if eff <= 0:
            return None, None
        score = max(0.0, min(1.0, target_field_length_m / eff))
        return float(eff), float(score)
    except Exception:  # noqa: BLE001 — graceful fallback for missing field service
        return None, None


def _kpi_field_friendliness(
    aeroplane: AeroplaneModel,
    target_field_length_m: float,
    range_min: float,
    range_max: float,
) -> MissionAxisKpi:
    """Field friendliness — composite take-off + landing field length score."""
    formula = "max(s_TO_50ft, s_LDG_50ft); score = target / effective"
    eff, score = _compute_field_length_score(aeroplane, target_field_length_m)
    if eff is None or score is None:
        return _missing("field_friendliness", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="field_friendliness",
        value=eff,
        unit="m",
        score_0_1=score,
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


# ----- Aggregator -----------------------------------------------------------


def _hash_context(ctx: dict[str, Any]) -> str:
    """Stable 64-char SHA-256 of the context dict for cache validation."""
    blob = json.dumps(ctx, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def compute_mission_kpis(
    db: Session,
    aeroplane_id: int,
    active_mission_ids: list[str],
) -> MissionKpiSet:
    """Bundle Ist + multi-mission Soll polygons for the spider chart.

    The first id in ``active_mission_ids`` is the *primary* (active)
    mission — its ``axis_ranges`` drive the Ist normalisation and its
    id is echoed back as ``active_mission_id``. Additional ids
    contribute extra ``MissionTargetPolygon`` overlays only.

    Unknown mission ids are silently dropped. An empty list defaults
    to ``[objective.mission_type]``.
    """
    # Local import to avoid a circular dependency on app.services.* at module load.
    from app.services.mission_objective_service import (
        get_mission_objective,
        list_mission_presets,
    )

    aeroplane = db.query(AeroplaneModel).filter_by(id=aeroplane_id).one()
    ctx: dict[str, Any] = aeroplane.assumption_computation_context or {}
    objective = get_mission_objective(db, aeroplane_id)
    presets = {p.id: p for p in list_mission_presets(db)}

    if not active_mission_ids:
        active_mission_ids = [objective.mission_type]

    # Pick the primary mission preset for Ist axis ranges; fall back to
    # the "trainer" preset when the active id is unknown so we always
    # have *some* ranges to normalise against.
    primary_preset = presets.get(active_mission_ids[0]) or presets.get("trainer")
    if primary_preset is None:
        # Defensive: no presets seeded at all — return empty Ist polygon.
        return MissionKpiSet(
            aeroplane_uuid=str(aeroplane.uuid),
            ist_polygon={},
            target_polygons=[],
            active_mission_id=active_mission_ids[0],
            computed_at=datetime.now(timezone.utc).isoformat(),
            context_hash=_hash_context(ctx),
        )
    rng = primary_preset.axis_ranges

    # Mass for W/S: first try cached context, then the AeroplaneModel column.
    mass = ctx.get("mass_kg")
    if not isinstance(mass, (int, float)) or mass <= 0:
        mass = aeroplane.total_mass_kg if aeroplane.total_mass_kg else None

    ist: dict[AxisName, MissionAxisKpi] = {
        "stall_safety": _kpi_stall_safety(ctx, *rng["stall_safety"]),
        "glide": _kpi_glide(ctx, *rng["glide"]),
        "climb": _kpi_climb_energy(ctx, *rng["climb"]),
        "cruise": _kpi_cruise(ctx, *rng["cruise"]),
        "maneuver": _kpi_maneuver(ctx, *rng["maneuver"]),
        "wing_loading": _kpi_wing_loading(ctx, mass, *rng["wing_loading"]),
        "field_friendliness": _kpi_field_friendliness(
            aeroplane,
            objective.target_field_length_m,
            *rng["field_friendliness"],
        ),
    }

    # Build target polygons (Soll for each active mission preset)
    targets: list[MissionTargetPolygon] = []
    for mid in active_mission_ids:
        preset = presets.get(mid)
        if preset is None:
            continue
        targets.append(
            MissionTargetPolygon(
                mission_id=preset.id,
                label=preset.label,
                scores_0_1=preset.target_polygon,
            )
        )

    return MissionKpiSet(
        aeroplane_uuid=str(aeroplane.uuid),
        ist_polygon=ist,
        target_polygons=targets,
        active_mission_id=active_mission_ids[0],
        computed_at=datetime.now(timezone.utc).isoformat(),
        context_hash=_hash_context(ctx),
    )
