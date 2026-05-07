"""Pydantic schemas for stability summary endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StabilitySummaryResponse(BaseModel):
    """Summary of static stability characteristics from an aerodynamic analysis."""

    static_margin: Optional[float] = Field(
        None,
        description="Static margin as fraction of MAC. Positive = stable. "
                    "Calculated as (Xnp - Xcg) / MAC.",
    )
    neutral_point_x: Optional[float] = Field(
        None,
        description="Neutral point x-coordinate in meters.",
    )
    cg_x: Optional[float] = Field(
        None,
        description="Center of gravity x-coordinate (xyz_ref) in meters.",
    )
    trim_alpha_deg: Optional[float] = Field(
        None,
        description="Angle of attack at the analyzed operating point in degrees.",
    )
    trim_elevator_deg: Optional[float] = Field(
        None,
        description="Elevator deflection for trim in degrees (if available).",
    )
    Cma: Optional[float] = Field(
        None,
        description="Pitching moment coefficient derivative w.r.t. alpha (dCm/dalpha). "
                    "Negative = longitudinally stable.",
    )
    Cnb: Optional[float] = Field(
        None,
        description="Yawing moment coefficient derivative w.r.t. beta (dCn/dbeta). "
                    "Positive = directionally stable.",
    )
    Clb: Optional[float] = Field(
        None,
        description="Rolling moment coefficient derivative w.r.t. beta (dCl/dbeta). "
                    "Negative = laterally stable (dihedral effect).",
    )
    is_statically_stable: bool = Field(
        False,
        description="True if Cma < 0 (longitudinally stable).",
    )
    is_directionally_stable: bool = Field(
        False,
        description="True if Cnb > 0 (directionally stable / weathervane effect).",
    )
    is_laterally_stable: bool = Field(
        False,
        description="True if Clb < 0 (dihedral effect provides roll stability).",
    )
    analysis_method: Optional[str] = Field(
        None,
        description="Method used for the analysis (avl, aerobuildup, vortex_lattice).",
    )
    static_margin_pct: Optional[float] = Field(
        None,
        description="Static margin as percentage of MAC (static_margin × 100).",
    )
    stability_class: Optional[str] = Field(
        None,
        description="Stability classification: stable, neutral, or unstable.",
    )
    cg_range_forward: Optional[float] = Field(
        None,
        description="Forward CG limit in meters (most stable).",
    )
    cg_range_aft: Optional[float] = Field(
        None,
        description="Aft CG limit in meters (least stable).",
    )
    mac: Optional[float] = Field(
        None,
        description="Mean aerodynamic chord in meters.",
    )


class StabilityResultRead(BaseModel):
    """Read-only representation of a persisted stability result."""

    id: int
    aeroplane_id: int
    solver: str
    neutral_point_x: Optional[float] = None
    mac: Optional[float] = None
    cg_x_used: Optional[float] = None
    static_margin_pct: Optional[float] = None
    stability_class: Optional[str] = None
    cg_range_forward: Optional[float] = None
    cg_range_aft: Optional[float] = None
    Cma: Optional[float] = None
    Cnb: Optional[float] = None
    Clb: Optional[float] = None
    trim_alpha_deg: Optional[float] = None
    trim_elevator_deg: Optional[float] = None
    is_statically_stable: bool = False
    is_directionally_stable: bool = False
    is_laterally_stable: bool = False
    computed_at: datetime
    status: str = "CURRENT"
    geometry_hash: Optional[str] = None

    model_config = {"from_attributes": True}
