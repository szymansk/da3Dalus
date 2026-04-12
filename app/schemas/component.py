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
]


class ComponentWrite(BaseModel):
    name: str = Field(..., min_length=1, description="Component name / model number")
    component_type: COMPONENT_TYPES = Field(..., description="Hardware category")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    description: Optional[str] = Field(None, description="Free-text description")
    mass_g: Optional[float] = Field(None, ge=0, description="Mass in grams")
    specs: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific specifications (e.g. kv, capacity_mah, voltage_range)",
    )


class ComponentRead(ComponentWrite):
    id: int = Field(..., description="Component ID")
    created_at: datetime
    updated_at: datetime


class ComponentList(BaseModel):
    items: list[ComponentRead] = Field(default_factory=list)
    total: int = Field(0, description="Total number of matching components")
