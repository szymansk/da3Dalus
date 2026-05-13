"""Pydantic schemas for Loading Scenarios (gh-488).

Loading-Envelope = CG range produced by user-defined loading scenarios.
Stability-Envelope = physically permissible CG range from aerodynamics.

Source: Anderson 6e §7.5–§7.7, Scholz §4.2 (10_BoxWingSystematic.md).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Supported aircraft classes for template selection and SM thresholds
AIRCRAFT_CLASS = Literal[
    "rc_trainer",
    "rc_aerobatic",
    "rc_pylon_3d",
    "rc_combust",
    "uav_survey",
    "glider",
    "boxwing",
]

# Valid adhoc item categories (matched to Cirrus W&B form UX)
ADHOC_CATEGORY = Literal["pilot", "payload", "ballast", "fuel", "fpv_gear", "other"]

# Overall classification of the CG envelope status
# "unknown" is returned when the stability envelope cannot be computed
# (x_NP and MAC not yet populated by recompute_assumptions).
CG_CLASSIFICATION = Literal["error", "warn", "ok", "unknown"]


# ---------------------------------------------------------------------------
# Component override sub-schemas
# ---------------------------------------------------------------------------


class ComponentToggle(BaseModel):
    """Enable or disable a component in this loading scenario."""

    component_uuid: str = Field(..., description="UUID of the component to toggle")
    enabled: bool = Field(..., description="True = component included; False = removed")


class MassOverride(BaseModel):
    """Override the mass of a component for this scenario."""

    component_uuid: str = Field(..., description="UUID of the component")
    mass_kg_override: float = Field(..., gt=0, description="Replacement mass in kg")


class PositionOverride(BaseModel):
    """Override the CG position of a component for this scenario."""

    component_uuid: str = Field(..., description="UUID of the component")
    x_m_override: float = Field(..., description="New longitudinal CG position [m]")
    y_m_override: float | None = Field(None, description="New lateral CG position [m]")
    z_m_override: float | None = Field(None, description="New vertical CG position [m]")


class AdhocItem(BaseModel):
    """An item not in the component tree — pilot, payload, ballast, FPV gear, etc.

    Matches the W&B form pattern from certified aircraft (Cirrus SR22, etc.),
    making the UX familiar to both hobbyists and professional UAV operators.
    """

    name: str = Field(..., description="Human-readable name of the item")
    mass_kg: float = Field(..., gt=0, description="Mass in kg")
    x_m: float = Field(..., description="Longitudinal CG position [m]")
    y_m: float = Field(0.0, description="Lateral CG position [m]")
    z_m: float = Field(0.0, description="Vertical CG position [m]")
    category: ADHOC_CATEGORY = Field("payload", description="Category of the item")


class ComponentOverrides(BaseModel):
    """All component overrides for a loading scenario."""

    toggles: list[ComponentToggle] = Field(
        default_factory=list, description="Enable/disable components"
    )
    mass_overrides: list[MassOverride] = Field(
        default_factory=list, description="Mass overrides for components"
    )
    position_overrides: list[PositionOverride] = Field(
        default_factory=list, description="Position overrides for components"
    )
    adhoc_items: list[AdhocItem] = Field(
        default_factory=list, description="Adhoc items not in the component tree"
    )


# ---------------------------------------------------------------------------
# Loading scenario CRUD schemas
# ---------------------------------------------------------------------------


class LoadingScenarioCreate(BaseModel):
    """Request body for creating a loading scenario."""

    name: str = Field(..., description="Human-readable name, e.g. 'Battery Fwd'")
    aircraft_class: AIRCRAFT_CLASS = Field(
        "rc_trainer", description="Aircraft class for template selection and SM thresholds"
    )
    component_overrides: ComponentOverrides = Field(
        default_factory=ComponentOverrides,
        description="Component-level overrides and adhoc items for this scenario",
    )
    is_default: bool = Field(
        False,
        description=(
            "When True, this scenario's CG is used as the legacy cg_agg_m "
            "for backward-compatible single-value clients"
        ),
    )


class LoadingScenarioUpdate(BaseModel):
    """Request body for patching a loading scenario (all fields optional)."""

    name: str | None = None
    aircraft_class: AIRCRAFT_CLASS | None = None
    component_overrides: ComponentOverrides | None = None
    is_default: bool | None = None


class LoadingScenarioRead(BaseModel):
    """Response body for a loading scenario."""

    id: int
    aeroplane_id: int
    name: str
    aircraft_class: str
    component_overrides: ComponentOverrides
    is_default: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CG envelope response schema
# ---------------------------------------------------------------------------


class CgEnvelopeRead(BaseModel):
    """CG envelope summary for an aeroplane (gh-488).

    Combines the Loading-Envelope (what loading scenarios produce) with the
    Stability-Envelope (what aerodynamics allows), and provides a classification.

    Loading-Envelope:
        cg_loading_fwd_m = min(cg_x over all scenarios)
        cg_loading_aft_m = max(cg_x over all scenarios)

    Stability-Envelope:
        cg_stability_aft_m = x_NP - target_sm * MAC  (Anderson §7.5)
        cg_stability_fwd_m = x_NP - 0.30 * MAC  (stub; full elevator-authority
                              calculation is a follow-up ticket)

    Validation: cg_loading_aft_m MUST be <= cg_stability_aft_m.
    """

    cg_loading_fwd_m: float = Field(..., description="Forward-most loading CG [m]")
    cg_loading_aft_m: float = Field(..., description="Aft-most loading CG [m]")
    cg_stability_fwd_m: float | None = Field(
        None,
        description=(
            "Forward stability limit (elevator-authority stub = x_NP - 0.30*MAC) [m]. "
            "None when x_NP / MAC not yet computed (run recompute_assumptions first). "
            "TODO: replace with full Cm-trim@CL_max_landing per Anderson §7.7."
        ),
    )
    cg_stability_aft_m: float | None = Field(
        None, description="Aft stability limit = x_NP - target_sm*MAC [m]. None until computed."
    )
    sm_at_fwd: float | None = Field(
        None,
        description=(
            "Static margin at forward loading CG (dimensionless). "
            "None when stability envelope is unavailable."
        ),
    )
    sm_at_aft: float | None = Field(
        None,
        description=(
            "Static margin at aft loading CG (dimensionless). "
            "None when stability envelope is unavailable."
        ),
    )
    classification: CG_CLASSIFICATION = Field(
        ...,
        description=(
            "Overall envelope classification: error | warn | ok | unknown. "
            "'unknown' when x_NP/MAC not yet computed — run recompute_assumptions."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list, description="Human-readable warnings and errors"
    )
