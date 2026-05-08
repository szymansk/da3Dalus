"""Flight envelope schemas — V-n diagram, KPIs, and markers."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VnPoint(BaseModel):
    """Single point on the V-n diagram."""

    velocity_mps: float = Field(..., description="Airspeed in m/s")
    load_factor: float = Field(..., description="Load factor (g)")

    @field_validator("velocity_mps")
    @classmethod
    def velocity_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("velocity_mps must be non-negative")
        return v


class VnCurve(BaseModel):
    """Complete V-n envelope boundary curves."""

    positive: list[VnPoint] = Field(..., description="Positive-g boundary points")
    negative: list[VnPoint] = Field(..., description="Negative-g boundary points")
    dive_speed_mps: float = Field(..., description="Dive speed Vd in m/s")
    stall_speed_mps: float = Field(..., description="1-g stall speed in m/s")


class PerformanceKPI(BaseModel):
    """One key performance indicator derived from the flight envelope."""

    label: str = Field(..., description="Machine-readable identifier, e.g. 'stall_speed'")
    display_name: str = Field(..., description="Human-readable label, e.g. 'Stall Speed'")
    value: float = Field(..., description="Numeric KPI value")
    unit: str = Field(..., description="Display unit, e.g. 'm/s' or 'g'")
    source_op_id: int | None = Field(
        None, description="Operating-point ID this KPI was derived from, if any"
    )
    confidence: Literal["trimmed", "estimated", "limit"] = Field(
        ..., description="How the value was determined"
    )


class VnMarker(BaseModel):
    """An operating point plotted on the V-n diagram."""

    op_id: int = Field(..., description="Operating point database ID")
    name: str = Field(..., description="Operating point name")
    velocity_mps: float = Field(..., description="Airspeed in m/s")
    load_factor: float = Field(..., description="Load factor (g)")
    status: str = Field(..., description="Trim status, e.g. 'TRIMMED'")
    label: str = Field(..., description="Category label, e.g. 'cruise', 'best_ld'")


class FlightEnvelopeRead(BaseModel):
    """Read-only representation of a computed flight envelope."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    aeroplane_id: int
    vn_curve: VnCurve
    kpis: list[PerformanceKPI]
    operating_points: list[VnMarker]
    assumptions_snapshot: dict
    computed_at: datetime


class ComputeEnvelopeRequest(BaseModel):
    """Request body for (re-)computing the flight envelope."""

    force_recompute: bool = Field(
        False, description="If true, recompute even if a cached result exists"
    )
