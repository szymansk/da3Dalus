"""Pydantic schemas for SM sizing constraint — gh-494."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SmOption(BaseModel):
    """A single sizing suggestion option."""

    lever: Literal["wing_shift", "htail_scale"] = Field(
        ...,
        description="Which lever to apply: 'wing_shift' (move wing fore/aft) or 'htail_scale' (chord-scale HS).",
    )
    delta_value: float = Field(
        ...,
        description=(
            "Magnitude of the change. For wing_shift: metres (negative = forward). "
            "For htail_scale: fraction (0.20 = +20% chord)."
        ),
    )
    delta_unit: str = Field(
        ...,
        description="Unit of delta_value. 'm' for wing_shift, 'fraction' for htail_scale.",
    )
    predicted_sm: float = Field(
        ...,
        description="Predicted SM after applying this option (dimensionless, fraction of MAC).",
    )
    narrative: str = Field(
        ...,
        description="Human-readable description of the change and its expected effect.",
    )


class SmSuggestionResponse(BaseModel):
    """Response from GET /aeroplanes/{uuid}/sm-suggestion."""

    status: Literal["ok", "suggestion", "error", "not_applicable"] = Field(
        ...,
        description=(
            "ok: SM already in target range [target_sm, 0.20]. "
            "suggestion: SM deviates, options provided. "
            "error: SM < 0.02 (unstable), block_save=True. "
            "not_applicable: canard/tailless/no-analysis."
        ),
    )
    options: list[SmOption] = Field(
        default_factory=list,
        description="One option per lever (wing_shift, htail_scale). Empty when status=ok or not_applicable.",
    )
    block_save: bool = Field(
        False,
        description="True when SM < 0.02 — aircraft is aerodynamically unstable.",
    )
    mass_coupling_warning: str | None = Field(
        None,
        description=(
            "Present when wing_shift option exists: warns that wing-mass CG shift "
            "is not included in the analytic formula (~15% systematic error)."
        ),
    )
    message: str | None = Field(
        None,
        description="Human-readable status message (for ok/error/not_applicable).",
    )
    hint: str | None = Field(
        None,
        description="Hint for not_applicable (e.g. 'Run analysis first').",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Additional advisory warnings (e.g. negative S_H, forward-CG clip).",
    )


class SmApplyRequest(BaseModel):
    """Request body for POST /aeroplanes/{uuid}/sm-suggestions/apply."""

    lever: Literal["wing_shift", "htail_scale"] = Field(
        ...,
        description="Which lever to apply.",
    )
    delta_value: float = Field(
        ...,
        description=(
            "Change magnitude. wing_shift: metres. htail_scale: fraction (0.20 = +20%)."
        ),
    )
    dry_run: bool = Field(
        False,
        description="When True: compute predicted SM only; do NOT modify the database.",
    )


class SmApplyResponse(BaseModel):
    """Response from POST /aeroplanes/{uuid}/sm-suggestions/apply."""

    lever: str = Field(..., description="Which lever was applied.")
    delta_value: float = Field(..., description="The delta_value that was applied.")
    predicted_sm: float = Field(
        ...,
        description="Predicted (analytic) SM after applying this change.",
    )
    dry_run: bool = Field(
        ...,
        description="True when no DB changes were made (preview mode).",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Advisory warnings about the apply operation.",
    )
