from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PowertrainSizingRequest(BaseModel):
    airframe_mass_kg: float = Field(..., ge=0, description="Airframe mass without powertrain in kg")
    target_cruise_speed_ms: float = Field(..., gt=0, description="Target cruise speed in m/s")
    target_top_speed_ms: float = Field(..., gt=0, description="Target top speed in m/s")
    target_flight_time_min: float = Field(..., gt=0, description="Target flight time in minutes")
    max_current_draw_a: Optional[float] = Field(None, ge=0, description="Max current draw constraint in A")
    altitude_m: float = Field(0.0, ge=0, description="Operating altitude in m")
    # Optional aerodynamic geometry — supply for accurate power estimates.
    # When omitted, RC-typical defaults are used (gh-490 Model A).
    cd0: Optional[float] = Field(None, ge=0, description="Zero-lift drag coefficient (default 0.03)")
    e_oswald: Optional[float] = Field(None, gt=0, le=1, description="Oswald efficiency factor (default 0.8)")
    aspect_ratio: Optional[float] = Field(None, gt=0, description="Wing aspect ratio (default 8.0)")
    s_ref_m2: Optional[float] = Field(None, gt=0, description="Wing reference area in m² (default 0.5)")
    eta_prop: Optional[float] = Field(None, gt=0, le=1, description="Propeller efficiency (default 0.65)")
    eta_motor: Optional[float] = Field(None, gt=0, le=1, description="Motor efficiency (default 0.85)")
    eta_esc: Optional[float] = Field(None, gt=0, le=1, description="ESC efficiency (default 0.94)")


class PowertrainCandidate(BaseModel):
    motor_id: Optional[int] = Field(None, description="Component ID of the motor")
    motor_name: Optional[str] = None
    esc_id: Optional[int] = Field(None, description="Component ID of the ESC")
    esc_name: Optional[str] = None
    battery_id: Optional[int] = Field(None, description="Component ID of the battery")
    battery_name: Optional[str] = None
    propeller: Optional[str] = Field(None, description="Propeller diameter/pitch suggestion")
    estimated_flight_time_min: float = Field(0.0, description="Estimated flight time")
    estimated_cruise_power_w: float = Field(0.0, description="Estimated cruise power draw")
    estimated_top_speed_ms: float = Field(0.0, description="Estimated achievable top speed")
    confidence: float = Field(0.0, ge=0, le=1, description="Recommendation confidence")


class PowertrainSizingResponse(BaseModel):
    recommendations: list[PowertrainCandidate] = Field(
        default_factory=list,
        description="Powertrain candidates sorted by confidence descending",
    )
