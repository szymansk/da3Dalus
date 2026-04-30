"""Pydantic schemas for the AVL geometry file (Expert Mode — gh-381)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AvlGeometryResponse(BaseModel):
    content: str = Field(..., description="The .avl geometry file content")
    is_dirty: bool = Field(..., description="True if airplane geometry changed since last edit")
    is_user_edited: bool = Field(..., description="True if the user has manually edited this file")


class AvlGeometryUpdateRequest(BaseModel):
    content: str = Field(..., description="The edited .avl geometry file content", min_length=1)
