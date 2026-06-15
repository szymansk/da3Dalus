"""Schemas for the Powertrain Sizing Modal (gh-197).

Provides pre-filled defaults for the modal dialog and the motor suggestion list.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MotorSuggestion(BaseModel):
    """A brushless motor from the component catalog, enriched for the modal."""

    id: int = Field(..., description="Component ID")
    name: str = Field(..., description="Motor name / model number")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    mass_g: Optional[float] = Field(None, ge=0, description="Mass in grams")
    efficiency_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Motor efficiency in percent. Read from specs.efficiency_pct when present; "
            "falls back to the brushless-motor default (85%)."
        ),
    )
    kv: Optional[float] = Field(None, gt=0, description="Motor KV (RPM/V)")
    max_power_w: Optional[float] = Field(None, ge=0, description="Peak shaft power rating in W")
    description: Optional[str] = Field(None, description="Free-text description")


class PowertrainModalParamsResponse(BaseModel):
    """Pre-filled defaults for the Powertrain Sizing Modal (gh-197).

    All editable fields in the modal have a suggested value here.  The frontend
    should populate the dialog with these and let the user override before
    calling POST /powertrain/sizing.
    """

    altitude_m: float = Field(
        0.0,
        ge=0,
        description="Operating altitude in m (default from mission context, fallback 0).",
    )
    cd0: float = Field(
        ...,
        ge=0,
        description=(
            "Zero-lift drag coefficient — from assumption_computation_context "
            "(gh-924 single source of truth), editable in the modal."
        ),
    )
    s_ref_m2: float = Field(
        ...,
        gt=0,
        description=(
            "Wing reference area in m² — from assumption_computation_context. "
            "Displayed read-only in the modal (constructive constraint)."
        ),
    )
    eta_prop: float = Field(
        0.65,
        gt=0,
        le=1.0,
        description="Propeller efficiency (editable; prop-finder is out of scope for Phase 1).",
    )
    eta_motor: float = Field(
        ...,
        gt=0,
        le=1.0,
        description=(
            "Motor efficiency as a fraction (e.g. 0.85). "
            "Editable; motor-specific value read from specs.efficiency_pct when a "
            "motor is selected."
        ),
    )
    motors: list[MotorSuggestion] = Field(
        default_factory=list,
        description="Brushless motors from the component library, sorted by name.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Informational notes about defaulted parameters (e.g. when "
            "assumption_computation_context is missing and RC-typical fallbacks are used)."
        ),
    )
