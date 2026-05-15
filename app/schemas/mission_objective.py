"""Mission-Objective + Mission-Preset Pydantic schemas (gh-546)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.mission_kpi import AxisName

RunwayType = Literal["grass", "asphalt", "belly"]
TakeoffMode = Literal["runway", "hand_launch", "bungee", "catapult"]


class MissionObjective(BaseModel):
    """User-set mission targets + field-performance inputs for one aeroplane."""

    mission_type: str = Field(..., description="FK to MissionPreset.id")

    # Performance targets (one per spider axis except W/S which is computed)
    target_cruise_mps: float = Field(..., ge=0)
    target_stall_safety: float = Field(..., ge=1.0, description="V_cruise / V_s1")
    target_maneuver_n: float = Field(..., ge=1.0, description="Load factor [g]")
    target_glide_ld: float = Field(..., ge=0, description="L/D target")
    target_climb_energy: float = Field(..., ge=0, description="C_L^1.5/CD")
    target_wing_loading_n_m2: float = Field(..., ge=0)
    target_field_length_m: float = Field(..., ge=0)

    # Field Performance inputs (migrated from Assumptions)
    available_runway_m: float = Field(..., ge=0)
    runway_type: RunwayType
    t_static_N: float = Field(..., ge=0, description="Static thrust at V=0")
    takeoff_mode: TakeoffMode


class MissionPresetEstimates(BaseModel):
    """Default DesignAssumption estimate_values applied when this mission is selected."""

    g_limit: float
    target_static_margin: float
    cl_max: float
    power_to_weight: float
    prop_efficiency: float


class MissionPreset(BaseModel):
    """One mission preset row (Trainer, Sport, Sailplane, …)."""

    id: str = Field(..., description="Stable preset id, e.g. 'trainer'")
    label: str
    description: str
    target_polygon: dict[AxisName, float] = Field(
        ..., description="Soll polygon scores 0..1 for the 7 axes"
    )
    axis_ranges: dict[AxisName, tuple[float, float]] = Field(
        ..., description="Mission-relative (min, max) for axis normalisation"
    )
    suggested_estimates: MissionPresetEstimates
