"""Pydantic schemas for AVL strip-force distribution responses."""

from pydantic import BaseModel, Field


class StripForceEntry(BaseModel):
    j: int = Field(..., description="Strip index")
    x_le: float = Field(..., alias="Xle", description="Strip leading-edge X (m)")
    y_le: float = Field(..., alias="Yle", description="Strip leading-edge Y (m)")
    z_le: float = Field(..., alias="Zle", description="Strip leading-edge Z (m)")
    chord: float = Field(..., alias="Chord", description="Local chord (m)")
    area: float = Field(..., alias="Area", description="Strip area (m²)")
    c_cl: float = Field(..., description="Chord × Cl product")
    ai: float = Field(..., description="Induced angle of attack (rad)")
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
    mach: float = Field(..., description="Mach number")
    sref: float = Field(..., description="Reference area (m²)")
    cref: float = Field(..., description="Reference chord (m)")
    bref: float = Field(..., description="Reference span (m)")
    surfaces: list[SurfaceStripForces] = Field(..., description="Per-surface strip forces")
