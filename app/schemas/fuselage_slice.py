"""Pydantic schemas for the fuselage STEP slicing endpoint."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.aeroplaneschema import FuselageSchema


class GeometryProperties(BaseModel):
    volume_m3: float = Field(..., description="Volume in cubic meters")
    surface_area_m2: float = Field(..., description="Surface area in square meters")


class FidelityMetrics(BaseModel):
    volume_ratio: float = Field(..., description="Reconstructed/original volume ratio (1.0 = perfect)")
    area_ratio: float = Field(..., description="Reconstructed/original area ratio (1.0 = perfect)")


class FuselageSliceResponse(BaseModel):
    fuselage: FuselageSchema = Field(..., description="Sliced fuselage in FuselageSchema format")
    original_properties: GeometryProperties = Field(..., description="Original STEP geometry properties")
    reconstructed_properties: GeometryProperties = Field(..., description="Reconstructed superellipse geometry properties")
    fidelity: FidelityMetrics = Field(..., description="Fidelity comparison metrics")
    original_tessellation_url: Optional[str] = Field(None, description="URL to original geometry STL")
    reconstructed_tessellation_url: Optional[str] = Field(None, description="URL to reconstructed geometry STL")
