"""Pydantic schemas for spanwise shear + bending-moment distribution (gh-1002)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpanwiseLoadEntry(BaseModel):
    """Per-strip structural loads referenced to the wing root."""

    y_m: float = Field(
        ..., description="Spanwise position of this strip's centre (m), from wing root"
    )
    chord_m: float = Field(..., description="Local chord at this strip (m)")
    shear_N: float = Field(
        ..., description="Running shear force V(y): sum of lift outboard of y (N)"
    )
    bending_moment_Nm: float = Field(
        ...,
        description="Running bending moment M(y): sum of L_j*(y_j - y) for all strips outboard (N·m)",
    )


class SurfaceSpanwiseLoads(BaseModel):
    """Shear + bending-moment distribution for one aerodynamic surface."""

    surface_name: str = Field(..., description="Name of the aerodynamic surface")

    starboard: list[SpanwiseLoadEntry] = Field(
        ...,
        description=(
            "Starboard (y ≥ 0) half-span distribution, sorted outboard-first "
            "(index 0 = tip, last index = root). Empty when all strips are port-side."
        ),
    )
    port: list[SpanwiseLoadEntry] = Field(
        ...,
        description=(
            "Port (y < 0) half-span distribution, sorted outboard-first "
            "(index 0 = most-negative-y tip, last index = root). "
            "Empty for surfaces that lie entirely in the starboard half."
        ),
    )

    root_shear_N_starboard: float = Field(..., description="Peak shear at the starboard root (N)")
    root_shear_N_port: float = Field(..., description="Peak shear at the port root (N)")
    root_bending_moment_Nm_starboard: float = Field(
        ...,
        description="Root bending moment on the starboard half (N·m) — headline spar-sizing value",
    )
    root_bending_moment_Nm_port: float = Field(
        ..., description="Root bending moment on the port half (N·m)"
    )


class SpanwiseLoadsResponse(BaseModel):
    """Full spanwise shear + bending-moment response for one operating point (gh-1002)."""

    alpha: float = Field(..., description="Angle of attack used for the run (deg)")
    velocity_mps: float = Field(..., description="Freestream velocity (m/s)")
    altitude_m: float = Field(..., description="Altitude (m)")
    dynamic_pressure_Pa: float = Field(
        ..., description="Dynamic pressure q = ½·ρ·V² (Pa) at the given altitude and velocity"
    )
    surfaces: list[SurfaceSpanwiseLoads] = Field(
        ..., description="Per-surface spanwise load distributions"
    )
