"""Pydantic schemas for the construction-parts domain (gh#57-g4h)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConstructionPartRead(BaseModel):
    """Read view of a construction part.

    Write/create schemas will follow in gh#57-9uk (file upload + CRUD).
    The MVP exposes only read + lock/unlock, which do not need a Write schema.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Construction-Part ID")
    aeroplane_id: str = Field(..., description="Owning aeroplane ID")
    name: str = Field(..., description="Display name")

    volume_mm3: Optional[float] = Field(None, ge=0, description="Volume in mm³")
    area_mm2: Optional[float] = Field(None, ge=0, description="Surface area in mm²")
    bbox_x_mm: Optional[float] = Field(None, ge=0, description="Bounding box X dimension in mm")
    bbox_y_mm: Optional[float] = Field(None, ge=0, description="Bounding box Y dimension in mm")
    bbox_z_mm: Optional[float] = Field(None, ge=0, description="Bounding box Z dimension in mm")

    material_component_id: Optional[int] = Field(
        None,
        description="FK to components table; expected to point at a component_type='material' entry",
    )

    locked: bool = Field(
        False,
        description="True if the DB entry is protected from overwrites by a regeneration pipeline",
    )

    thumbnail_url: Optional[str] = Field(None, description="Optional preview image URL")

    file_path: Optional[str] = Field(
        None, description="Local storage path of the uploaded CAD file"
    )
    file_format: Optional[str] = Field(
        None, description="Source file format: 'step' or 'stl'"
    )

    created_at: datetime
    updated_at: datetime


class ConstructionPartUpdate(BaseModel):
    """Metadata-only update payload (PUT). File and geometry are untouched."""

    name: Optional[str] = Field(None, min_length=1)
    material_component_id: Optional[int] = Field(None)
    thumbnail_url: Optional[str] = Field(None)


class ConstructionPartList(BaseModel):
    """Listing response for a specific aeroplane."""

    aeroplane_id: str = Field(..., description="Aeroplane scope of the listing")
    items: list[ConstructionPartRead] = Field(default_factory=list)
    total: int = Field(0, description="Total number of parts returned")
