"""Powertrain Sizing Service — recommend motor+ESC+battery combos for a mission."""

import logging
import math

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from app.schemas.powertrain_sizing import (
    PowertrainCandidate,
    PowertrainSizingRequest,
    PowertrainSizingResponse,
)

logger = logging.getLogger(__name__)

# Simplified aerodynamic constants for estimation
AIR_DENSITY_SEA_LEVEL = 1.225  # kg/m³
DRAG_COEFF_ESTIMATE = 0.04
WING_AREA_ESTIMATE_M2 = 0.5
PROP_EFFICIENCY = 0.7
MOTOR_EFFICIENCY = 0.85


def _air_density(altitude_m: float) -> float:
    """ISA air density approximation."""
    return AIR_DENSITY_SEA_LEVEL * math.exp(-altitude_m / 8500.0)


def _required_power_w(speed_ms: float, total_mass_kg: float, altitude_m: float) -> float:
    """Estimate power required for level flight at given speed."""
    rho = _air_density(altitude_m)
    # Parasitic drag: half rho v-squared Cd S
    drag_n = 0.5 * rho * speed_ms**2 * DRAG_COEFF_ESTIMATE * WING_AREA_ESTIMATE_M2
    # Add induced drag (simple)
    cl = (2 * total_mass_kg * 9.81) / (rho * speed_ms**2 * WING_AREA_ESTIMATE_M2)
    aspect_ratio = 8.0  # typical for RC
    induced_drag = (cl**2) / (math.pi * aspect_ratio * 0.9)
    total_drag = drag_n + 0.5 * rho * speed_ms**2 * induced_drag * WING_AREA_ESTIMATE_M2
    power_shaft = total_drag * speed_ms
    return power_shaft / (PROP_EFFICIENCY * MOTOR_EFFICIENCY)


def size_powertrain(
    db: Session, aeroplane_uuid, request: PowertrainSizingRequest
) -> PowertrainSizingResponse:
    # Verify aeroplane exists
    aeroplane = db.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)

    # Fetch available components
    motors = db.query(ComponentModel).filter(
        ComponentModel.component_type == "brushless_motor"
    ).all()
    batteries = db.query(ComponentModel).filter(
        ComponentModel.component_type == "battery"
    ).all()
    escs = db.query(ComponentModel).filter(
        ComponentModel.component_type == "esc"
    ).all()

    if not motors or not batteries:
        return PowertrainSizingResponse(recommendations=[])

    # Calculate power requirements
    cruise_power = _required_power_w(
        request.target_cruise_speed_ms,
        request.airframe_mass_kg,
        request.altitude_m,
    )

    candidates: list[PowertrainCandidate] = []

    for motor in motors:
        motor_mass_kg = (motor.mass_g or 0) / 1000.0
        motor_specs = motor.specs or {}

        for battery in batteries:
            battery_mass_kg = (battery.mass_g or 0) / 1000.0
            battery_specs = battery.specs or {}
            capacity_mah = battery_specs.get("capacity_mah", 0)
            voltage = battery_specs.get("voltage", battery_specs.get("nominal_voltage", 11.1))

            if capacity_mah <= 0 or voltage <= 0:
                continue

            total_mass = request.airframe_mass_kg + motor_mass_kg + battery_mass_kg
            actual_cruise_power = _required_power_w(
                request.target_cruise_speed_ms, total_mass, request.altitude_m
            )

            cruise_current_a = actual_cruise_power / voltage if voltage > 0 else 999
            if request.max_current_draw_a and cruise_current_a > request.max_current_draw_a:
                continue

            capacity_ah = capacity_mah / 1000.0
            flight_time_h = (capacity_ah / cruise_current_a) * 0.8 if cruise_current_a > 0 else 0
            flight_time_min = flight_time_h * 60

            # Confidence scoring
            time_ratio = min(flight_time_min / request.target_flight_time_min, 1.5)
            confidence = min(time_ratio / 1.5, 1.0)
            if flight_time_min < request.target_flight_time_min * 0.5:
                confidence *= 0.3

            # Pick best matching ESC
            esc_match = None
            for esc in escs:
                esc_specs = esc.specs or {}
                max_a = esc_specs.get("max_continuous_a", 0)
                if max_a >= cruise_current_a:
                    esc_match = esc
                    break

            candidates.append(PowertrainCandidate(
                motor_id=motor.id,
                motor_name=motor.name,
                esc_id=esc_match.id if esc_match else None,
                esc_name=esc_match.name if esc_match else None,
                battery_id=battery.id,
                battery_name=battery.name,
                estimated_flight_time_min=round(flight_time_min, 1),
                estimated_cruise_power_w=round(actual_cruise_power, 1),
                estimated_top_speed_ms=round(request.target_top_speed_ms, 1),
                confidence=round(confidence, 3),
            ))

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return PowertrainSizingResponse(recommendations=candidates[:10])
