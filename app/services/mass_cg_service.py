"""Mass / CG design parameter service — derived metrics, sweep, and CG comparison."""

from __future__ import annotations

import logging
import math
from typing import Sequence, TypedDict

from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, WeightItemModel
from app.schemas.mass_cg import (
    CGComparisonResponse,
    DesignMetricsResponse,
    MassSweepPoint,
    MassSweepResponse,
)

logger = logging.getLogger(__name__)

GRAVITY = 9.81
CG_TOLERANCE_M = 0.01


class WeightItemData(TypedDict):
    mass_kg: float
    x_m: float
    y_m: float
    z_m: float


# ---------------------------------------------------------------------------
# Pure computation helpers (no DB)
# ---------------------------------------------------------------------------


def compute_recommended_cg(np_x: float, mac: float, target_static_margin: float) -> float:
    """CG_x = NP_x - target_static_margin * MAC."""
    return np_x - target_static_margin * mac


def compute_design_metrics(
    mass_kg: float,
    s_ref: float,
    cl_max: float,
    rho: float,
    velocity: float,
) -> DesignMetricsResponse:
    """Compute mass-dependent design quantities at a given flight condition."""
    if mass_kg <= 0:
        raise ValidationError(message="mass_kg must be positive")
    if s_ref <= 0:
        raise ValidationError(message="s_ref must be positive")
    if cl_max <= 0:
        raise ValidationError(message="cl_max must be positive")
    if rho <= 0:
        raise ValidationError(message="rho must be positive")
    if velocity <= 0:
        raise ValidationError(message="velocity must be positive")

    weight = mass_kg * GRAVITY
    wing_loading = weight / s_ref
    stall_speed = math.sqrt(2 * weight / (rho * s_ref * cl_max))
    q = 0.5 * rho * velocity**2
    required_cl = weight / (q * s_ref)
    cl_margin = cl_max - required_cl

    return DesignMetricsResponse(
        mass_kg=mass_kg,
        s_ref=s_ref,
        cl_max=cl_max,
        wing_loading_pa=wing_loading,
        stall_speed_ms=stall_speed,
        required_cl=required_cl,
        cl_margin=cl_margin,
    )


def compute_mass_sweep(
    masses_kg: list[float],
    s_ref: float,
    cl_max: float,
    rho: float,
    velocity: float,
) -> list[MassSweepPoint]:
    """Compute derived metrics at each mass point (no aero re-run needed)."""
    points: list[MassSweepPoint] = []
    for m in masses_kg:
        dm = compute_design_metrics(m, s_ref, cl_max, rho, velocity)
        points.append(
            MassSweepPoint(
                mass_kg=m,
                wing_loading_pa=dm.wing_loading_pa,
                stall_speed_ms=dm.stall_speed_ms,
                required_cl=dm.required_cl,
                cl_margin=dm.cl_margin,
            )
        )
    return points


def aggregate_weight_items(
    items: Sequence[WeightItemData],
) -> tuple[float | None, float | None, float | None, float | None]:
    """Compute total mass and mass-weighted CG from a list of weight item dicts.

    Returns (total_mass, cg_x, cg_y, cg_z). All None when items is empty
    or total mass is zero.
    """
    if not items:
        return None, None, None, None

    total_mass = sum(it["mass_kg"] for it in items)
    if total_mass <= 0:
        return None, None, None, None

    cg_x = sum(it["mass_kg"] * it["x_m"] for it in items) / total_mass
    cg_y = sum(it["mass_kg"] * it["y_m"] for it in items) / total_mass
    cg_z = sum(it["mass_kg"] * it["z_m"] for it in items) / total_mass

    return total_mass, cg_x, cg_y, cg_z


# ---------------------------------------------------------------------------
# DB-aware helpers
# ---------------------------------------------------------------------------


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def get_effective_assumption_value(db: Session, aeroplane_uuid, param_name: str) -> float:
    """Return the effective value for a design assumption parameter."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane.id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        raise NotFoundError(entity="DesignAssumption", resource_id=param_name)

    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return row.calculated_value
    return row.estimate_value


def sync_weight_items_to_assumptions(db: Session, aeroplane_uuid) -> None:
    """Aggregate weight items and update mass/cg_x calculated values."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)

    target_params = {"mass", "cg_x"}
    existing = (
        db.query(DesignAssumptionModel.parameter_name)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane.id,
            DesignAssumptionModel.parameter_name.in_(target_params),
        )
        .all()
    )
    existing_names = {row[0] for row in existing}
    if not existing_names:
        return

    rows = db.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == aeroplane.id).all()
    items: list[WeightItemData] = [
        {"mass_kg": r.mass_kg, "x_m": r.x_m, "y_m": r.y_m, "z_m": r.z_m} for r in rows
    ]

    total_mass, cg_x, _cg_y, _cg_z = aggregate_weight_items(items)

    from app.services.design_assumptions_service import update_calculated_value

    source = "weight_items" if total_mass is not None else None
    if "mass" in existing_names:
        update_calculated_value(db, aeroplane_uuid, "mass", total_mass, source)
    if "cg_x" in existing_names:
        update_calculated_value(
            db, aeroplane_uuid, "cg_x", cg_x,
            "weight_items" if cg_x is not None else None,
        )


def get_cg_comparison(db: Session, aeroplane_uuid) -> CGComparisonResponse:
    """Compare design CG assumption with component-tree CG from weight items."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)

    design_cg_x = get_effective_assumption_value(db, aeroplane_uuid, "cg_x")

    rows = db.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == aeroplane.id).all()
    items = [{"mass_kg": r.mass_kg, "x_m": r.x_m, "y_m": r.y_m, "z_m": r.z_m} for r in rows]

    total_mass, cg_x, cg_y, cg_z = aggregate_weight_items(items)

    delta_x = None
    within_tolerance = None
    if cg_x is not None:
        delta_x = design_cg_x - cg_x
        within_tolerance = abs(delta_x) < CG_TOLERANCE_M

    return CGComparisonResponse(
        design_cg_x=design_cg_x,
        component_cg_x=cg_x,
        component_cg_y=cg_y,
        component_cg_z=cg_z,
        component_total_mass_kg=total_mass,
        delta_x=delta_x,
        within_tolerance=within_tolerance,
    )


def get_s_ref_for_aeroplane(db: Session, aeroplane_uuid) -> float:
    """Build an ASB airplane and return its wing reference area [m^2]."""
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    try:
        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
    except Exception as e:
        logger.error("Error building ASB airplane for s_ref: %s", e)
        raise InternalError(message=f"Could not compute wing reference area: {e}") from e
    s_ref = float(getattr(asb_airplane, "s_ref", 0.0) or 0.0)
    if s_ref <= 0:
        raise ValidationError(
            message="Wing reference area (s_ref) is zero or negative — add wings first"
        )
    return s_ref


def get_design_metrics_for_aeroplane(
    db: Session, aeroplane_uuid, velocity: float, altitude: float
) -> DesignMetricsResponse:
    """Compute design metrics for an aeroplane using its effective assumptions."""
    import aerosandbox as asb

    mass_kg = get_effective_assumption_value(db, aeroplane_uuid, "mass")
    cl_max = get_effective_assumption_value(db, aeroplane_uuid, "cl_max")
    s_ref = get_s_ref_for_aeroplane(db, aeroplane_uuid)
    rho = asb.Atmosphere(altitude=altitude).density()

    return compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)


def get_mass_sweep_for_aeroplane(
    db: Session,
    aeroplane_uuid,
    masses_kg: list[float],
    velocity: float,
    altitude: float,
) -> MassSweepResponse:
    """Compute a mass sweep for an aeroplane."""
    import aerosandbox as asb

    cl_max = get_effective_assumption_value(db, aeroplane_uuid, "cl_max")
    s_ref = get_s_ref_for_aeroplane(db, aeroplane_uuid)
    rho = asb.Atmosphere(altitude=altitude).density()

    points = compute_mass_sweep(masses_kg, s_ref, cl_max, rho, velocity)
    return MassSweepResponse(
        s_ref=s_ref,
        cl_max=cl_max,
        velocity=velocity,
        altitude=altitude,
        points=points,
    )
