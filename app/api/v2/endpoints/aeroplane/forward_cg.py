"""Forward CG / elevator authority endpoints — gh-500, gh-516.

Exposes POST /aeroplanes/{uuid}/forward-cg/recompute to trigger an
on-demand forward CG limit recomputation with a chosen solver.

Default solver: asb (AeroSandbox AeroBuildup — fast, automatic).
High-fidelity: avl (AVL vortex-lattice — opt-in, higher confidence for
unconventional configurations such as V-tail, elevon, flaperon layouts).

The AVL path always returns ForwardCGConfidence.avl_full.
It is opt-in only — never triggered automatically. The PO activates
it via an explicit "Recompute with AVL" UI action or direct API call.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    InternalError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.forward_cg import ForwardCGResult
from app.services.elevator_authority_service import compute_forward_cg_limit

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/forward-cg/recompute",
    status_code=status.HTTP_200_OK,
    tags=["forward-cg"],
    operation_id="recompute_forward_cg",
    response_model=ForwardCGResult,
    responses={
        200: {"description": "Forward CG limit computed successfully"},
        404: {"description": "Aeroplane not found"},
        422: {"description": "Validation error (e.g. invalid solver value)"},
        500: {"description": "Internal server error (AVL/ASB computation failure)"},
    },
)
async def recompute_forward_cg(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
    solver: Annotated[
        Literal["asb", "avl"],
        Query(
            description=(
                "Solver to use for Cm_δe computation. "
                "'asb' (default): AeroSandbox AeroBuildup — fast, automatic. "
                "'avl' (opt-in): AVL vortex-lattice — higher fidelity for V-tail, "
                "elevon, flaperon layouts. Always returns avl_full confidence."
            )
        ),
    ] = "asb",
) -> ForwardCGResult:
    """Recompute the forward CG limit for an aeroplane using the chosen solver.

    The default solver is ASB (AeroSandbox AeroBuildup). Use solver=avl to
    request the high-fidelity AVL vortex-lattice path — this is opt-in only
    and should be triggered by an explicit user action, not automatically.

    The result includes Cm_δe, CL_max_landing, and the confidence tier.
    On any computation failure, falls back to the 0.30·MAC stub.
    """
    # Look up the aeroplane model
    aeroplane = (
        db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
    )
    if aeroplane is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aeroplane {aeroplane_id} not found",
        )

    try:
        result = compute_forward_cg_limit(db, aeroplane, force_solver=solver)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        logger.error(
            "Unexpected error in forward-cg recompute for aeroplane %s (solver=%s): %s",
            aeroplane_id,
            solver,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forward CG computation failed: {exc}",
        ) from exc

    return result
