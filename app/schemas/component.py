from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ComponentWrite(BaseModel):
    name: str = Field(..., min_length=1, description="Component name / model number")
    # gh#83: component_type is now a free string; validation happens at the
    # service layer against the dynamic `component_types` registry.
    component_type: str = Field(..., min_length=1, description="Type name (see GET /component-types)")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    description: Optional[str] = Field(None, description="Free-text description")
    mass_g: Optional[float] = Field(None, ge=0, description="Mass in grams")
    bbox_x_mm: Optional[float] = Field(None, ge=0, description="Bounding box X dimension in mm")
    bbox_y_mm: Optional[float] = Field(None, ge=0, description="Bounding box Y dimension in mm")
    bbox_z_mm: Optional[float] = Field(None, ge=0, description="Bounding box Z dimension in mm")
    model_ref: Optional[str] = Field(None, description="Reference to STEP/STL 3D model file")
    specs: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific specifications — validated against the type's schema.",
    )


class ComponentRead(ComponentWrite):
    id: int = Field(..., description="Component ID")
    created_at: datetime
    updated_at: datetime


class ComponentList(BaseModel):
    items: list[ComponentRead] = Field(default_factory=list)
    total: int = Field(0, description="Total number of matching components")


class ComponentTypesResponse(BaseModel):
    types: list[str] = Field(..., description="List of all available component type names")
