import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Path, Depends, Query, Body
from fastapi import Response
from fastapi import status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app import schemas
from app.db.session import get_db
from app.schemas.AeroplaneRequest import AeroplaneMassRequest
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


@router.get("/aeroplanes",
            response_model=GetAeroplaneResponse,
            status_code=status.HTTP_200_OK,
            tags=["aeroplanes"],
            operation_id="get_all_aeroplanes")
async def get_aeroplanes(db: Session = Depends(get_db)) -> GetAeroplaneResponse:
    """Returns a list of all aeroplanes names with ids alphabetically sorted by the name."""
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


@router.post("/aeroplanes",
             status_code=status.HTTP_201_CREATED,
             tags=["aeroplanes"],
             operation_id="create_aeroplane")
async def create_aeroplane(
        name: str = Query(..., description="The aeroplanes name.", examples=["RV-7", "eHawk"]),
        db: Session = Depends(get_db)
) -> JSONResponse:
    """Create a new aeroplane instance and returns its ID."""
    aeroplane = aeroplane_service.create_aeroplane(db, name)
    return JSONResponse(content={"id": str(aeroplane.uuid)})


@router.get("/aeroplanes/{aeroplane_id}",
            status_code=status.HTTP_200_OK,
            response_model=schemas.AeroplaneSchema,
            tags=["aeroplanes"],
            operation_id="get_aeroplane_by_id")
async def get_aeroplane(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> schemas.AeroplaneSchema:
    """Returns the aeroplane definition."""
    return aeroplane_service.get_aeroplane_schema(db, aeroplane_id)


@router.delete("/aeroplanes/{aeroplane_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["aeroplanes"],
               operation_id="delete_aeroplane")
async def delete_aeroplane(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane to be deleted"),
        db: Session = Depends(get_db)
):
    """Deletes the aeroplane."""
    aeroplane_service.delete_aeroplane(db, aeroplane_id)
    return


@router.get("/aeroplanes/{aeroplane_id}/total_mass_kg",
            status_code=status.HTTP_200_OK,
            response_model=AeroplaneMassRequest,
            tags=["aeroplanes"],
            operation_id="get_aeroplane_total_mass")
async def get_aeroplane_total_mass_in_kg(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> AeroplaneMassRequest:
    """Returns the total weight of the aeroplane in kg."""
    mass = aeroplane_service.get_aeroplane_mass(db, aeroplane_id)
    return AeroplaneMassRequest(total_mass_kg=mass)


@router.post("/aeroplanes/{aeroplane_id}/total_mass_kg",
             status_code=status.HTTP_201_CREATED,
             response_class=Response,
             tags=["aeroplanes"],
             operation_id="set_aeroplane_total_mass")
async def create_aeroplane_total_mass_kg(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        total_mass_kg: AeroplaneMassRequest = Body(..., description="The total mass of the aeroplane in kg"),
        db: Session = Depends(get_db)
):
    """Set the total mass of the aeroplane in kg. If it already exists, it will be overwritten."""
    created = aeroplane_service.set_aeroplane_mass(db, aeroplane_id, total_mass_kg.total_mass_kg)
    if created:
        return Response(status_code=status.HTTP_201_CREATED)
    else:
        return Response(status_code=status.HTTP_200_OK)