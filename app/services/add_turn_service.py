"""gh-806: add a single coordinated-turn operating point for an aircraft."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import AddTurnRequest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def add_turn_operating_point(
    db: "Session", aircraft_uuid, request: AddTurnRequest
) -> OperatingPointModel:
    """Build, trim, and persist one coordinated-turn OP at ``request.bank_angle_deg``."""
    from app.converters.model_schema_converters import (
        aeroplane_model_to_aeroplane_schema_async,
        aeroplane_schema_to_asb_airplane_async,
    )
    from app.services.operating_point_generator_service import (
        _apply_turn_feasibility,
        _detect_control_capabilities,
        _estimate_reference_speeds,
        _get_aircraft_or_raise,
        _load_design_cg_x,
        _load_effective_flight_profile,
        _load_effective_mass_kg,
        _resolve_cruise_speed_with_md_fallback,
        _trim_or_estimate_point,
    )
    from app.services.trim_enrichment_service import (
        build_deflection_limits_from_schema,
        build_mix_params_from_schema,
        compute_enrichment,
    )

    aircraft = _get_aircraft_or_raise(db, aircraft_uuid)
    profile, source_profile_id = _load_effective_flight_profile(db, aircraft, None)
    cruise = _resolve_cruise_speed_with_md_fallback(
        aircraft, profile.get("goals", {}), source_profile_id
    )
    profile.setdefault("goals", {})["cruise_speed_mps"] = cruise
    refs = _estimate_reference_speeds(
        profile, cached_context=aircraft.assumption_computation_context
    )
    mass_kg = _load_effective_mass_kg(db, aircraft.id, aircraft.total_mass_kg)
    design_cg_x = _load_design_cg_x(db, aircraft.id)

    bank = float(request.bank_angle_deg)
    velocity = (
        float(request.velocity)
        if request.velocity
        else max(cruise, 1.3 * refs["vs_clean"])
    )
    altitude = float(request.altitude) if request.altitude is not None else 0.0
    name = request.name or f"turn_{round(bank)}"

    target = {
        "name": name,
        "config": "clean",
        "velocity": velocity,
        "altitude": altitude,
        "beta_target_deg": 0.0,
        "bank_deg": bank,
        "n_target": round(1.0 / math.cos(math.radians(bank)), 4),
    }

    plane_schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
    asb_airplane.xyz_ref = [design_cg_x, 0.0, 0.0]
    capabilities = _detect_control_capabilities(asb_airplane)
    deflection_limits = build_deflection_limits_from_schema(plane_schema)

    point = _trim_or_estimate_point(
        asb_airplane=asb_airplane,
        aircraft=aircraft,
        target=target,
        constraints=profile.get("constraints", {}),
        capabilities=capabilities,
        effective_mass_kg=mass_kg,
    )
    _apply_turn_feasibility(point, bank, point.velocity, refs.get("vs_clean", 0.0))

    enrichment_data = None
    try:
        enrichment = compute_enrichment(
            controls=point.controls,
            limits=deflection_limits,
            trim_method=point.trim_method,
            trim_score=point.trim_score,
            trim_residuals=point.trim_residuals or {},
            op_name=point.name,
            alpha_deg=math.degrees(point.alpha_rad),
            status=point.status.value if point.status else None,
            mix_params=build_mix_params_from_schema(plane_schema),
        )
        enrichment_data = enrichment.model_dump()
    except Exception:
        enrichment_data = None

    model = OperatingPointModel(
        aircraft_id=aircraft.id,
        name=point.name,
        description=point.description,
        config=point.config,
        status=point.status.value,
        warnings=point.warnings,
        controls=point.controls,
        velocity=point.velocity,
        alpha=point.alpha_rad,
        beta=point.beta_rad,
        p=point.p,
        q=point.q,
        r=point.r,
        xyz_ref=[design_cg_x, 0.0, 0.0],
        altitude=point.altitude,
        trim_enrichment=enrichment_data,
    )
    db.add(model)
    db.flush()
    db.refresh(model)
    return model
