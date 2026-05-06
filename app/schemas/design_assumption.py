"""Design assumption schemas — tracking manual estimates vs. computed values."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VALID_PARAMETERS = Literal["mass", "cg_x", "target_static_margin", "cd0", "cl_max", "g_limit"]
ACTIVE_SOURCE = Literal["ESTIMATE", "CALCULATED"]
DIVERGENCE_LEVEL = Literal["none", "info", "warning", "alert"]

DESIGN_CHOICE_PARAMS = frozenset({"target_static_margin", "g_limit"})

PARAMETER_UNITS: dict[str, str] = {
    "mass": "kg",
    "cg_x": "m",
    "target_static_margin": "% MAC",
    "cd0": "",
    "cl_max": "",
    "g_limit": "g",
}

PARAMETER_DEFAULTS: dict[str, float] = {
    "mass": 1.5,
    "cg_x": 0.15,
    "target_static_margin": 0.12,
    "cd0": 0.03,
    "cl_max": 1.4,
    "g_limit": 3.0,
}


def compute_divergence_pct(estimate: float, calculated: float | None) -> float | None:
    """Percentage divergence between estimate and calculated value."""
    if calculated is None or calculated == 0:
        return None
    return round(abs(estimate - calculated) / abs(calculated) * 100, 1)


def divergence_level(pct: float | None) -> DIVERGENCE_LEVEL:
    """Map a divergence percentage to a severity level."""
    if pct is None:
        return "none"
    if pct < 5:
        return "none"
    if pct < 15:
        return "info"
    if pct <= 30:
        return "warning"
    return "alert"


class AssumptionWrite(BaseModel):
    """Payload for updating a design assumption estimate."""

    estimate_value: float = Field(..., description="Manual estimate for this parameter")


class AssumptionSourceSwitch(BaseModel):
    """Payload for switching between ESTIMATE and CALCULATED sources."""

    active_source: ACTIVE_SOURCE = Field(
        ..., description="Which value to use: ESTIMATE or CALCULATED"
    )


class AssumptionRead(BaseModel):
    """Read-only representation of one design assumption."""

    id: int
    parameter_name: str
    estimate_value: float
    calculated_value: float | None = None
    calculated_source: str | None = None
    active_source: str
    effective_value: float = Field(..., description="Value used for simulations")
    divergence_pct: float | None = None
    divergence_level: str = Field(..., description="none, info, warning, or alert")
    unit: str = Field("", description="Display unit for this parameter")
    is_design_choice: bool = Field(
        False, description="True for params that are never auto-calculated"
    )
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssumptionsSummary(BaseModel):
    """Summary of all design assumptions for an aeroplane."""

    assumptions: list[AssumptionRead] = Field(default_factory=list)
    warnings_count: int = Field(
        0, description="Count of assumptions with divergence_level >= warning"
    )
