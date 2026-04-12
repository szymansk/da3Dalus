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
