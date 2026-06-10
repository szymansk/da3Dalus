"""Response and request schemas for the turbulator optimizer endpoint — gh-935 Part C."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TurbulatorOptimizeRequest(BaseModel):
    """Request body for POST /aeroplanes/{id}/turbulator/optimize."""

    scope: Literal["section", "segment", "whole"] = Field(
        "section",
        description=(
            "'section' → per-section optima (independent xtr per section); "
            "'segment' → one xtr per wing segment (representative Re); "
            "'whole'   → single global xtr for the whole wing."
        ),
    )


class TurbulatorSectionResult(BaseModel):
    """Optimizer result for one spanwise section."""

    y_m: float = Field(..., description="Spanwise position [m]")
    chord_m: float = Field(..., description="Local chord [m]")
    re_local: float = Field(..., description="Local chord Reynolds number")
    cl: float = Field(..., description="Section lift coefficient at operating point")
    xtr_opt: float = Field(
        ..., description="Optimal trip position x/c that minimises cd"
    )
    cd_clean: float = Field(..., description="2D cd at natural transition (xtr=1.0)")
    cd_tripped: float = Field(..., description="2D cd at xtr_opt")
    delta_cd: float = Field(..., description="cd_tripped − cd_clean")
    warnings: list[str] = Field(
        default_factory=list,
        description="Per-section warnings (NaN convergence, low confidence, boundary minimum)",
    )


class TurbulatorOptimizerSummarySchema(BaseModel):
    """3-D aggregate summary of the turbulator effect."""

    delta_cd0: float = Field(
        ..., description="Area-weighted 3D ΔCD0 = Σ(cd_tripped−cd_clean)·Sᵢ/Sref"
    )
    l_d_clean: float = Field(..., description="L/D without turbulator effect")
    l_d_tripped: float = Field(..., description="L/D with turbulator at xtr_opt")
    delta_l_d: float = Field(..., description="L/D improvement (l_d_tripped − l_d_clean)")


class TurbulatorOptimizerResponse(BaseModel):
    """Full response for POST /aeroplanes/{id}/turbulator/optimize."""

    sections: list[TurbulatorSectionResult] = Field(
        default_factory=list,
        description="Per-section optimizer results",
    )
    summary: TurbulatorOptimizerSummarySchema = Field(
        ..., description="3D aggregate L/D and ΔCD0 summary"
    )
    scope: str = Field(..., description="Scope used for this optimization run")
