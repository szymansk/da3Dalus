from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


COMPONENT_TYPES = Literal[
    "servo",
    "brushless_motor",
    "esc",
    "battery",
    "receiver",
    "flight_controller",
    "material",
    "propeller",
    "generic",
]

COMPONENT_TYPE_LIST: list[str] = [
    "servo",
    "brushless_motor",
    "esc",
    "battery",
    "receiver",
    "flight_controller",
    "material",
    "propeller",
    "generic",
]


class ComponentWrite(BaseModel):
    name: str = Field(..., min_length=1, description="Component name / model number")
    component_type: COMPONENT_TYPES = Field(..., description="Hardware category")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    description: Optional[str] = Field(None, description="Free-text description")
    mass_g: Optional[float] = Field(None, ge=0, description="Mass in grams")
    bbox_x_mm: Optional[float] = Field(None, ge=0, description="Bounding box X dimension in mm")
    bbox_y_mm: Optional[float] = Field(None, ge=0, description="Bounding box Y dimension in mm")
    bbox_z_mm: Optional[float] = Field(None, ge=0, description="Bounding box Z dimension in mm")
    model_ref: Optional[str] = Field(None, description="Reference to STEP/STL 3D model file")
    specs: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific specifications (e.g. kv, capacity_mah, voltage_range, density_kg_m3)",
    )


class ComponentRead(ComponentWrite):
    id: int = Field(..., description="Component ID")
    created_at: datetime
    updated_at: datetime


class ComponentList(BaseModel):
    items: list[ComponentRead] = Field(default_factory=list)
    total: int = Field(0, description="Total number of matching components")


class ComponentTypesResponse(BaseModel):
    types: list[str] = Field(..., description="List of all available component types")
