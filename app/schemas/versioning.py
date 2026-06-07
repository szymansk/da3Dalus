"""Pydantic schemas for the aircraft versioning system (gh-905).

Covers: VersionNode, BranchOut, TreeOut, CompareOut.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SnapshotRequest(BaseModel):
    """Body for POST /aeroplanes/{id}/snapshot."""

    label: str = Field(..., min_length=1, description="Human-readable label for the snapshot")
    note: Optional[str] = Field(None, description="Why this snapshot was taken")
    provenance_message_id: Optional[int] = Field(
        None,
        description="ID of the last copilot_messages row at snapshot time (AI provenance cursor)",
    )

    model_config = ConfigDict(extra="forbid")


class BranchRequest(BaseModel):
    """Body for POST /aeroplanes/{id}/branch."""

    name: str = Field(..., min_length=1, description="Branch name (e.g. 'ai/winglet-experiment')")
    created_by: Optional[str] = Field(
        "human", description="Who created the branch: 'human' or 'ai'"
    )

    model_config = ConfigDict(extra="forbid")


class VersionNode(BaseModel):
    """A single node in the version lineage graph.

    Returned by snapshot, restore, and list_tree.
    """

    id: int
    uuid: str
    name: str
    branch_id: Optional[int] = None
    predecessor_id: Optional[int] = None
    root_id: Optional[int] = None
    is_immutable: bool
    version_label: Optional[str] = None
    version_note: Optional[str] = None
    created_by: Optional[str] = None
    provenance_message_id: Optional[int] = None
    # preview_png is base64 — omit from tree listing for bandwidth; present on detail
    preview_png: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BranchOut(BaseModel):
    """Branch metadata returned by create_branch and adopt_branch."""

    id: int
    root_id: int
    head_id: int
    name: str
    is_main: bool
    created_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TreeNodeOut(BaseModel):
    """One node in the lineage tree (compact — no preview_png)."""

    id: int
    uuid: str
    name: str
    branch_id: Optional[int] = None
    predecessor_id: Optional[int] = None
    root_id: Optional[int] = None
    is_immutable: bool
    is_head: bool = Field(description="True if this node is the head of any branch")
    version_label: Optional[str] = None
    version_note: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TreeOut(BaseModel):
    """Version lineage graph for a root aeroplane."""

    root_id: int
    nodes: list[TreeNodeOut]
    branches: list[BranchOut]


class CompareOut(BaseModel):
    """Side-by-side metrics payload for two aeroplane nodes."""

    node_a: VersionNode
    node_b: VersionNode
    metrics_a: Optional[dict[str, Any]] = Field(
        None, description="assumption_computation_context + key geometry/stability for node A"
    )
    metrics_b: Optional[dict[str, Any]] = Field(
        None, description="assumption_computation_context + key geometry/stability for node B"
    )
