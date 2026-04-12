from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DesignVersionCreate(BaseModel):
    label: str = Field(..., min_length=1, description="Human-readable version label")
    description: Optional[str] = Field(None, description="Optional longer description")


class DesignVersionSummary(BaseModel):
    id: int
    label: str
    description: Optional[str] = None
    parent_version_id: Optional[int] = None
    created_at: datetime


class DesignVersionRead(DesignVersionSummary):
    snapshot: dict[str, Any] = Field(..., description="Full aeroplane state at snapshot time")


class DesignVersionDiff(BaseModel):
    version_a: int
    version_b: int
    changes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of structured change records",
    )
