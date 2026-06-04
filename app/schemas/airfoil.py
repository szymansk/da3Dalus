"""Pydantic schemas for airfoil profiles.

Includes the frozen API contract for the low-Re suitability endpoint (gh-821).
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
# Low-Re suitability scoring — frozen API contract (gh-821)
# ---------------------------------------------------------------------------

# Frozen family literals — must match the classifier labels exactly.
AirfoilFamily = Literal["flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"]

# Frozen active-lens literals — 'target_cl_loiter' is explicitly excluded (loiter
# is display-only; see spec §FROZEN API CONTRACT).
ActiveLens = Literal["re_agnostic", "mission", "target_cl_cruise"]


class SuitabilityItem(BaseModel):
    """One airfoil in the ranked suitability response."""

    airfoil_name: str
    family: AirfoilFamily
    re_agnostic: float = Field(..., ge=0.0, le=1.0)
    mission: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_cl_cruise: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_cl_loiter: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_analysis_confidence: float = Field(..., ge=0.0, le=1.0)
    tip_re_flag: bool
    caveat: str


class SuitabilityQuery(BaseModel):
    """Echo of the query parameters used to compute this response."""

    chord_m: float
    speed_ms: float
    reynolds: float
    re_clamped: bool
    mission_type: Optional[str]
    target_cl_cruise: Optional[float]
    target_cl_loiter: Optional[float]
    active_lens: ActiveLens


class SuitabilityCaveat(BaseModel):
    """Caveats block. Always present in every suitability response."""

    relative_ranking_only: bool = True
    no_hysteresis_modelling: bool = True
    recommend_xfoil_validation: bool
    text: str


class SuitabilityResponse(BaseModel):
    """Full response for GET /airfoils/db/suitability."""

    query: SuitabilityQuery
    caveat: SuitabilityCaveat
    results: list[SuitabilityItem]
