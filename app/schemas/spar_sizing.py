"""Pydantic schemas for spar-sizing from spanwise loads (gh-1008)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

SparShape = Literal["tube", "rod", "rectangular", "capped"]


class SparSizingParams(BaseModel):
    """Parameters that drive the spar-sizing computation."""

    material_id: int = Field(
        ...,
        description=(
            "ID of a Component with component_type='material' and allowable_bending_stress_mpa set."
        ),
    )
    shape: SparShape = Field(
        ...,
        description="Cross-section shape: tube | rod | rectangular | capped",
    )
    sigma_allow_mpa_override: Optional[float] = Field(
        None,
        gt=0,
        description=(
            "Override allowable bending stress (MPa). When None, the material's "
            "allowable_bending_stress_mpa is used."
        ),
    )
    safety_factor_j: float = Field(
        1.5,
        gt=0,
        description="Safety factor applied to M_design = |M(y)| · g_limit · j.",
    )
    packing_factor: float = Field(
        0.8,
        gt=0,
        le=1.0,
        description=(
            "Fraction of the local airfoil thickness that the spar outer dimension "
            "may occupy. Default 0.8."
        ),
    )
    cap_width_mm: Optional[float] = Field(
        None,
        gt=0,
        description=("Flange/cap width b (mm) — required for shape='capped', ignored otherwise."),
    )


class SparSizingStation(BaseModel):
    """Spar-sizing result at one spanwise station."""

    y_m: float = Field(..., description="Spanwise position from root (m)")
    chord_m: float = Field(..., description="Local chord (m)")
    profile_thickness_mm: float = Field(
        ..., description="Local airfoil thickness = chord · (t/c) (mm)"
    )
    outer_mm: float = Field(
        ...,
        description="Spar outer dimension = profile_thickness · packing (mm)",
    )
    tc_ratio: float = Field(..., description="Thickness-to-chord ratio used at this station")
    tc_fallback: bool = Field(
        False,
        description="True when t/c fell back to the 0.12 default (no airfoil data).",
    )
    center_z_mm: Optional[float] = Field(
        None,
        description=(
            "Section mid-height (wing-local frame, mm) from the built CAD section "
            "— spar-placement reference. None when section geometry is unavailable."
        ),
    )
    m_design_Nm: float = Field(..., description="Design bending moment M_design = |M|·n·j (N·m)")
    required_W_mm3: float = Field(
        ..., description="Required section modulus erf_W = M_design / σ_allow (mm³)"
    )

    # Shape-specific solved dimension
    solved_mm: Optional[float] = Field(
        None,
        description=(
            "The solved free dimension (mm): wall thickness for Tube; d for Rod; "
            "width b for Rectangular; gurt thickness for Capped. None if infeasible."
        ),
    )
    feasible: bool = Field(
        ...,
        description=(
            "True when the solved dimension satisfies the geometric constraints "
            "(e.g., tube wall > 0, rod fits within profile, capped gurt > 0)."
        ),
    )
    infeasibility_reason: Optional[str] = Field(
        None,
        description="Human-readable reason when feasible=False.",
    )
    cross_section_area_mm2: Optional[float] = Field(
        None,
        description="Cross-section area of the spar at this station (mm²), for mass integration.",
    )


class SparSizingResult(BaseModel):
    """Full spar-sizing result for one surface (gh-1008)."""

    surface_name: str = Field(..., description="Name of the aerodynamic surface sized")
    shape: SparShape = Field(..., description="Cross-section shape used")
    material_name: str = Field(..., description="Material component name")
    sigma_allow_mpa: float = Field(..., description="Allowable bending stress used (MPa)")
    density_kg_m3: float = Field(..., description="Material density used (kg/m³)")
    g_limit: float = Field(..., description="Limit load factor from design assumptions (g)")
    g_limit_fallback: bool = Field(
        False,
        description="True when g_limit fell back to the default 3.0 (no assumption row).",
    )
    safety_factor_j: float = Field(..., description="Safety factor j applied")
    packing_factor: float = Field(..., description="Packing factor applied")

    stations: list[SparSizingStation] = Field(
        ...,
        description=(
            "Per-station sizing results, ordered from tip to root "
            "(index 0 = tip, last index = innermost strip)."
        ),
    )
    root_station: SparSizingStation = Field(
        ..., description="Sizing at the root station (worst case for a typical wing)."
    )

    # Mass estimates (half-span and full)
    spar_mass_half_kg: float = Field(
        ...,
        description="Estimated spar mass for one half-span (kg), trapezoidal integration.",
    )
    spar_mass_full_kg: float = Field(
        ..., description="Estimated full-span spar mass = 2 · half (kg)."
    )

    tc_fallback_warning: Optional[str] = Field(
        None,
        description=(
            "Present when one or more stations used the t/c = 0.12 fallback. "
            "Lists station y-positions where fallback was applied."
        ),
    )
