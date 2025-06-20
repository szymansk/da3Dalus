import logging
from datetime import datetime
from typing import List, OrderedDict

from fastapi import APIRouter, Path, Depends, Query, Body, HTTPException
from fastapi import Response
from fastapi import status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app import schemas
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.AeroplaneRequest import AeroplaneMassRequest

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


# Handle an aeroplane
@router.get("/aeroplanes",
            response_model=GetAeroplaneResponse,
            status_code=status.HTTP_200_OK,
            tags=["aeroplanes"],
            operation_id="get_all_aeroplanes")
async def get_aeroplanes(db: Session = Depends(get_db)) -> GetAeroplaneResponse:
    """
    Returns a list of all aeroplanes names with ids alphabetically sorted by the name.
    """
    try:
        # Query all aeroplanes, ordered by name
        aeroplanes = db.query(AeroplaneModel).order_by(AeroplaneModel.name).all()
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
    except SQLAlchemyError as e:
        logger.error(f"Database error when listing aeroplanes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error when listing aeroplanes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/aeroplanes",
             status_code=status.HTTP_201_CREATED,
             tags=["aeroplanes"],
             operation_id="create_aeroplane")
async def create_aeroplane(
        name: str = Query(..., description="The aeroplanes name.", examples=["RV-7", "eHawk"]),
        db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Create a new aeroplane instance and returns its ID.
    """
    try:
        # Create a new aeroplane instance
        aeroplane = AeroplaneModel(name=name)

        # Add to database
        with db.begin():
            db.add(aeroplane)
            db.flush()  # sets the aeroplane.id
            db.refresh(aeroplane)

        # Return the UUID
        return JSONResponse(content={"id": str(aeroplane.uuid)})
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error when creating aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# noinspection PyTypeChecker
@router.get("/aeroplanes/{aeroplane_id}",
            status_code=status.HTTP_200_OK,
            response_model=schemas.AeroplaneSchema,
            tags=["aeroplanes"],
            operation_id="get_aeroplane_by_id")
async def get_aeroplane(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> schemas.AeroplaneSchema:
    """
    Returns the aeroplane definition.
    \f
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")

        # Build wing and fuselage mappings for serialization
        wing_map: OrderedDict[str, schemas.AsbWingSchema] = OrderedDict({
            w.name: schemas.AsbWingSchema.model_validate(w, from_attributes=True)
            for w in aeroplane.wings
        })
        fuselage_map: OrderedDict[str, schemas.FuselageSchema] = OrderedDict({
            f.name: schemas.FuselageSchema.model_validate(f, from_attributes=True)
            for f in aeroplane.fuselages
        })

        # Construct response model instance
        result = schemas.AeroplaneSchema(
            name=aeroplane.name,
            xyz_ref=aeroplane.xyz_ref,
            wings=wing_map,
            fuselages=fuselage_map
        )
        return result
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException as e:
        # re-raise FastAPI HTTPExceptions (e.g., 404) without modification
        raise e
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/aeroplanes/{aeroplane_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["aeroplanes"],
               operation_id="delete_aeroplane")
async def delete_aeroplane(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane to be deleted"),
        db: Session = Depends(get_db)
):
    """
    Deletes the aeroplane.
    """
    try:
        with db.begin():
            # noinspection PyTypeChecker
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            db.delete(aeroplane)
        return
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when deleting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/aeroplanes/{aeroplane_id}/total_mass_kg",
            status_code=status.HTTP_200_OK,
            response_model=AeroplaneMassRequest,
            tags=["aeroplanes"],
            operation_id="get_aeroplane_total_mass")
async def get_aeroplane_total_mass_in_kg(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> AeroplaneMassRequest:
    """
    Returns the total weight of the aeroplane in kg.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        if aeroplane.total_mass_kg is None:
            raise HTTPException(status_code=404, detail="Aeroplane weight not set")
        return AeroplaneMassRequest(total_mass_kg=aeroplane.total_mass_kg)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane weight: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane weight: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


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
    """ Set the total mass of the aeroplane in kg. If it already exists, it will be overwritten. """
    try:
        created: bool = False
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            if aeroplane.total_mass_kg is None:
                created = True
            aeroplane.total_mass_kg = total_mass_kg.total_mass_kg
            aeroplane.updated_at = datetime.now()
        if created:
            return Response(status_code=status.HTTP_201_CREATED)
        else:
            return Response(status_code=status.HTTP_200_OK)
    except SQLAlchemyError as e:
        logger.error(f"Database error when setting aeroplane mass: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error when setting aeroplane mass: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")