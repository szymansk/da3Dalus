"""Pydantic schemas for the Mission compliance spider chart (gh-546)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AxisName = Literal[
    "stall_safety", "glide", "climb", "cruise",
    "maneuver", "wing_loading", "field_friendliness",
]
"""The seven mission-compliance axes."""

Provenance = Literal["computed", "estimated", "missing"]
"""Where a KPI value came from. ``missing`` -> renders as a polygon gap."""


class MissionAxisKpi(BaseModel):
    """One axis on the spider chart."""

    axis: AxisName
    value: float | None = Field(..., description="Raw physical value, None when missing")
    unit: str | None = Field(..., description="SI unit; UI converts via global preset")
    score_0_1: float | None = Field(..., description="Normalised to current mission range")
    range_min: float = Field(..., description="Lower bound used for normalisation")
    range_max: float = Field(..., description="Upper bound used for normalisation")
    provenance: Provenance
    formula: str = Field(..., description="Human-readable formula for the side-drawer")
    warning: str | None = None


class MissionTargetPolygon(BaseModel):
    """The Soll-polygon for one mission preset."""

    mission_id: str = Field(..., description="Mission preset id (e.g. 'trainer')")
    label: str
    scores_0_1: dict[AxisName, float]


class MissionKpiSet(BaseModel):
    """Full KPI payload returned from /mission-kpis."""

    aeroplane_uuid: str
    ist_polygon: dict[AxisName, MissionAxisKpi]
    target_polygons: list[MissionTargetPolygon]
    active_mission_id: str
    computed_at: str
    context_hash: str = Field(..., min_length=64, max_length=64)
