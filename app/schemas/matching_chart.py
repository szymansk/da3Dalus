"""Matching chart schemas — T/W vs W/S constraint diagram (gh-492)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AircraftMode = Literal["rc_runway", "rc_hand_launch", "uav_runway", "uav_belly_land"]


class ConstraintLine(BaseModel):
    """A line constraint T/W(W/S) or a vertical W/S_max line on the matching chart."""

    name: str = Field(..., description="Human-readable constraint name (e.g. 'Takeoff', 'Stall')")
    t_w_points: list[float] | None = Field(
        default=None,
        description="T/W values at each W/S sample point (line constraints); "
        "None for vertical (W/S_max) constraints.",
    )
    ws_max: float | None = Field(
        default=None,
        description="Maximum allowable W/S [N/m²] (vertical line); "
        "None for line constraints (use t_w_points).",
    )
    color: str = Field(..., description="Hex color for the constraint line in the chart")
    binding: bool = Field(
        ...,
        description="True when the design point lies on or very near this constraint line "
        "(i.e. this constraint is actively limiting the design)",
    )
    hover_text: str | None = Field(
        default=None,
        description="Short formula / reference shown on hover in the frontend chart",
    )


class DesignPoint(BaseModel):
    """Drag-and-droppable design point on the matching chart."""

    ws_n_m2: float = Field(..., description="Wing loading W/S [N/m²]")
    t_w: float = Field(
        ...,
        description="Thrust-to-weight ratio T_static_SL / W_MTOW (dimensionless)",
    )


class MatchingChartResponse(BaseModel):
    """Full matching chart response — T/W vs W/S constraint diagram.

    Convention: T/W = T_static_SL / W_MTOW; AR held constant during drag.
    Sizing interpretation A: W, T_static, AR, CD0, e fixed; S, b, V_md vary.
    """

    ws_range_n_m2: list[float] = Field(
        ...,
        description="W/S sweep values [N/m²] — the X-axis of the chart",
    )
    constraints: list[ConstraintLine] = Field(
        ...,
        description="All constraint lines.  Each has either t_w_points (line) or ws_max (vertical).",
    )
    design_point: DesignPoint = Field(
        ...,
        description="Current aircraft design point derived from mass, thrust and wing area",
    )
    feasibility: Literal["feasible", "infeasible_below_constraints"] = Field(
        ...,
        description="'feasible' when design point satisfies all constraints; "
        "'infeasible_below_constraints' when it falls below one or more constraint lines",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (e.g. polar fallback used, V_cruise estimated)",
    )
