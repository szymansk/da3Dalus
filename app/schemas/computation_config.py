"""Computation config schemas — controls the alpha-sweep and debounce parameters
used when auto-computing design assumptions (cl_max, cd0, cg_x) from geometry."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ComputationConfigRead(BaseModel):
    """Full representation of a computation config record, returned by the API."""

    id: int
    aeroplane_id: int
    coarse_alpha_min_deg: float = Field(..., description="Lower bound of the coarse alpha sweep (deg)")
    coarse_alpha_max_deg: float = Field(..., description="Upper bound of the coarse alpha sweep (deg)")
    coarse_alpha_step_deg: float = Field(..., description="Step size of the coarse alpha sweep (deg)")
    fine_alpha_margin_deg: float = Field(
        ..., description="Margin around the coarse peak used for the fine sweep (deg)"
    )
    fine_alpha_step_deg: float = Field(..., description="Step size of the fine alpha sweep (deg)")
    fine_velocity_count: int = Field(..., description="Number of velocity samples in the fine sweep")
    debounce_seconds: float = Field(
        ..., description="Idle time before an auto-compute job is triggered (s)"
    )

    model_config = ConfigDict(from_attributes=True)


class ComputationConfigWrite(BaseModel):
    """Partial-update payload for a computation config; all fields are optional."""

    coarse_alpha_min_deg: float | None = Field(
        None, description="Lower bound of the coarse alpha sweep (deg)"
    )
    coarse_alpha_max_deg: float | None = Field(
        None, description="Upper bound of the coarse alpha sweep (deg)"
    )
    coarse_alpha_step_deg: float | None = Field(
        None, gt=0, description="Must be positive — step size of the coarse alpha sweep (deg)"
    )
    fine_alpha_margin_deg: float | None = Field(
        None, gt=0, description="Must be positive — margin around the coarse peak (deg)"
    )
    fine_alpha_step_deg: float | None = Field(
        None, gt=0, description="Must be positive — step size of the fine alpha sweep (deg)"
    )
    fine_velocity_count: int | None = Field(
        None, ge=2, le=50, description="Number of velocity samples (2–50)"
    )
    debounce_seconds: float | None = Field(
        None, ge=0.5, le=30.0, description="Debounce idle time in seconds (0.5–30)"
    )
