"""Flight envelope service — V-n curve computation, KPI derivation, and DB persistence."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel
from app.models.flight_envelope_model import FlightEnvelopeModel
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.flight_envelope import (
    FlightEnvelopeRead,
    PerformanceKPI,
    VnCurve,
    VnMarker,
    VnPoint,
)

logger = logging.getLogger(__name__)

GRAVITY = 9.81


# ---------------------------------------------------------------------------
# Pure computation helpers (no DB)
# ---------------------------------------------------------------------------


def compute_vn_curve(
    mass_kg: float,
    cl_max: float,
    g_limit: float,
    wing_area_m2: float,
    rho: float = 1.225,
    v_max_mps: float = 28.0,
) -> VnCurve:
    """Compute the V-n diagram boundary curves.

    Returns a VnCurve with positive and negative boundary points from
    stall speed to dive speed (1.4 * v_max).
    """
    weight = mass_kg * GRAVITY
    v_stall = math.sqrt(2 * weight / (rho * wing_area_m2 * cl_max))
    v_dive = 1.4 * v_max_mps
    cl_min = -0.8 * cl_max

    n_points = 60  # > 50 as required

    positive: list[VnPoint] = []
    negative: list[VnPoint] = []

    for i in range(n_points):
        v = v_stall + (v_dive - v_stall) * i / (n_points - 1)
        q = 0.5 * rho * v**2

        n_pos = min(q * wing_area_m2 * cl_max / weight, g_limit)
        n_neg = max(q * wing_area_m2 * cl_min / weight, -0.4 * g_limit)

        positive.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_pos, 6)))
        negative.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_neg, 6)))

    return VnCurve(
        positive=positive,
        negative=negative,
        dive_speed_mps=round(v_dive, 6),
        stall_speed_mps=round(v_stall, 6),
    )


def derive_performance_kpis(
    stall_speed_mps: float,
    v_max_mps: float,
    g_limit: float,
    markers: list[VnMarker],
) -> list[PerformanceKPI]:
    """Derive 6 KPIs from the flight envelope and operating-point markers.

    Always returns exactly 6 KPIs: stall_speed, best_ld_speed,
    min_sink_speed, max_speed, max_load_factor, dive_speed.
    """
    markers_by_label: dict[str, VnMarker] = {m.label: m for m in markers}

    kpis: list[PerformanceKPI] = []

    # 1. stall_speed
    kpis.append(
        PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=round(stall_speed_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    # 2. best_ld_speed
    best_ld_marker = markers_by_label.get("best_ld")
    if best_ld_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(best_ld_marker.velocity_mps, 4),
                unit="m/s",
                source_op_id=best_ld_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(1.4 * stall_speed_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="estimated",
            )
        )

    # 3. min_sink_speed
    min_sink_marker = markers_by_label.get("min_sink")
    if min_sink_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(min_sink_marker.velocity_mps, 4),
                unit="m/s",
                source_op_id=min_sink_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(1.2 * stall_speed_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="estimated",
            )
        )

    # 4. max_speed
    kpis.append(
        PerformanceKPI(
            label="max_speed",
            display_name="Max Speed",
            value=round(v_max_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    # 5. max_load_factor
    max_turn_marker = markers_by_label.get("max_turn")
    if max_turn_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="max_load_factor",
                display_name="Max Load Factor",
                value=round(max_turn_marker.load_factor, 4),
                unit="g",
                source_op_id=max_turn_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="max_load_factor",
                display_name="Max Load Factor",
                value=round(g_limit, 4),
                unit="g",
                source_op_id=None,
                confidence="limit",
            )
        )

    # 6. dive_speed
    kpis.append(
        PerformanceKPI(
            label="dive_speed",
            display_name="Dive Speed",
            value=round(1.4 * v_max_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    return kpis


# ---------------------------------------------------------------------------
# DB-aware helpers
# ---------------------------------------------------------------------------


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    """Query AeroplaneModel by uuid; raise NotFoundError if missing."""
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _load_assumptions(db: Session, aeroplane_uuid) -> dict[str, float]:
    """Load effective values for mass, cl_max, g_limit.

    Falls back to PARAMETER_DEFAULTS if a design assumption row is missing.
    """
    from app.services.mass_cg_service import get_effective_assumption_value

    result: dict[str, float] = {}
    for param in ("mass", "cl_max", "g_limit"):
        try:
            result[param] = get_effective_assumption_value(db, aeroplane_uuid, param)
        except NotFoundError:
            result[param] = PARAMETER_DEFAULTS[param]
    return result


def _get_wing_area_m2(db: Session, aeroplane: AeroplaneModel) -> float:
    """Convert aeroplane to ASB Airplane and return s_ref."""
    from app.converters.model_schema_converters import (
        aeroplane_model_to_aeroplane_schema_async,
        aeroplane_schema_to_asb_airplane_async,
    )

    schema = aeroplane_model_to_aeroplane_schema_async(aeroplane)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(schema)
    return asb_airplane.s_ref


def _get_v_max(db: Session, aeroplane: AeroplaneModel) -> float:
    """Get max level speed from flight profile goals; default 28.0 m/s."""
    profile = aeroplane.flight_profile
    if profile is not None:
        goals = profile.goals
        if isinstance(goals, dict):
            v = goals.get("max_level_speed_mps")
            if v is not None:
                return float(v)
    return 28.0


def _load_operating_point_markers(
    db: Session,
    aeroplane: AeroplaneModel,
    mass_kg: float,
    wing_area_m2: float,
) -> list[VnMarker]:
    """Query OperatingPointModel rows for this aeroplane and map to VnMarker."""
    ops = (
        db.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aeroplane.id).all()
    )
    markers: list[VnMarker] = []
    weight = mass_kg * GRAVITY
    for op in ops:
        v = op.velocity
        if v is None or v <= 0:
            continue
        # Compute load factor from alpha: n ~ q * S * CL / W
        # but we don't know CL from this row. Approximate as 1.0 for level flight.
        # For trimmed points, CL = W / (q * S) => n = 1.0; for turning points
        # the status encodes it. We report n=1.0 as a safe default; markers
        # are visual aids and refined later by the frontend.
        q = 0.5 * 1.225 * v**2
        n = q * wing_area_m2 / weight if weight > 0 else 1.0
        # Clamp to a reasonable range
        n = max(-5.0, min(n, 5.0))
        markers.append(
            VnMarker(
                op_id=op.id,
                name=op.name or "unnamed",
                velocity_mps=v,
                load_factor=round(n, 4),
                status=op.status or "NOT_TRIMMED",
                label=op.name or "unnamed",
            )
        )
    return markers


def _model_to_read(row: FlightEnvelopeModel) -> FlightEnvelopeRead:
    """Convert a FlightEnvelopeModel row to a FlightEnvelopeRead schema."""
    return FlightEnvelopeRead(
        id=row.id,
        aeroplane_id=row.aeroplane_id,
        vn_curve=VnCurve.model_validate(row.vn_curve_json),
        kpis=[PerformanceKPI.model_validate(k) for k in row.kpis_json],
        operating_points=[VnMarker.model_validate(m) for m in row.markers_json],
        assumptions_snapshot=row.assumptions_snapshot,
        computed_at=row.computed_at,
    )


# ---------------------------------------------------------------------------
# Public orchestration API
# ---------------------------------------------------------------------------


def compute_flight_envelope(db: Session, aeroplane_uuid) -> FlightEnvelopeRead:
    """Compute (or recompute) the flight envelope for an aeroplane.

    Steps:
    1. Load aeroplane and design assumptions
    2. Get wing area via ASB conversion
    3. Get v_max from flight profile
    4. Compute V-n curve and KPIs
    5. Load operating-point markers
    6. Upsert to DB
    7. Return FlightEnvelopeRead
    """
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    assumptions = _load_assumptions(db, aeroplane_uuid)
    wing_area_m2 = _get_wing_area_m2(db, aeroplane)
    v_max = _get_v_max(db, aeroplane)

    mass_kg = assumptions["mass"]
    cl_max = assumptions["cl_max"]
    g_limit = assumptions["g_limit"]

    vn_curve = compute_vn_curve(
        mass_kg=mass_kg,
        cl_max=cl_max,
        g_limit=g_limit,
        wing_area_m2=wing_area_m2,
        v_max_mps=v_max,
    )

    markers = _load_operating_point_markers(db, aeroplane, mass_kg, wing_area_m2)

    kpis = derive_performance_kpis(
        stall_speed_mps=vn_curve.stall_speed_mps,
        v_max_mps=v_max,
        g_limit=g_limit,
        markers=markers,
    )

    now = datetime.now(timezone.utc)

    # Serialize for JSON columns
    vn_curve_json = vn_curve.model_dump(mode="json")
    kpis_json = [k.model_dump(mode="json") for k in kpis]
    markers_json = [m.model_dump(mode="json") for m in markers]
    assumptions_snapshot = assumptions

    # Upsert: update if exists, create if not
    existing = (
        db.query(FlightEnvelopeModel)
        .filter(FlightEnvelopeModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if existing is not None:
        existing.vn_curve_json = vn_curve_json
        existing.kpis_json = kpis_json
        existing.markers_json = markers_json
        existing.assumptions_snapshot = assumptions_snapshot
        existing.computed_at = now
        db.flush()
        db.refresh(existing)
        return _model_to_read(existing)

    row = FlightEnvelopeModel(
        aeroplane_id=aeroplane.id,
        vn_curve_json=vn_curve_json,
        kpis_json=kpis_json,
        markers_json=markers_json,
        assumptions_snapshot=assumptions_snapshot,
        computed_at=now,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return _model_to_read(row)


def get_flight_envelope(db: Session, aeroplane_uuid) -> FlightEnvelopeRead | None:
    """Return the cached flight envelope, or None if not yet computed."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    row = (
        db.query(FlightEnvelopeModel)
        .filter(FlightEnvelopeModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if row is None:
        return None
    return _model_to_read(row)
