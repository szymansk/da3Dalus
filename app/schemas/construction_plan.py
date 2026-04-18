"""Pydantic schemas for Construction Plans (gh#101)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    """Request body for creating / updating a construction plan."""

    name: str = Field(..., min_length=1, description="Plan display name")
    description: Optional[str] = Field(None, description="Optional description")
    tree_json: dict = Field(
        ...,
        description="Serialised ConstructionRootNode tree (GeneralJSONEncoder format)",
    )


class PlanRead(PlanCreate):
    """Full plan including DB metadata."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanSummary(BaseModel):
    """Lightweight plan entry for list views."""

    id: int
    name: str
    description: Optional[str] = None
    step_count: int = Field(0, description="Number of steps in the tree")
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Creator reflection schemas ──────────────────────────────────


class CreatorParam(BaseModel):
    """A single constructor parameter of a Creator class."""

    name: str
    type: str = Field(description="Python type annotation as string")
    default: Optional[Any] = None
    required: bool
    description: Optional[str] = Field(None, description="Human-readable parameter description")


class CreatorOutput(BaseModel):
    """A single output shape key produced by a Creator."""

    key: str = Field(description="Shape key pattern, e.g. '{id}' or '{id}.cape'")
    description: str


class CreatorInfo(BaseModel):
    """Metadata for one AbstractShapeCreator subclass."""

    class_name: str
    category: str = Field(description="Module category: wing, fuselage, cad_operations, export_import, components")
    description: Optional[str] = None
    parameters: list[CreatorParam]
    outputs: list[CreatorOutput] = Field(default_factory=list, description="Shape keys this creator produces")


# ── Execute schemas ─────────────────────────────────────────────


class ExecuteRequest(BaseModel):
    """Request body for executing a plan against an aeroplane."""

    aeroplane_id: str = Field(..., description="UUID of the aeroplane to use")


class ExecutionResult(BaseModel):
    """Response from plan execution."""

    status: str = Field(description="'success' or 'error'")
    shape_keys: list[str] = Field(default_factory=list)
    export_paths: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    duration_ms: int = 0
