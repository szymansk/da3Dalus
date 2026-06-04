"""Pydantic schemas for airfoil profiles.

Includes the frozen API contract for the low-Re suitability endpoint (gh-821/gh-825).
See docs/superpowers/specs/2026-06-04-low-re-airfoil-scoring-design.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AirfoilSummary(BaseModel):
    """Lightweight airfoil entry for list views."""

    id: int
    name: str

    model_config = {"from_attributes": True}


class AirfoilRead(BaseModel):
    """Full airfoil with coordinates."""

    id: int
    name: str
    coordinates: list[list[float]] = Field(
        description="List of [x, y] coordinate pairs",
    )
    source_file: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AirfoilImportResult(BaseModel):
    """Summary of a directory import operation."""

    imported: int = Field(0, description="Number of new airfoils imported")
    skipped: int = Field(0, description="Already existed (case-insensitive)")
    errors: int = Field(0, description="Files that could not be parsed")
    error_files: list[str] = Field(default_factory=list, description="Filenames that failed")
    # Names of newly imported airfoils (used to schedule low-Re recompute)
    imported_names: list[str] = Field(
        default_factory=list, description="Names of newly imported airfoils", exclude=True
    )


# ---------------------------------------------------------------------------
# Low-Re suitability scoring — frozen API contract (gh-821, updated gh-825)
# ---------------------------------------------------------------------------

# Frozen family literals — must match the classifier labels exactly.
AirfoilFamily = Literal["flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"]

# Frozen active-lens literals — glide-point lenses are display-only and never
# used for ranking (see spec §FROZEN API CONTRACT).
ActiveLens = Literal["re_agnostic", "mission", "target_cl_cruise"]

# Provenance of target CL values resolved from aeroplane context.
TargetClProvenance = Literal["estimated", "calculated", "mixed"]


class SuitabilityItem(BaseModel):
    """One airfoil in the ranked suitability response (gh-825 schema)."""

    airfoil_name: str
    family: AirfoilFamily
    re_agnostic: float = Field(..., ge=0.0, le=1.0)
    mission: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_cl_cruise: Optional[float] = Field(None, ge=0.0, le=1.0)
    # gh-825: renamed from target_cl_loiter → target_cl_min_sink
    target_cl_min_sink: Optional[float] = Field(None, ge=0.0, le=1.0)
    # gh-825: new field — target CL at best-glide (engine-off / glide)
    target_cl_best_glide: Optional[float] = Field(None, ge=0.0, le=1.0)
    # gh-825: raw dCL/dα past peak (≈0 gentle, negative = abrupt stall)
    stall_gentleness: Optional[float] = None
    # gh-825: signed CL margin = cl_max − max(target CLs); negative means target > section CL_max
    cl_max_margin: Optional[float] = None
    min_analysis_confidence: float = Field(..., ge=0.0, le=1.0)
    tip_re_flag: bool
    caveat: str


class SuitabilityQuery(BaseModel):
    """Echo of the query parameters used to compute this response (gh-825 schema)."""

    chord_m: float
    speed_ms: float
    reynolds: float
    re_clamped: bool
    mission_type: Optional[str]
    target_cl_cruise: Optional[float]
    # gh-825: renamed from target_cl_loiter
    target_cl_min_sink: Optional[float]
    # gh-825: new — best-glide target CL
    target_cl_best_glide: Optional[float] = None
    # gh-825: provenance of the resolved target CL values
    target_cl_provenance: Optional[TargetClProvenance] = None
    active_lens: ActiveLens


class SuitabilityCaveat(BaseModel):
    """Caveats block. Always present in every suitability response (gh-825 schema)."""

    relative_ranking_only: bool = True
    no_hysteresis_modelling: bool = True
    # gh-825: always True — section CL == wing CL (elliptical/untwisted assumption)
    ignores_tip_re_clmax_collapse: bool = True
    recommend_xfoil_validation: bool
    text: str


class SuitabilityResponse(BaseModel):
    """Full response for GET /airfoils/db/suitability."""

    query: SuitabilityQuery
    caveat: SuitabilityCaveat
    results: list[SuitabilityItem]
