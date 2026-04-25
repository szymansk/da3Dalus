"""Pydantic schemas for airfoil profiles."""
from __future__ import annotations

from typing import Optional

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
    created_at: str

    model_config = {"from_attributes": True}


class AirfoilImportResult(BaseModel):
    """Summary of a directory import operation."""

    imported: int = Field(0, description="Number of new airfoils imported")
    skipped: int = Field(0, description="Already existed (case-insensitive)")
    errors: int = Field(0, description="Files that could not be parsed")
    error_files: list[str] = Field(default_factory=list, description="Filenames that failed")
