"""Pydantic schemas for airfoil profiles.

Includes the frozen API contract for the low-Re suitability endpoint (gh-821, gh-825).
See docs/superpowers/specs/2026-06-04-low-re-airfoil-scoring-design.md.

## Unit and CL assumptions (documented per contract)

Reynolds number stays LOCAL (per xsec chord).  Section CL is treated as
equal to the whole-wing CL under the elliptical, untwisted ideal — this is
the standard top-down design target assumption.  The approximation breaks
down where tip-stall lives (low-Re tip chord, CL_max collapse), which is
explicitly surfaced via:
  - ``SuitabilityItem.tip_re_flag`` — True when tip Re < root Re.
  - ``SuitabilityCaveat.ignores_tip_re_clmax_collapse`` — always True.
  - ``SuitabilityItem.cl_max_margin`` — margin from target CL to section CL_max;
    negative values flag designs where the section may stall before the
    tip CL_max collapse is modelled.
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

# Frozen active-lens literals (gh-825):
#   Only THREE values are valid for active_lens:
#     - re_agnostic  : general Re-normalised quality score
#     - mission      : mission-weighted re_agnostic
#     - target_cl_cruise : efficiency at the cruise operating CL
#
#   GLIDE POINTS NEVER AUTO-RANK:
#     target_cl_best_glide and target_cl_min_sink are display-only.
#     The backend never sets active_lens to a glide point, so the default
#     sort is always driven by a design-primary operating point (cruise)
#     or mission weighting — not an engine-out / min-sink contingency point.
#     A user may re-sort the UI list by any target-CL column (client-side),
#     but that is an explicit user action and does NOT change active_lens.
ActiveLens = Literal["re_agnostic", "mission", "target_cl_cruise"]

# Provenance of the target CL values (gh-825).
# Derived from the 'mass' DesignAssumptionModel.active_source combined with
# ctx['v_cruise_auto']:
#   - all inputs CALCULATED/auto  → "calculated"
#   - all inputs ESTIMATE/manual  → "estimated"
#   - otherwise                   → "mixed"
#   - null/no mass row            → "estimated" (default)
TargetClProvenance = Literal["estimated", "calculated", "mixed"]


class SuitabilityItem(BaseModel):
    """One airfoil in the ranked suitability response.

    Field notes (gh-825 contract):
      - target_cl_cruise : score at the cruise operating CL (drives active_lens).
      - target_cl_best_glide : score at V_md (best L/D speed, display-only).
      - target_cl_min_sink : score at V_min_sink (min-sink speed, display-only).
      - stall_gentleness : raw dCL/dα slope past CL_max peak (≈0 gentle, negative abrupt).
          NOT normalised to [0, 1] — raw slope value in units of CL per degree.
      - cl_max_margin : cl_max − max(target CLs present). Negative means target CL
          exceeds section CL_max — a stall-risk flag.
    """

    airfoil_name: str
    family: AirfoilFamily
    re_agnostic: float = Field(..., ge=0.0, le=1.0)
    mission: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_cl_cruise: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_cl_best_glide: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_cl_min_sink: Optional[float] = Field(None, ge=0.0, le=1.0)
    stall_gentleness: Optional[float] = Field(
        None,
        description="dCL/dα past CL_max peak (raw, ≈0 gentle / negative abrupt). NOT 0..1.",
    )
    cl_max_margin: Optional[float] = Field(
        None,
        description="cl_max − max(target CLs present). Negative → target above section CL_max.",
    )
    min_analysis_confidence: float = Field(..., ge=0.0, le=1.0)
    tip_re_flag: bool
    caveat: str


class SuitabilityQuery(BaseModel):
    """Echo of the query parameters used to compute this response.

    target_cl_provenance documents how reliably the three target CLs were derived:
      - 'calculated' : mass and cruise speed were both auto-computed
      - 'estimated'  : at least one input was a manual estimate
      - 'mixed'      : some inputs calculated, some estimated
    """

    chord_m: float
    speed_ms: float
    reynolds: float
    re_clamped: bool
    mission_type: Optional[str] = None
    target_cl_cruise: Optional[float] = None
    target_cl_best_glide: Optional[float] = None
    target_cl_min_sink: Optional[float] = None
    target_cl_provenance: TargetClProvenance = "estimated"
    active_lens: ActiveLens


class SuitabilityCaveat(BaseModel):
    """Caveats block. Always present in every suitability response.

    ignores_tip_re_clmax_collapse is always True: the score uses section CL as
    a proxy for whole-wing CL (ideal elliptic, untwisted assumption).  This
    ignores the tip-Re CL_max collapse that governs tip-stall onset on tapered
    wings.  Use tip_re_flag + cl_max_margin to surface this risk in the UI.
    """

    relative_ranking_only: bool = True
    no_hysteresis_modelling: bool = True
    ignores_tip_re_clmax_collapse: bool = True
    recommend_xfoil_validation: bool
    text: str


class SuitabilityResponse(BaseModel):
    """Full response for GET /airfoils/db/suitability."""

    query: SuitabilityQuery
    caveat: SuitabilityCaveat
    results: list[SuitabilityItem]
