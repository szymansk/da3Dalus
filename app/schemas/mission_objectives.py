from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


MANEUVERABILITY_CLASSES = Literal[
    "3d_acro", "sport", "long_range", "slope", "trainer"
]
ENGINE_TYPES = Literal[
    "electric_pusher", "electric_puller", "none"
]


class SizeEnvelope(BaseModel):
    length_mm: Optional[float] = Field(None, description="Bounding-box length in mm")
    width_mm: Optional[float] = Field(None, description="Bounding-box width in mm")
    height_mm: Optional[float] = Field(None, description="Bounding-box height in mm")


class MissionObjectivesWrite(BaseModel):
    payload_kg: Optional[float] = Field(None, ge=0, description="Payload mass in kg")
    target_flight_time_min: Optional[float] = Field(None, ge=0, description="Target flight time in minutes")
    maneuverability_class: Optional[MANEUVERABILITY_CLASSES] = Field(
        None, description="Maneuverability class"
    )
    size_envelope: Optional[SizeEnvelope] = Field(None, description="Transport / storage bounding box")
    engine_type: Optional[ENGINE_TYPES] = Field(None, description="Engine type")
    target_stall_speed_ms: Optional[float] = Field(None, ge=0, description="Target stall speed in m/s")
    target_cruise_speed_ms: Optional[float] = Field(None, ge=0, description="Target cruise speed in m/s")
    target_top_speed_ms: Optional[float] = Field(None, ge=0, description="Target top speed in m/s")


class MissionObjectivesRead(MissionObjectivesWrite):
    """Read schema — identical fields, returned from GET."""
    pass
