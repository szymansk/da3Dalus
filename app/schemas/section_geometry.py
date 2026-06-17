"""Pydantic request/response schemas for the section-geometry endpoint (gh-1021).

The underlying :class:`cad_designer.airplane.geometry.section_geometry.SectionPoint`
works in **millimetres** (wing-local frame). This API exposes lengths in
**metres** (project convention) — the service converts mm -> m (x0.001).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SectionGeometryRequest(BaseModel):
    """Request body for ``POST /aeroplanes/{id}/section-geometry``.

    All fields are optional. When ``y_over_span`` / ``x_over_chord`` are omitted
    the service samples an evenly spaced default grid.
    """

    y_over_span: Optional[list[float]] = Field(
        None,
        description=(
            "Spanwise sample fractions (0..1 across the semi-span). "
            "Omit for an evenly spaced default grid."
        ),
    )
    x_over_chord: Optional[list[float]] = Field(
        None,
        description=(
            "Chordwise sample fractions (0..1 along the local chord). "
            "Omit for an evenly spaced default grid."
        ),
    )
    per_segment: bool = Field(
        False,
        description=("When true, also return a per-segment grid keyed by segment index."),
    )
    wing_name: Optional[str] = Field(
        None,
        description=(
            "Name of the wing to query. When omitted, the aeroplane's first wing is used."
        ),
    )
    mode: Literal["analytic", "solid"] = Field(
        "analytic",
        description=(
            "Evaluation mode (gh-1046). 'analytic' (default) blends the segment "
            "airfoils — fast (~ms), no CAD loft built. 'solid' builds and slices "
            "the real lofted CAD solid for true built-geometry fidelity (slow, "
            "~seconds); use only when exact built geometry is required."
        ),
    )


class SectionPointOut(BaseModel):
    """A sampled point on the built wing section. Lengths in **metres**."""

    y_span: float = Field(..., description="Span fraction 0..1 across the semi-span")
    x_c: float = Field(..., description="Chord fraction 0..1 along the local chord")
    thickness: float = Field(..., description="Vertical section extent at this chord location (m)")
    top_z: float = Field(..., description="Upper surface height, wing frame (m)")
    bottom_z: float = Field(..., description="Lower surface height, wing frame (m)")
    center_z: float = Field(..., description="Section mid-height, spar-placement reference (m)")


class SectionGeometryResponse(BaseModel):
    """Response for ``POST /aeroplanes/{id}/section-geometry``."""

    surface: list[SectionPointOut] = Field(
        ...,
        description="Whole-surface grid of sampled section points (metres).",
    )
    segments: Optional[dict[int, list[SectionPointOut]]] = Field(
        None,
        description=(
            "Per-segment grids keyed by segment index. Present only when "
            "per_segment=true was requested."
        ),
    )
