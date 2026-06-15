"""Powertrain Sizing Modal endpoint (gh-197).

GET /aeroplanes/{aeroplane_id}/powertrain/sizing-modal-params

Returns the pre-filled defaults for the frontend Powertrain Sizing Modal:
  - aero parameters (cd0, s_ref_m2) from the gh-924 computation context
  - motor catalog (brushless_motor components with efficiency_pct)
  - warnings when values are defaulted
"""

from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ServiceException, ValidationError
from app.db.session import get_db
from app.schemas.powertrain_sizing_modal import PowertrainModalParamsResponse
from app.services import powertrain_sizing_modal_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/powertrain/sizing-modal-params",
    status_code=status.HTTP_200_OK,
    tags=["powertrain"],
    operation_id="get_powertrain_sizing_modal_params",
    summary=(
        "Return pre-filled defaults for the Powertrain Sizing Modal "
        "(cd0, s_ref_m2, motors with efficiency, warnings)"
    ),
    responses={
        404: {"description": "Aeroplane not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_powertrain_sizing_modal_params(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> PowertrainModalParamsResponse:
    """Return pre-filled defaults for the Powertrain Sizing Modal.

    The frontend uses this response to pre-populate the modal dialog fields:
    - altitude_m: defaults to 0.0 (sea level) — editable
    - cd0: from assumption_computation_context (gh-924), editable
    - s_ref_m2: from assumption_computation_context, read-only display
    - eta_prop: default 0.65 (placeholder until prop-finder Phase 2, #199), editable
    - eta_motor: default 0.85 (brushless typical), editable per motor selection
    - motors: brushless_motor catalog sorted by name, with efficiency_pct
    - warnings: notes about any defaulted parameters
    """
    try:
        return svc.get_modal_params(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        logger.exception("Unexpected error in get_powertrain_sizing_modal_params: %s", exc)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
