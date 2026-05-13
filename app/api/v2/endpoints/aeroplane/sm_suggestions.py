"""SM sizing suggestion endpoint — gh-494.

GET  /aeroplanes/{uuid}/sm-suggestion         — suggest wing_shift / htail_scale
POST /aeroplanes/{uuid}/sm-suggestions/apply  — apply (or dry-run) a suggestion
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.sm_sizing import (
    SmApplyRequest,
    SmApplyResponse,
    SmOption,
    SmSuggestionResponse,
)
from app.services import sm_sizing_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_aeroplane(db: Session, aeroplane_id: UUID4) -> AeroplaneModel:
    """Resolve aeroplane by UUID or raise HTTP 404."""
    plane = (
        db.query(AeroplaneModel)
        .filter(AeroplaneModel.uuid == str(aeroplane_id))
        .first()
    )
    if plane is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aeroplane {aeroplane_id} not found",
        )
    return plane


@router.get(
    "/aeroplanes/{aeroplane_id}/sm-suggestion",
    status_code=status.HTTP_200_OK,
    tags=["sm-sizing"],
    operation_id="get_sm_suggestion",
    response_model=SmSuggestionResponse,
    summary="Static margin sizing suggestion (Step 9 ↔ Step 11)",
    description=(
        "Analyse the current static margin at aft CG versus the target_static_margin "
        "assumption.  Returns up to two banner options: move the main wing fore/aft "
        "(wing_shift) OR chord-scale the horizontal tail (htail_scale). "
        "Silent when SM is already in target range [target_sm, 0.20]. "
        "Returns not_applicable for canard, tailless, or no-analysis-yet configurations."
    ),
    responses={
        404: {"description": "Aeroplane not found"},
        200: {"description": "SM suggestion computed (status=ok|suggestion|error|not_applicable)"},
    },
)
async def get_sm_suggestion(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Session = Depends(get_db),
) -> SmSuggestionResponse:
    """Compute SM sizing suggestions for an aeroplane."""
    plane = _get_aeroplane(db, aeroplane_id)
    ctx = plane.assumption_computation_context or {}
    target_sm = ctx.get("target_static_margin", 0.10)

    try:
        raw = sm_sizing_service.suggest_corrections(ctx, target_sm=target_sm, at_cg="aft")
    except Exception as exc:
        logger.error(
            "SM suggestion failed for %s: %s", aeroplane_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SM suggestion computation failed: {exc}",
        ) from exc

    options = [SmOption(**o) for o in raw.get("options", [])]
    return SmSuggestionResponse(
        status=raw["status"],
        options=options,
        block_save=raw.get("block_save", False),
        mass_coupling_warning=raw.get("mass_coupling_warning"),
        message=raw.get("message"),
        hint=raw.get("hint"),
        warnings=raw.get("warnings", []),
    )


@router.post(
    "/aeroplanes/{aeroplane_id}/sm-suggestions/apply",
    status_code=status.HTTP_200_OK,
    tags=["sm-sizing"],
    operation_id="apply_sm_suggestion",
    response_model=SmApplyResponse,
    summary="Apply (or dry-run preview) an SM sizing suggestion",
    description=(
        "Apply a wing_shift or htail_scale suggestion to the aeroplane geometry. "
        "When dry_run=True, returns predicted_sm without touching the database. "
        "When dry_run=False, updates geometry and schedules a background recompute. "
        "Not applicable for canard / tailless configurations."
    ),
    responses={
        404: {"description": "Aeroplane not found"},
        400: {"description": "Configuration not applicable (canard, tailless, no NP)"},
        422: {"description": "Invalid lever or delta_value"},
    },
)
async def apply_sm_suggestion(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    body: Annotated[SmApplyRequest, Body(...)],
    db: Session = Depends(get_db),
) -> SmApplyResponse:
    """Apply an SM sizing suggestion to an aeroplane."""
    # Verify aeroplane exists (raises 404 if not)
    _get_aeroplane(db, aeroplane_id)

    aeroplane_uuid_str = str(aeroplane_id)

    try:
        if body.lever == "wing_shift":
            result = sm_sizing_service.apply_wing_shift(
                db,
                aeroplane_uuid_str,
                delta_m=body.delta_value,
                dry_run=body.dry_run,
            )
        elif body.lever == "htail_scale":
            result = sm_sizing_service.apply_htail_scale(
                db,
                aeroplane_uuid_str,
                delta_pct=body.delta_value,
                dry_run=body.dry_run,
            )
        else:
            # Should not reach here due to Pydantic Literal validation, but be defensive
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown lever '{body.lever}'. Must be 'wing_shift' or 'htail_scale'.",
            )
    except ValueError as exc:
        msg = str(exc)
        if "not_applicable" in msg or "not found" not in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "SM suggestion apply failed for %s: %s", aeroplane_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SM suggestion apply failed: {exc}",
        ) from exc

    warnings: list[str] = []
    if not body.dry_run and body.lever == "wing_shift":
        warnings.append(sm_sizing_service._MASS_COUPLING_WARNING)
    if not body.dry_run and body.lever == "htail_scale" and body.delta_value < 0:
        warnings.append(sm_sizing_service._NEGATIVE_SH_WARNING)

    return SmApplyResponse(
        lever=result["lever"],
        delta_value=result["delta_value"],
        predicted_sm=result["predicted_sm"],
        dry_run=result["dry_run"],
        warnings=warnings,
    )
