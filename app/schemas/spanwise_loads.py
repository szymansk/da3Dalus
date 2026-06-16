"""Pydantic schemas for spanwise shear + bending-moment distribution (gh-1002).

gh-1008: Extended with SpanwiseLoadsWithSizingResponse for the optional
spar-sizing block returned when sizing params are supplied to the endpoint.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SpanwiseLoadEntry(BaseModel):
    """Per-strip structural loads referenced to the wing root."""

    y_m: float = Field(
        ...,
        description=(
            "Absolute spanwise distance from the wing root to this strip's centre (m). "
            "Always >= 0 for BOTH starboard and port entries — port strips have a "
            "negative physical Yle, but the absolute value is stored here (negate for "
            "physical coordinates)."
        ),
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


class SpanwiseLoadsWithSizingResponse(SpanwiseLoadsResponse):
    """Spanwise loads response extended with per-surface spar-sizing results (gh-1008).

    Returned by the endpoint when ``spar_params`` are supplied in the request body.
    Each element in ``spar_sizing`` corresponds to one surface in ``surfaces``
    (by position and ``surface_name``).

    Import note: SparSizingResult is imported inline to avoid circular imports
    between spanwise_loads and spar_sizing schemas.
    """

    # Use Any to avoid import-time circular dependency; validated at runtime.
    spar_sizing: Optional[list] = Field(
        None,
        description=(
            "Per-surface spar-sizing results (list of SparSizingResult). "
            "Present only when spar_params were supplied."
        ),
    )
