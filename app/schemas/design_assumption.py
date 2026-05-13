"""Design assumption schemas — tracking manual estimates vs. computed values."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VALID_PARAMETERS = Literal[
    "mass",
    "cg_x",
    "target_static_margin",
    "cd0",
    "cl_max",
    "g_limit",
    "power_to_weight",
    "prop_efficiency",
    # Electric endurance / propulsion — gh-490
    "battery_capacity_wh",
    "battery_specific_energy_wh_per_kg",
    "propulsion_eta_motor",
    "propulsion_eta_esc",
    "motor_continuous_power_w",
    # Static thrust — gh-489: rc_pylon_3d into Literal + unit comment + stash resolve)
    "t_static_N": "N",
}

PARAMETER_DEFAULTS: dict[str, float] = {
    "mass": 1.5,
    "cg_x": 0.15,
    "target_static_margin": 0.12,
    "cd0": 0.03,
    "cl_max": 1.4,
    "g_limit": 3.0,
    # Typical RC ranges (per common P/W chart):
    #   160-200 W/kg → trainer / slow aerobatic
    #   200-240 W/kg → sport aerobatic / scale     ← default
    #   240-290 W/kg → advanced aerobatic / fast
    #   290-330 W/kg → light 3D / ducted fan
    #   330-440 W/kg → unlimited 3D
    #   0           → glider (no powertrain, V_max = structural V_NE)
    "power_to_weight": 220.0,
    # Typical 0.55-0.75 for RC propellers at cruise; 0.65 is a sane middle.
    "prop_efficiency": 0.65,
    # Electric endurance / propulsion assumptions — gh-490
    # battery_capacity_wh: 0.0 signals "not yet set" (missing input →
    # compute_endurance returns None values with a warning).
    "battery_capacity_wh": 0.0,
    # Pack-level LiPo specific energy (Hepperle 2012; cell-level ≈ 220 Wh/kg)
    "battery_specific_energy_wh_per_kg": 180.0,
    # Brushless outrunner motor efficiency (typical 80-90 %)
    "propulsion_eta_motor": 0.85,
    # Modern ESC efficiency (typical 92-96 %)
    "propulsion_eta_esc": 0.94,
    # Motor continuous power rating: 0.0 signals "not yet set" (→ p_margin unknown)
    "motor_continuous_power_w": 0.0,
    # Static thrust at zero velocity (gh-489 takeoff field length).
    # Default = 0 (glider / unknown). User MUST override for powered runway takeoff.: rc_pylon_3d into Literal + unit comment + stash resolve)
    "t_static_N": 0.0,
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

    estimate_value: float = Field(
        ..., allow_inf_nan=False, description="Manual estimate for this parameter"
    )


class AssumptionSourceSwitch(BaseModel):
    """Payload for switching between ESTIMATE and CALCULATED sources."""

    active_source: ACTIVE_SOURCE = Field(
        ..., description="Which value to use: ESTIMATE or CALCULATED"
    )


class AssumptionRead(BaseModel):
    """Read-only representation of one design assumption."""

    id: int
    parameter_name: VALID_PARAMETERS
    estimate_value: float
    calculated_value: float | None = None
    calculated_source: str | None = None
    active_source: ACTIVE_SOURCE
    effective_value: float = Field(..., description="Value used for simulations")
    divergence_pct: float | None = None
    divergence_level: DIVERGENCE_LEVEL = Field(
        ..., description="none, info, warning, or alert"
    )
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
