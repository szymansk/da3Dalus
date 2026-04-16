"""Pydantic schemas for the component tree."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


NODE_TYPES = Literal["group", "cad_shape", "cots"]


class ComponentTreeNodeWrite(BaseModel):
    parent_id: Optional[int] = Field(None, description="Parent node ID, null for root")
    sort_index: int = Field(0, description="Sort order among siblings")
    node_type: NODE_TYPES = Field(..., description="Node type: group, cad_shape, or cots")
    name: str = Field(..., min_length=1, description="Display name")

    # cad_shape fields
    shape_key: Optional[str] = Field(None, description="Key from create_shape() dict")
    shape_hash: Optional[str] = Field(None, description="Hash of the Workplane object")
    volume_mm3: Optional[float] = Field(None, ge=0, description="Volume in mm³")
    area_mm2: Optional[float] = Field(None, ge=0, description="Surface area in mm²")

    # cots fields
    component_id: Optional[int] = Field(None, description="Reference to components table")
    quantity: int = Field(1, ge=1, description="Quantity of this component")

    # cad_shape — manually uploaded source. When set on create, the service
    # snapshots volume_mm3 / area_mm2 / material_id from the referenced part
    # (unless those fields are also explicitly provided in the request).
    construction_part_id: Optional[int] = Field(
        None,
        description="Reference to construction_parts table (gh#57). Mutually "
                    "compatible with shape_key (Creator pipeline source).",
    )

    # Position / Orientation
    pos_x: float = Field(0, description="X position in mm")
    pos_y: float = Field(0, description="Y position in mm")
    pos_z: float = Field(0, description="Z position in mm")
    rot_x: float = Field(0, description="Rotation around X in degrees")
    rot_y: float = Field(0, description="Rotation around Y in degrees")
    rot_z: float = Field(0, description="Rotation around Z in degrees")

    # Weight
    material_id: Optional[int] = Field(None, description="Material component ID (for print weight calc)")
    weight_override_g: Optional[float] = Field(None, ge=0, description="Manual weight override in grams")
    print_type: Optional[str] = Field(None, description="'volume' or 'surface' for 3D print weight calc")
    scale_factor: float = Field(1.0, gt=0, description="Weight scaling factor (empirical)")


class ComponentTreeNodeRead(ComponentTreeNodeWrite):
    id: int
    aeroplane_id: str
    synced_from: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ComponentTreeNodeWithChildren(ComponentTreeNodeRead):
    """Node with nested children for tree response."""
    children: list[ComponentTreeNodeWithChildren] = Field(default_factory=list)


class ComponentTreeResponse(BaseModel):
    """Full component tree for an aeroplane."""
    aeroplane_id: str
    root_nodes: list[ComponentTreeNodeWithChildren] = Field(default_factory=list)
    total_nodes: int = 0


class MoveNodeRequest(BaseModel):
    new_parent_id: Optional[int] = Field(None, description="New parent node ID, null for root")
    sort_index: int = Field(0, description="New sort index")


class WeightResponse(BaseModel):
    node_id: int
    name: str
    own_weight_g: Optional[float] = Field(None, description="This node's weight in grams")
    children_weight_g: float = Field(0, description="Sum of children weights")
    total_weight_g: float = Field(0, description="own + children")
    source: str = Field("none", description="Weight source: calculated, override, cots, or none")
