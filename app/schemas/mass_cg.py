"""Schemas for mass/CG design parameter endpoints."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class RecommendedCGRequest(BaseModel):
    """Input for computing the recommended CG position."""

    velocity: float = Field(15.0, gt=0, description="Airspeed in m/s")
    alpha: float = Field(0.0, description="Angle of attack in degrees")
    altitude: float = Field(0.0, ge=0, description="Altitude in meters")


class RecommendedCGResponse(BaseModel):
    """Result of the recommended CG computation."""

    neutral_point_x: float = Field(..., description="Neutral point x-position [m]")
    mac: float = Field(..., description="Mean aerodynamic chord [m]")
    target_static_margin: float = Field(..., description="Target static margin (fraction of MAC)")
    recommended_cg_x: float = Field(..., description="Recommended CG x-position [m]: NP - SM * MAC")


class DesignMetricsRequest(BaseModel):
    """Input for computing mass-dependent design metrics."""

    velocity: float = Field(15.0, gt=0, description="Cruise velocity in m/s")
    altitude: float = Field(0.0, ge=0, description="Altitude in meters")


class DesignMetricsResponse(BaseModel):
    """Mass-dependent derived design quantities."""

    mass_kg: float = Field(..., description="Effective mass used [kg]")
    s_ref: float = Field(..., description="Wing reference area [m^2]")
    cl_max: float = Field(..., description="Maximum lift coefficient")
    wing_loading_pa: float = Field(..., description="Wing loading W/S [N/m^2]")
    stall_speed_ms: float = Field(..., description="Stall speed at given altitude [m/s]")
    required_cl: float = Field(..., description="CL required for level flight at given velocity")
    cl_margin: float = Field(..., description="CL_max - required_CL (positive = above stall)")


class MassSweepRequest(BaseModel):
    """Input for a mass sweep (post-processing, no re-run of aero)."""

    masses_kg: list[Annotated[float, Field(gt=0)]] = Field(
        ..., min_length=1, max_length=100, description="List of mass values to evaluate [kg]"
    )
    velocity: float = Field(15.0, gt=0, description="Cruise velocity in m/s")
    altitude: float = Field(0.0, ge=0, description="Altitude in meters")


class MassSweepPoint(BaseModel):
    """One data point in a mass sweep."""

    mass_kg: float = Field(..., description="Mass at this sweep point [kg]")
    wing_loading_pa: float = Field(..., description="Wing loading W/S [N/m^2]")
    stall_speed_ms: float = Field(..., description="Stall speed at given altitude [m/s]")
    required_cl: float = Field(..., description="CL required for level flight")
    cl_margin: float = Field(..., description="CL_max - required_CL")


class MassSweepResponse(BaseModel):
    """Result of a mass sweep."""

    s_ref: float = Field(..., description="Wing reference area [m^2]")
    cl_max: float = Field(..., description="Maximum lift coefficient")
    velocity: float = Field(..., description="Cruise velocity used [m/s]")
    altitude: float = Field(..., description="Altitude used [m]")
    points: list[MassSweepPoint] = Field(..., description="Sweep data points")


class CGComparisonResponse(BaseModel):
    """Comparison between design CG and component-tree CG."""

    design_cg_x: float = Field(..., description="CG from effective design assumption [m]")
    component_cg_x: float | None = Field(
        None, description="CG computed from weight items [m] (None if no items)"
    )
    component_cg_y: float | None = Field(None, description="CG Y from weight items [m]")
    component_cg_z: float | None = Field(None, description="CG Z from weight items [m]")
    component_total_mass_kg: float | None = Field(
        None, description="Total mass from weight items [kg]"
    )
    delta_x: float | None = Field(
        None,
        description="design_cg_x - component_cg_x [m] (None if no component CG)",
    )
    within_tolerance: bool | None = Field(
        None,
        description="True if |delta_x| < 0.01 m (None if no component CG)",
    )
