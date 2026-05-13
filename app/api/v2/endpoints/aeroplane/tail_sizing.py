"""Tail sizing endpoint (gh-491) — GET /aeroplanes/{id}/tail-sizing."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4, BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.services.tail_sizing_service import (
    TailVolumeResult,
    build_tail_sizing_context_from_aeroplane,
    compute_tail_volumes,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class TailSizingResponse(BaseModel):
    """Tail volume coefficient sizing response (gh-491)."""

    # Volume coefficients
    v_h_current: float | None = Field(None, description="Current V_H = S_H·l_H/(S_w·MAC)")
    v_v_current: float | None = Field(None, description="Current V_V = S_V·l_V/(S_w·b)")

    # Arm lengths
    l_h_m: float | None = Field(
        None,
        description="Horizontal tail moment arm — wing-AC to tail-AC in metres (drives recommendation)",
    )
    l_h_eff_from_aft_cg_m: float | None = Field(
        None,
        description="Effective l_H from aft CG to tail-AC (display-only, for SM cross-check)",
    )

    # Recommended tail areas
    s_h_recommended_mm2: float | None = Field(
        None, description="Recommended S_H at target V_H midpoint, in mm²"
    )
    s_v_recommended_mm2: float | None = Field(
        None, description="Recommended S_V at target V_V midpoint, in mm²"
    )

    # Classification
    classification: str = Field(
        ...,
        description=(
            "Top-level classification: in_range | below_range | above_range | "
            "out_of_physical_range | not_applicable"
        ),
    )
    classification_h: str = Field(..., description="Per-surface V_H classification")
    classification_v: str = Field(..., description="Per-surface V_V classification")

    # Metadata
    aircraft_class_used: str = Field(..., description="Aircraft class used for target lookup")
    cg_aware: bool = Field(
        ...,
        description="True when neutral point was available for full CG-aware computation",
    )

    # Target ranges for UI
    v_h_target_min: float | None = Field(None, description="V_H target range lower bound")
    v_h_target_max: float | None = Field(None, description="V_H target range upper bound")
    v_v_target_min: float | None = Field(None, description="V_V target range lower bound")
    v_v_target_max: float | None = Field(None, description="V_V target range upper bound")
    v_h_citation: str = Field("", description="Source citation for V_H target range")
    v_v_citation: str = Field("", description="Source citation for V_V target range")

    warnings: list[str] = Field(default_factory=list)


def _to_response(result: TailVolumeResult) -> TailSizingResponse:
    return TailSizingResponse(
        v_h_current=result.v_h_current,
        v_v_current=result.v_v_current,
        l_h_m=result.l_h_m,
        l_h_eff_from_aft_cg_m=result.l_h_eff_from_aft_cg_m,
        s_h_recommended_mm2=result.s_h_recommended_mm2,
        s_v_recommended_mm2=result.s_v_recommended_mm2,
        classification=result.classification,
        classification_h=result.classification_h,
        classification_v=result.classification_v,
        aircraft_class_used=result.aircraft_class_used,
        cg_aware=result.cg_aware,
        v_h_target_min=result.v_h_target_range[0] if result.v_h_target_range else None,
        v_h_target_max=result.v_h_target_range[1] if result.v_h_target_range else None,
        v_v_target_min=result.v_v_target_range[0] if result.v_v_target_range else None,
        v_v_target_max=result.v_v_target_range[1] if result.v_v_target_range else None,
        v_h_citation=result.v_h_citation,
        v_v_citation=result.v_v_citation,
        warnings=result.warnings,
    )


@router.get(
    "/aeroplanes/{aeroplane_id}/tail-sizing",
    status_code=status.HTTP_200_OK,
    tags=["tail-sizing"],
    operation_id="get_tail_sizing",
    response_model=TailSizingResponse,
    responses={
        404: {"description": "Aeroplane not found"},
        200: {"description": "Tail volume coefficients computed"},
    },
    summary="Tail volume coefficient sizing",
    description=(
        "Compute V_H and V_V for the current aircraft configuration "
        "and return recommended S_H / S_V. Returns classification=not_applicable "
        "for canard, tailless, or V-tail configurations."
    ),
)
async def get_tail_sizing(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Session = Depends(get_db),
) -> TailSizingResponse:
    aircraft = (
        db.query(AeroplaneModel)
        .filter(AeroplaneModel.uuid == str(aeroplane_id))
        .first()
    )
    if aircraft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aeroplane {aeroplane_id} not found",
        )

    try:
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        if ctx is None:
            # No assumption context yet — return not_applicable
            return TailSizingResponse(
                classification="not_applicable",
                classification_h="not_applicable",
                classification_v="not_applicable",
                aircraft_class_used="rc_trainer",
                cg_aware=False,
                warnings=["Recompute assumptions first to obtain reference geometry"],
            )
        result = compute_tail_volumes(ctx)
        return _to_response(result)
    except Exception as exc:
        logger.error(
            "Tail sizing failed for aeroplane %s: %s", aeroplane_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tail sizing computation failed: {exc}",
        ) from exc
