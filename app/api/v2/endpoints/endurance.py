"""REST endpoint for electric endurance / range — gh-490.

GET /aeroplanes/{aeroplane_id}/endurance
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas.endurance import EnduranceResponse
from app.services.endurance_service import compute_endurance_for_aeroplane

router = APIRouter()
logger = logging.getLogger(__name__)

_DESC_AEROPLANE_ID = "UUID of the aeroplane"


@router.get(
    "/aeroplanes/{aeroplane_id}/endurance",
    response_model=EnduranceResponse,
    tags=["endurance"],
    operation_id="get_electric_endurance",
    summary="Compute electric endurance and range for an aeroplane",
    description=(
        "Computes maximum endurance (at V_min_sink) and maximum range (at V_md) "
        "for an electrically-powered aeroplane using a Class-I energy-balance model "
        "(Anderson §6.4–6.5, Hepperle 2012). "
        "Reads battery capacity, propulsion efficiencies, and polar parameters from "
        "the aeroplane's assumption_computation_context. "
        "Assumptions: constant η, constant m_TO, pack-level E* = 180 Wh/kg, "
        "Peukert effect neglected."
    ),
)
def get_electric_endurance(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> EnduranceResponse:
    """Compute electric endurance and range KPIs for an aeroplane."""
    try:
        result = compute_endurance_for_aeroplane(db=db, aeroplane_uuid=aeroplane_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Endurance compute failed for aeroplane %s", aeroplane_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Endurance computation failed: {exc}",
        ) from exc

    return EnduranceResponse(**result)
