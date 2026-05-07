from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


WEIGHT_CATEGORIES = Literal["electronics", "battery", "structural", "payload", "other"]


class WeightItemWrite(BaseModel):
    name: str = Field(..., min_length=1, description="Component name")
    mass_kg: float = Field(..., ge=0, description="Mass in kg")
    x_m: float = Field(0.0, description="X position in aeroplane coords [m]")
    y_m: float = Field(0.0, description="Y position in aeroplane coords [m]")
    z_m: float = Field(0.0, description="Z position in aeroplane coords [m]")
    description: Optional[str] = Field(None, description="Free-text description")
    category: WEIGHT_CATEGORIES = Field("other", description="Component category")


class WeightItemRead(WeightItemWrite):
    id: int = Field(..., description="Item ID")


class WeightSummary(BaseModel):
    items: list[WeightItemRead] = Field(default_factory=list)
    total_mass_kg: float = Field(0.0, description="Sum of all item masses")
    cg_x_m: float | None = Field(None, description="Mass-weighted CG X [m]")
    cg_y_m: float | None = Field(None, description="Mass-weighted CG Y [m]")
    cg_z_m: float | None = Field(None, description="Mass-weighted CG Z [m]")
