"""Stability Summary Service — extract static stability data from an analysis result."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.stability import StabilitySummaryResponse, StabilityResultRead
from app.services.analysis_service import get_aeroplane_schema_or_raise

logger = logging.getLogger(__name__)


def _scalar(val) -> Optional[float]:
    """Extract a scalar float from a value that may be a list, numpy array, or None."""
    if val is None:
        return None
    if isinstance(val, np.ndarray):
        if val.ndim == 0:
            return float(val)
        if val.size > 1:
            logger.warning("_scalar received %s with %d elements; using first", type(val).__name__, val.size)
        return float(val[0]) if val.size > 0 else None
    if isinstance(val, list):
        if len(val) > 1:
            logger.warning("_scalar received %s with %d elements; using first", type(val).__name__, len(val))
        return float(val[0]) if len(val) > 0 else None
    return float(val)


def _compute_static_margin(xnp: Optional[float], xcg: Optional[float], cref_val) -> Optional[float]:
    """Compute static margin: (Xnp - Xcg) / MAC."""
    if xnp is None or xcg is None:
        return None
    mac = _scalar(cref_val)
    if not mac or mac <= 0:
        return None
    return (xnp - xcg) / mac


def _find_trim_elevator(control_surfaces) -> Optional[float]:
    """Extract trim elevator deflection from control surface data."""
    if not hasattr(control_surfaces, "deflections") or not control_surfaces.deflections:
        return None
    for name, defl in control_surfaces.deflections.items():
        if "elevator" in name.lower():
            return _scalar(defl)
    return None


# ---------------------------------------------------------------------------
# Pure computation helpers (no DB)
# ---------------------------------------------------------------------------


def classify_stability(static_margin_pct: float | None) -> str | None:
    """Classify stability based on static margin percentage.

    >5% → stable, 0-5% → neutral, <0% → unstable.
    """
    if static_margin_pct is None:
        return None
    if static_margin_pct > 5:
        return "stable"
    if static_margin_pct >= 0:
        return "neutral"
    return "unstable"


def compute_cg_range(
    np_x: float,
    mac: float,
    min_margin: float = 5.0,
    max_margin: float = 25.0,
) -> tuple[float, float] | None:
    """Compute forward and aft CG limits from NP position and margin bounds.

    Forward limit = NP_x − (max_margin / 100) × MAC  (most stable)
    Aft limit     = NP_x − (min_margin / 100) × MAC  (least stable)
    """
    if mac is None or mac <= 0:
        return None
    forward = np_x - (max_margin / 100) * mac
    aft = np_x - (min_margin / 100) * mac
    return (forward, aft)


def compute_geometry_hash(plane_schema) -> str:
    """Produce a deterministic hash of the geometry that affects stability."""
    data: dict = {"wings": [], "fuselages": []}
    if hasattr(plane_schema, "wings") and plane_schema.wings:
        for w in plane_schema.wings:
            wing_data = {
                "name": getattr(w, "name", ""),
                "symmetric": getattr(w, "symmetric", False),
            }
            xsecs = []
            if hasattr(w, "x_secs") and w.x_secs:
                for xs in w.x_secs:
                    xsecs.append({
                        "x_le": getattr(xs, "x_le", 0),
                        "y_le": getattr(xs, "y_le", 0),
                        "z_le": getattr(xs, "z_le", 0),
                        "chord": getattr(xs, "chord", 0),
                        "twist": getattr(xs, "twist", 0),
                    })
            wing_data["x_secs"] = xsecs
            data["wings"].append(wing_data)
    if hasattr(plane_schema, "fuselages") and plane_schema.fuselages:
        for f in plane_schema.fuselages:
            fus_data = {"name": getattr(f, "name", "")}
            xsecs = []
            if hasattr(f, "x_secs") and f.x_secs:
                for xs in f.x_secs:
                    xsecs.append({
                        "x": getattr(xs, "x_c", 0),
                        "width": getattr(xs, "width", 0),
                        "height": getattr(xs, "height", 0),
                    })
            fus_data["x_secs"] = xsecs
            data["fuselages"].append(fus_data)
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def persist_stability_result(
    db: Session,
    aeroplane_id: int,
    solver: str,
    summary: StabilitySummaryResponse,
    geometry_hash: str | None = None,
) -> None:
    """Upsert a stability result row for the given aeroplane+solver."""
    from app.models.stability_result import StabilityResultModel

    existing = (
        db.query(StabilityResultModel)
        .filter_by(aeroplane_id=aeroplane_id, solver=solver)
        .first()
    )
    values = {
        "neutral_point_x": summary.neutral_point_x,
        "mac": summary.mac,
        "cg_x_used": summary.cg_x,
        "static_margin_pct": summary.static_margin_pct,
        "stability_class": summary.stability_class,
        "cg_range_forward": summary.cg_range_forward,
        "cg_range_aft": summary.cg_range_aft,
        "Cma": summary.Cma,
        "Cnb": summary.Cnb,
        "Clb": summary.Clb,
        "trim_alpha_deg": summary.trim_alpha_deg,
        "trim_elevator_deg": summary.trim_elevator_deg,
        "is_statically_stable": summary.is_statically_stable,
        "is_directionally_stable": summary.is_directionally_stable,
        "is_laterally_stable": summary.is_laterally_stable,
        "computed_at": datetime.now(timezone.utc),
        "status": "CURRENT",
        "geometry_hash": geometry_hash,
    }
    if existing:
        for k, v in values.items():
            setattr(existing, k, v)
    else:
        row = StabilityResultModel(
            aeroplane_id=aeroplane_id,
            solver=solver,
            **values,
        )
        db.add(row)
    db.flush()


def get_cached_stability(db: Session, aeroplane_id: int) -> StabilityResultRead | None:
    """Return the most recent stability result, preferring CURRENT over DIRTY."""
    from app.models.stability_result import StabilityResultModel

    row = (
        db.query(StabilityResultModel)
        .filter_by(aeroplane_id=aeroplane_id)
        .order_by(
            StabilityResultModel.status.asc(),
            StabilityResultModel.computed_at.desc(),
        )
        .first()
    )
    if row is None:
        return None
    return StabilityResultRead.model_validate(row)


def mark_stability_dirty(db: Session, aeroplane_id: int) -> None:
    """Mark all stability results for an aeroplane as DIRTY."""
    from sqlalchemy import update
    from app.models.stability_result import StabilityResultModel

    db.execute(
        update(StabilityResultModel)
        .where(StabilityResultModel.aeroplane_id == aeroplane_id)
        .values(status="DIRTY")
    )


def _get_margin_bounds(db: Session, aeroplane_id: int) -> tuple[float, float]:
    """Read min/max static margin from design_assumptions, with defaults."""
    from app.models.aeroplanemodel import DesignAssumptionModel

    min_margin = 5.0
    max_margin = 25.0
    rows = (
        db.query(DesignAssumptionModel)
        .filter_by(aeroplane_id=aeroplane_id)
        .filter(DesignAssumptionModel.parameter_name.in_(
            ["min_static_margin", "max_static_margin"]
        ))
        .all()
    )
    if not rows:
        logger.debug("No margin bounds in design_assumptions for aeroplane %s; using defaults (5%%/25%%)", aeroplane_id)
    for r in rows:
        val = r.calculated_value if r.active_source == "CALCULATED" and r.calculated_value is not None else r.estimate_value
        if r.parameter_name == "min_static_margin":
            min_margin = val
        elif r.parameter_name == "max_static_margin":
            max_margin = val
    return (min_margin, max_margin)


def _auto_populate_cd0(db: Session, aeroplane_id: int, result) -> None:
    """Update cd0 calculated_value from AeroBuildup parasitic drag."""
    from app.models.aeroplanemodel import DesignAssumptionModel

    try:
        cd0_val = _scalar(getattr(result, "CD", None))
        if cd0_val is None:
            cd0_val = _scalar(getattr(getattr(result, "aero", None), "CD", None))
        if cd0_val is None:
            return
        row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aeroplane_id, parameter_name="cd0")
            .first()
        )
        if row is None:
            logger.debug("No cd0 assumption row for aeroplane %s; skipping auto-populate", aeroplane_id)
            return
        row.calculated_value = cd0_val
        row.calculated_source = "stability_analysis"
        db.flush()
    except Exception:
        logger.warning("Failed to auto-populate cd0 for aeroplane %s", aeroplane_id, exc_info=True)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def get_stability_summary(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> StabilitySummaryResponse:
    """Run an analysis and extract stability summary from the result."""
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.api.utils import analyse_aerodynamics

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    avl_file_content = None
    if analysis_tool == AnalysisToolUrlType.AVL:
        from app.services.avl_geometry_service import build_avl_geometry_file, inject_cdcl
        from app.schemas.aeroanalysisschema import CdclConfig, SpacingConfig

        cdcl_config = operating_point.cdcl_config or CdclConfig()
        spacing_config = operating_point.spacing_config or SpacingConfig()
        avl_file = build_avl_geometry_file(plane_schema, spacing_config)
        inject_cdcl(avl_file, plane_schema, operating_point, cdcl_config)
        avl_file_content = repr(avl_file)

    try:
        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        result, _ = analyse_aerodynamics(
            analysis_tool, operating_point, asb_airplane, avl_file_content=avl_file_content
        )
    except Exception as e:
        logger.error("Error computing stability: %s", e)
        raise InternalError(message=f"Stability analysis error: {e}")

    xnp = _scalar(result.reference.Xnp)
    xcg = float(operating_point.xyz_ref[0]) if operating_point.xyz_ref else None
    cma = _scalar(result.derivatives.Cma)
    cnb = _scalar(result.derivatives.Cnb)
    clb = _scalar(result.derivatives.Clb)
    mac_val = _scalar(result.reference.Cref)
    static_margin = _compute_static_margin(xnp, xcg, mac_val)
    static_margin_pct = static_margin * 100 if static_margin is not None else None

    min_margin, max_margin = _get_margin_bounds(db, plane_schema.id)
    cg_range = None
    if xnp is not None and mac_val is not None and mac_val > 0:
        cg_range = compute_cg_range(xnp, mac_val, min_margin, max_margin)

    summary = StabilitySummaryResponse(
        static_margin=static_margin,
        neutral_point_x=xnp,
        cg_x=xcg,
        trim_alpha_deg=_scalar(result.flight_condition.alpha),
        trim_elevator_deg=_find_trim_elevator(result.control_surfaces),
        Cma=cma,
        Cnb=cnb,
        Clb=clb,
        is_statically_stable=(cma is not None and cma < 0),
        is_directionally_stable=(cnb is not None and cnb > 0),
        is_laterally_stable=(clb is not None and clb < 0),
        analysis_method=result.method,
        static_margin_pct=static_margin_pct,
        stability_class=classify_stability(static_margin_pct),
        cg_range_forward=cg_range[0] if cg_range else None,
        cg_range_aft=cg_range[1] if cg_range else None,
        mac=mac_val,
    )

    geometry_hash = compute_geometry_hash(plane_schema)
    persist_stability_result(db, plane_schema.id, str(analysis_tool), summary, geometry_hash)

    if str(analysis_tool).lower() in ("aerobuildup",):
        _auto_populate_cd0(db, plane_schema.id, result)

    return summary
