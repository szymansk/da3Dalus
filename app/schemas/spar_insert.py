"""Pydantic schemas for the spar-plan → wing insert endpoint (gh-1049).

The insert endpoint reuses the :class:`app.schemas.spar_plan.SparPlanRequest`
inputs (material + sizing + spanwise moments) and adds a ``dry_run`` flag plus
the target wing. It computes the buildable :class:`SparPlan` (gh-1031), maps each
piece to a persisted ``Spare`` (gh-1032), resolves the target segment from the
piece's spanwise span, and assigns the **spar_index** invariant
(front → 0, rear → 1, reinforcement → next) consistently across segments.

**dry_run=true** → return the planned insertions WITHOUT writing. **dry_run=false**
→ persist each via ``wing_service.create_spare`` honouring the assigned
``sort_index``.

Units: the plan is solved in mm; this API exposes piece dimensions in **metres**
(project convention), matching :mod:`app.schemas.spar_plan`.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.spar_plan import SparPlanRequest


class SparInsertRequest(SparPlanRequest):
    """Request body for ``POST /aeroplanes/{id}/spar-plan/insert`` (gh-1049).

    Same inputs as the spar-plan request plus a ``dry_run`` flag. When
    ``dry_run`` is true the endpoint returns the planned insertions without
    writing; when false it persists each spar piece as a ``Spare``.
    """

    dry_run: bool = Field(
        True,
        description=(
            "When true (default) return the planned insertions WITHOUT writing. "
            "When false, persist each spar piece as a Spare honouring the "
            "spar_index invariant (front=0, rear=1, reinforcement=next)."
        ),
    )


class PlannedSpareOut(BaseModel):
    """One planned spar insertion. Dimensions in **metres**, wing-local frame."""

    segment_index: int = Field(
        ...,
        description=(
            "Target wing segment / cross-section index this piece is inserted "
            "into (resolved from the piece's spanwise span)."
        ),
    )
    spar_index: int = Field(
        ...,
        description=(
            "The per-segment sort_index assigned to this spare. Front (main) spar "
            "= 0 in every segment, rear = 1, reinforcement = next. The same "
            "logical spar carries the same spar_index across every segment."
        ),
    )
    role: str = Field(..., description="Structural role: 'front' (bending) or 'rear' (torsion).")
    spare_support_dimension_width: float = Field(
        ..., description="Spar bounding-box width = outer_d (m)."
    )
    spare_support_dimension_height: float = Field(
        ..., description="Spar bounding-box height = outer_d (m)."
    )
    spare_length: float = Field(..., description="Spar piece length (m).")
    outer_d: float = Field(..., description="Outer diameter (m).")
    inner_d: float = Field(..., description="Inner diameter / bore (m); not modelled in the Spare.")
    spare_origin: list[float] = Field(
        ..., description="Piece root origin (x, y, z) in the wing-local frame (m)."
    )
    spare_vector: list[float] = Field(
        ..., description="Unit direction vector the piece runs along (dimensionless)."
    )
    joint_note: Optional[str] = Field(
        None,
        description=("Joint to the next (tip-side) piece, e.g. 'telescoping'. None if last."),
    )
    feasible: bool = Field(
        ..., description="False when the section cannot contain a round tube strong enough."
    )


class SparInsertResponse(BaseModel):
    """Response for ``POST /aeroplanes/{id}/spar-plan/insert`` (gh-1049).

    Lengths in metres. ``committed`` is false for a dry-run preview, true once
    the spares have been persisted. On commit (gh-1058) an immutable snapshot is
    auto-created before the destructive REPLACE and its id is returned in
    ``snapshot_id`` so the user can one-click revert; it is None on a dry-run.
    """

    dry_run: bool = Field(..., description="Echo of the request dry_run flag.")
    committed: bool = Field(
        ...,
        description="True when the spares were persisted; false for a dry-run preview.",
    )
    wing_name: str = Field(..., description="Name of the wing the spar was inserted into.")
    planned_spares: list[PlannedSpareOut] = Field(
        ...,
        description="The planned (or persisted) spar insertions, in insertion order.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Faithful-representation warnings (telescoping overlap, bent-pin, "
            "reinforcement+joiner, dropped bore) surfaced by the mapping."
        ),
    )
    feasible: bool = Field(..., description="The plan's overall feasibility.")
    infeasibility_reason: Optional[str] = Field(
        None, description="Reason when the plan is infeasible; None otherwise."
    )
    snapshot_id: Optional[int] = Field(
        None,
        description=(
            "Integer PK of the immutable snapshot auto-created BEFORE the "
            "destructive commit (gh-1058). The commit REPLACEs existing spares in "
            "each touched segment; this snapshot captures the pre-insert state so "
            "the user can one-click revert via POST /aeroplanes/{snapshot_id}/restore. "
            "None on a dry-run preview (nothing was mutated, so nothing was snapshotted)."
        ),
    )
