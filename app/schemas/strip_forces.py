"""Pydantic schemas for AVL strip-force distribution responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class StripForceEntry(BaseModel):
    j: int = Field(..., description="Strip index")
    x_le: float = Field(..., alias="Xle", description="Strip leading-edge X (m)")
    y_le: float = Field(..., alias="Yle", description="Strip leading-edge Y (m)")
    z_le: float = Field(..., alias="Zle", description="Strip leading-edge Z (m)")
    chord: float = Field(..., alias="Chord", description="Local chord (m)")
    area: float = Field(..., alias="Area", description="Strip area (m²)")
    c_cl: float = Field(..., description="Chord × Cl product")
    ai: float = Field(..., description="Induced angle of attack (deg)")
    cl_norm: float = Field(..., description="Normalized Cl (cl × chord / Cref)")
    cl: float = Field(..., description="Local lift coefficient")
    cd: float = Field(..., description="Local drag coefficient")
    cdv: float = Field(..., description="Local viscous drag coefficient")
    cm_c4: float = Field(..., alias="cm_c/4", description="Moment coefficient at c/4")
    cm_le: float = Field(..., alias="cm_LE", description="Moment coefficient at LE")
    cp_xc: float = Field(..., alias="C.P.x/c", description="Center of pressure x/c")

    model_config = {"populate_by_name": True}


class SurfaceStripForces(BaseModel):
    surface_name: str = Field(..., description="AVL surface name")
    surface_number: int = Field(..., description="AVL surface index")
    n_chordwise: int = Field(..., description="Number of chordwise panels")
    n_spanwise: int = Field(..., description="Number of spanwise strips")
    surface_area: float = Field(..., description="Total surface area (m²)")
    strips: list[StripForceEntry] = Field(..., description="Per-strip force data")


class StripForcesResponse(BaseModel):
    alpha: float = Field(..., description="Angle of attack (deg)")
    beta: float = Field(..., description="Sideslip angle (deg)")
    mach: float = Field(..., description="Mach number")
    sref: float = Field(..., description="Reference area (m²)")
    cref: float = Field(..., description="Reference chord (m)")
    bref: float = Field(..., description="Reference span (m)")
    surfaces: list[SurfaceStripForces] = Field(..., description="Per-surface strip forces")

    # gh-592: full compute-parameter echo so the Trefftz-Plane Plotly annotation
    # can display every input that produced the run. New fields are optional for
    # backward-compatibility with any existing consumers, but the analysis
    # service always populates them.
    velocity_mps: Optional[float] = Field(
        None, description="Freestream velocity (m/s) used for the run"
    )
    altitude_m: Optional[float] = Field(None, description="Altitude (m) used to set the atmosphere")
    xyz_ref_m: Optional[list[float]] = Field(
        None,
        description="Moment/CG reference point [x, y, z] in metres",
        min_length=3,
        max_length=3,
    )
    wing_name: Optional[str] = Field(
        None,
        description="Wing/aeroplane identifier the strip-forces were computed for",
    )
    reynolds: Optional[float] = Field(
        None,
        description="Reynolds number based on V, Cref, and the kinematic viscosity at altitude",
    )
    aero_model: Optional[Literal["AVL", "ASB"]] = Field(
        "AVL",
        description=(
            "Aerodynamic solver that produced the strip forces: 'ASB' for the "
            "default in-process VortexLatticeMethod, 'AVL' for the subprocess "
            "fallback (gh-674)"
        ),
    )
    computed_at: Optional[datetime] = Field(
        None, description="UTC timestamp when the run completed (ISO-8601)"
    )
    operating_point_label: Optional[str] = Field(
        None,
        description="Human-readable label of the bound stored operating point, if any",
    )
