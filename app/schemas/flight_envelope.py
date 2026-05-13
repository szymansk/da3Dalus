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


class GustCriticalWarning(BaseModel):
    """Structural warning emitted when gust load exceeds maneuver g-limit.

    Indicates the aircraft is gust-critical: the structural sizing must
    account for the gust envelope, not just the maneuver envelope.
    See CS-VLA.333 / FAR-25.341 for regulatory basis.
    """

    velocity_mps: float = Field(
        ..., description="Airspeed at which gust load exceeds g-limit, in m/s"
    )
    n_gust: float = Field(..., description="Peak gust load factor (1 + Δn) at this speed")
    g_limit: float = Field(..., description="Maneuver g-limit the gust load exceeds")
    message: str = Field(
        ...,
        description=(
            "Human-readable warning, e.g. "
            "'Gust-critical: structure sized by gust loads, not maneuver loads'"
        ),
    )


class VnCurve(BaseModel):
    """Complete V-n envelope boundary curves.

    Fields ``gust_lines_positive`` and ``gust_lines_negative`` carry the
    Pratt-Walker discrete gust envelope (CS-VLA.333 / FAR-25.341).
    They default to empty lists for backwards compatibility when gust data
    is unavailable (e.g. no wing geometry yet).
    """

    positive: list[VnPoint] = Field(..., description="Positive-g maneuver boundary points")
    negative: list[VnPoint] = Field(..., description="Negative-g maneuver boundary points")
    dive_speed_mps: float = Field(..., description="Dive speed Vd in m/s")
    stall_speed_mps: float = Field(..., description="1-g stall speed in m/s")
    gust_lines_positive: list[VnPoint] = Field(
        default_factory=list,
        description=(
            "Positive gust load-factor line (1 + Δn_gust) vs. airspeed. "
            "Pratt-Walker model, U_gust = 15.24 m/s at V_C, 7.62 m/s at V_D "
            "(CS-VLA.333(c)(1) / FAR-23.333(c))."
        ),
    )
    gust_lines_negative: list[VnPoint] = Field(
        default_factory=list,
        description=(
            "Negative gust load-factor line (1 − Δn_gust) vs. airspeed. "
            "Same regulatory basis as gust_lines_positive."
        ),
    )
    gust_warnings: list[GustCriticalWarning] = Field(
        default_factory=list,
        description=(
            "Structural warnings emitted when gust load exceeds maneuver g-limit "
            "at V_C or V_D. Empty when the aircraft is not gust-critical."
        ),
    )


class PerformanceKPI(BaseModel):
    """One key performance indicator derived from the flight envelope."""

    label: str = Field(..., description="Machine-readable identifier, e.g. 'stall_speed'")
    display_name: str = Field(..., description="Human-readable label, e.g. 'Stall Speed'")
    value: float = Field(..., description="Numeric KPI value")
    unit: str = Field(..., description="Display unit, e.g. 'm/s' or 'g'")
    source_op_id: int | None = Field(
        None, description="Operating-point ID this KPI was derived from, if any"
    )
    confidence: Literal["trimmed", "computed", "estimated", "limit"] = Field(
        ...,
        description=(
            "How the value was determined: "
            "'trimmed' = from a TRIMMED operating point; "
            "'computed' = polar/physics-derived from cached assumptions "
            "(e.g. V_md from C_D0/AR/e); "
            "'estimated' = heuristic shortcut (e.g. 1.4·V_s); "
            "'limit' = boundary or user-supplied limit."
        ),
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
    """Read-only representation of a computed flight envelope.

    ``gust_warnings`` surfaces any structural warnings at the API level so
    the frontend can render a prominent banner when the aircraft is
    gust-critical (gh-487).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    aeroplane_id: int
    vn_curve: VnCurve
    kpis: list[PerformanceKPI]
    operating_points: list[VnMarker]
    assumptions_snapshot: dict
    computed_at: datetime
    gust_warnings: list[GustCriticalWarning] = Field(
        default_factory=list,
        description=(
            "Top-level gust-critical warnings (mirrors vn_curve.gust_warnings). "
            "Non-empty when gust loads exceed maneuver g-limit at V_C or V_D."
        ),
    )


class ComputeEnvelopeRequest(BaseModel):
    """Request body for (re-)computing the flight envelope."""

    force_recompute: bool = Field(
        False, description="If true, recompute even if a cached result exists"
    )
