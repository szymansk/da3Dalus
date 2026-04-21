import logging
from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Path, Depends, Query, Body, Response, HTTPException
from fastapi import status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.db.session import get_db
from app.schemas.AeroplaneRequest import AeroplaneMassRequest
from app.schemas.api_responses import (
    AirplaneConfigurationResponse,
    CreateAeroplaneResponse,
    OperationStatusResponse,
)
from app.services import aeroplane_service

logger = logging.getLogger(__name__)

router = APIRouter()

AeroPlaneID = UUID4


class GetAeroplaneResponse(BaseModel):
    class NameIdMap(BaseModel):
        name: str
        id: AeroPlaneID
        created_at: datetime
        updated_at: datetime

    aeroplanes: List[NameIdMap]


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


@router.get("/aeroplanes",
            status_code=status.HTTP_200_OK,
            tags=["aeroplanes"],
            operation_id="get_all_aeroplanes")
async def get_aeroplanes(db: Annotated[Session, Depends(get_db)]) -> GetAeroplaneResponse:
    """Returns a list of all aeroplanes names with ids alphabetically sorted by the name."""
    try:
        aeroplanes = aeroplane_service.list_all_aeroplanes(db)
        items = [
            GetAeroplaneResponse.NameIdMap(
                name=ap.name,
                id=ap.uuid,
                created_at=ap.created_at,
                updated_at=ap.updated_at,
            )
            for ap in aeroplanes
        ]
        return GetAeroplaneResponse(aeroplanes=items)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes",
             status_code=status.HTTP_201_CREATED,
             tags=["aeroplanes"],
             operation_id="create_aeroplane")
async def create_aeroplane(
        name: Annotated[str, Query(..., description="The aeroplanes name.", examples=["RV-7", "eHawk"])],
        db: Annotated[Session, Depends(get_db)],
) -> CreateAeroplaneResponse:
    """Create a new aeroplane instance and returns its ID."""
    try:
        aeroplane = aeroplane_service.create_aeroplane(db, name)
        return CreateAeroplaneResponse(id=str(aeroplane.uuid))
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.get("/aeroplanes/{aeroplane_id}",
            status_code=status.HTTP_200_OK,
            tags=["aeroplanes"],
            operation_id="get_aeroplane_by_id")
async def get_aeroplane(
        aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
        db: Annotated[Session, Depends(get_db)],
) -> schemas.AeroplaneSchema:
    """Returns the aeroplane definition."""
    try:
        return aeroplane_service.get_aeroplane_schema(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.delete("/aeroplanes/{aeroplane_id}",
               status_code=status.HTTP_200_OK,
               response_model=OperationStatusResponse,
               tags=["aeroplanes"],
               operation_id="delete_aeroplane")
async def delete_aeroplane(
        aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane to be deleted")],
        db: Annotated[Session, Depends(get_db)],
):
    """Deletes the aeroplane."""
    try:
        aeroplane_service.delete_aeroplane(db, aeroplane_id)
        return OperationStatusResponse(status="ok", operation="delete_aeroplane")
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.get("/aeroplanes/{aeroplane_id}/total_mass_kg",
            status_code=status.HTTP_200_OK,
            tags=["aeroplanes"],
            operation_id="get_aeroplane_total_mass")
async def get_aeroplane_total_mass_in_kg(
        aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
        db: Annotated[Session, Depends(get_db)],
) -> AeroplaneMassRequest:
    """Returns the total weight of the aeroplane in kg."""
    try:
        mass = aeroplane_service.get_aeroplane_mass(db, aeroplane_id)
        return AeroplaneMassRequest(total_mass_kg=mass)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes/{aeroplane_id}/total_mass_kg",
             status_code=status.HTTP_201_CREATED,
             responses={
                 200: {"model": OperationStatusResponse},
                 201: {"model": OperationStatusResponse},
             },
             tags=["aeroplanes"],
             operation_id="set_aeroplane_total_mass")
async def create_aeroplane_total_mass_kg(
        aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
        total_mass_kg: Annotated[AeroplaneMassRequest, Body(..., description="The total mass of the aeroplane in kg")],
        response: Response = None,
        db: Annotated[Session, Depends(get_db)] = None,
) -> OperationStatusResponse:
    """Set the total mass of the aeroplane in kg. If it already exists, it will be overwritten."""
    try:
        created = aeroplane_service.set_aeroplane_mass(db, aeroplane_id, total_mass_kg.total_mass_kg)
        if created:
            if response is not None:
                response.status_code = status.HTTP_201_CREATED
            return OperationStatusResponse(status="created", operation="set_aeroplane_total_mass")

        if response is not None:
            response.status_code = status.HTTP_200_OK
        return OperationStatusResponse(status="ok", operation="set_aeroplane_total_mass")
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/airplane_configuration",
    status_code=status.HTTP_200_OK,
    tags=["aeroplanes"],
    operation_id="get_aeroplane_airplane_configuration",
)
async def get_aeroplane_airplane_configuration(
        aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
        db: Annotated[Session, Depends(get_db)],
) -> AirplaneConfigurationResponse:
    """Returns the full AirplaneConfiguration payload for the aeroplane."""
    try:
        payload = aeroplane_service.get_aeroplane_airplane_configuration(db, aeroplane_id)
        return AirplaneConfigurationResponse.model_validate(payload)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc
