"""Pydantic schemas for the electric endurance / range service — gh-490."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EnduranceResponse(BaseModel):
    """Response from the electric endurance / range endpoint."""

    # --- Core KPIs ---
    t_endurance_max_s: float | None = Field(
        None, description="Maximum endurance at V_min_sink (V_mp) in seconds"
    )
    range_max_m: float | None = Field(None, description="Maximum range at V_md in metres")

    # --- Power budget ---
    p_req_at_v_md_w: float | None = Field(
        None, description="Power required at V_md (min-drag speed) in Watts"
    )
    p_req_at_v_min_sink_w: float | None = Field(
        None, description="Power required at V_min_sink (min-power speed) in Watts"
    )

    # --- Motor margin ---
    p_margin: float | None = Field(
        None, description="(P_motor_continuous - P_req(V_md)) / P_motor_continuous"
    )
    p_margin_class: str | None = Field(
        None,
        description=("comfortable | feasible but tight | infeasible — motor underpowered"),
    )

    # --- Battery cross-check ---
    battery_mass_g_predicted: float | None = Field(
        None,
        description="Capacity-implied battery mass in grams (capacity_wh / E* × 1000)",
    )

    # --- Confidence & quality ---
    confidence: Literal["computed", "estimated"] = Field(
        "estimated",
        description=(
            "'computed' when polar fit is reliable; "
            "'estimated' when e_oswald fallback or poor polar quality"
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Advisory messages about input quality or assumptions",
    )
