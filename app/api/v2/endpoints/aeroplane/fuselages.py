import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Path, Depends, Body, HTTPException
from fastapi import status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import schemas
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel, FuselageModel, FuselageXSecSuperEllipseModel

logger = logging.getLogger(__name__)

router = APIRouter()

AeroPlaneID = UUID4


class OperationStatusResponse(BaseModel):
    status: str
    operation: str


# Handle an aeroplane fuselages
@router.get("/aeroplanes/{aeroplane_id}/fuselages",
            status_code=status.HTTP_200_OK,
            response_model=List[str],
            tags=["fuselages"],
            operation_id="get_aeroplane_fuselages")
async def get_aeroplane_fuselages(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> List[str]:
    """
    Returns a list of aeroplane's fuselage names.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        fuselages = aeroplane.fuselages
        return [f.name for f in fuselages]
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane fuselages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane fuselages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Handle an aeroplane fuselage
@router.put("/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
            status_code=status.HTTP_201_CREATED,
            response_model=OperationStatusResponse,
            tags=["fuselages"],
            operation_id="create_aeroplane_fuselage")
async def create_aeroplane_fuselage(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        request: schemas.FuselageSchema = Body(..., description="The new fuselage data"),
        db: Session = Depends(get_db)
):
    """
    Create the fuselage for the aeroplane.
    """
    try:
        # perform read and write in a single transaction to avoid nested begin
        with db.begin():
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            if any(f.name == fuselage_name for f in plane.fuselages):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Fuselage name must be unique for this aeroplane",
                )

            # Create fuselage from request data
            fuselage = FuselageModel.from_dict(name=fuselage_name, data=request.model_dump())

            plane.fuselages.append(fuselage)
            db.add(fuselage)
            plane.updated_at = datetime.now()
        return OperationStatusResponse(status="created", operation="create_aeroplane_fuselage")
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating aeroplane fuselage: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when creating aeroplane fuselage: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["fuselages"],
    operation_id="update_aeroplane_fuselage"
)
async def update_aeroplane_fuselage(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        request: schemas.FuselageSchema = Body(..., description="The new fuselage data"),
        db: Session = Depends(get_db),
):
    """
    Overwrite an existing fuselage with the data in the request.
    """
    try:
        with db.begin():
            plane = (
                db.query(AeroplaneModel)
                .filter(AeroplaneModel.uuid == aeroplane_id)
                .first()
            )
            if not plane:
                raise HTTPException(404, "Aeroplane not found")

            fuselage = next((f for f in plane.fuselages if f.name == fuselage_name), None)
            if not fuselage:
                raise HTTPException(404, "Fuselage not found")

            # Create new fuselage from request data
            new_fuselage = FuselageModel.from_dict(name=fuselage_name, data=request.model_dump())

            plane.fuselages.remove(fuselage)
            plane.fuselages.append(new_fuselage)
            plane.updated_at = datetime.now()
        return OperationStatusResponse(status="ok", operation="update_aeroplane_fuselage")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error("DB error updating fuselage: %s", e)
        raise HTTPException(500, f"Database error: {e}")
    except Exception as e:
        logger.error("Unexpected error updating fuselage: %s", e)
        raise HTTPException(500, f"Unexpected error: {e}")


@router.get("/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
            response_model=schemas.FuselageSchema,
            tags=["fuselages"],
            operation_id="get_aeroplane_fuselage")
async def get_aeroplane_fuselage(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        db: Session = Depends(get_db)
) -> schemas.FuselageSchema:
    """
    Returns the aeroplane fuselage.
    """
    try:
        # Load the parent aeroplane
        plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not plane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        # Find the fuselage belonging to this aeroplane
        fuselage = next((f for f in plane.fuselages if f.name == fuselage_name), None)
        if not fuselage:
            raise HTTPException(status_code=404, detail="Fuselage not found")
        return schemas.FuselageSchema.model_validate(fuselage, from_attributes=True)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane fuselage: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane fuselage: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["fuselages"],
    operation_id="delete_aeroplane_fuselage"
)
async def delete_aeroplane_fuselage(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        db: Session = Depends(get_db)
):
    """
    Delete a fuselage.
    """
    try:
        # Find the plane and the fuselage belonging to it
        with db.begin():
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            fuselage = next((f for f in plane.fuselages if str(f.name) == str(fuselage_name)), None)
            if not fuselage:
                raise HTTPException(status_code=404, detail="Fuselage not found")
            db.delete(fuselage)
            plane.updated_at = datetime.now()
        return OperationStatusResponse(status="ok", operation="delete_aeroplane_fuselage")
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting aeroplane fuselage: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when deleting aeroplane fuselage: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


#########################################
# Handle an aeroplane fuselage cross sections
#########################################
@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections",
    response_model=List[schemas.FuselageXSecSuperEllipseSchema],
    status_code=status.HTTP_200_OK,
    tags=["fuselage-cross-sections"],
    operation_id="get_fuselage_cross_sections"
)
async def get_aeroplane_fuselage_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        db: Session = Depends(get_db)
) -> List[schemas.FuselageXSecSuperEllipseSchema]:
    """
    Returns the fuselage's cross-sections as a list.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
        if not fuselage:
            raise HTTPException(status_code=404, detail="Fuselage not found")
        # Serialize cross-sections
        return [
            schemas.FuselageXSecSuperEllipseSchema.model_validate(xs, from_attributes=True)
            for xs in fuselage.x_secs
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting fuselage cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting fuselage cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections",
    status_code=status.HTTP_200_OK,
    response_model=OperationStatusResponse,
    tags=["fuselage-cross-sections"],
    operation_id="delete_all_fuselage_cross_sections"
)
async def delete_aeroplane_fuselage_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        db: Session = Depends(get_db)
):
    """
    Delete all cross-sections of a fuselage.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
            if not fuselage:
                raise HTTPException(status_code=404, detail="Fuselage not found")
            # Remove all cross-sections (using delete-orphan cascade)
            fuselage.x_secs.clear()
            # Touch parent timestamp
            aeroplane.updated_at = datetime.now()
        return OperationStatusResponse(status="ok", operation="delete_all_fuselage_cross_sections")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting fuselage cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when deleting fuselage cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    response_model=schemas.FuselageXSecSuperEllipseSchema,
    status_code=status.HTTP_200_OK,
    tags=["fuselage-cross-sections"],
    operation_id="get_fuselage_cross_section"
)
async def get_aeroplane_fuselage_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
) -> schemas.FuselageXSecSuperEllipseSchema:
    """
    Returns the aeroplane fuselage cross-section at the specified index.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
        if not fuselage:
            raise HTTPException(status_code=404, detail="Fuselage not found")
        x_secs = fuselage.x_secs
        if cross_section_index < 0 or cross_section_index >= len(x_secs):
            raise HTTPException(status_code=404, detail="Cross-section not found")
        xs = x_secs[cross_section_index]
        return schemas.FuselageXSecSuperEllipseSchema.model_validate(xs, from_attributes=True)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when getting fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["fuselage-cross-sections"],
    operation_id="create_fuselage_cross_section"
)
async def create_aeroplane_fuselage_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        cross_section_index: int = Path(...,
                                        description="The index where it will be spliced into the list of cross sections. (-1 is the end of the list, 0 is the start of the list)"),
        request: schemas.FuselageXSecSuperEllipseSchema = Body(..., description="Fuselage cross section request"),
        db: Session = Depends(get_db)
) :
    """
    Creates a new cross-section for the fuselage and splice it into the list of cross-sections.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
            if not fuselage:
                raise HTTPException(status_code=404, detail="Fuselage not found")
            # build new FuselageXSecSuperEllipseModel from request data
            data = request.model_dump()

            # determine insertion index
            existing = fuselage.x_secs
            if cross_section_index == -1 or cross_section_index >= len(existing):
                insertion_index = len(existing)
            else:
                insertion_index = cross_section_index

            # shift sort_index of following cross-sections
            for xs in existing[insertion_index:]:
                xs.sort_index = xs.sort_index + 1
                db.add(xs)

            # create new cross-section with appropriate sort_index
            new_xsec = FuselageXSecSuperEllipseModel(sort_index=insertion_index, **data)

            # insert new cross-section
            if insertion_index == len(existing):
                fuselage.x_secs.append(new_xsec)
            else:
                fuselage.x_secs.insert(insertion_index, new_xsec)
            # touch parent timestamp
            aeroplane.updated_at = datetime.now()
            db.add(new_xsec)
        return OperationStatusResponse(status="created", operation="create_fuselage_cross_section")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when creating fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.put(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["fuselage-cross-sections"],
    operation_id="update_fuselage_cross_section"
)
async def update_aeroplane_fuselage_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        request: schemas.FuselageXSecSuperEllipseSchema = Body(...),
        db: Session = Depends(get_db)
):
    """
    Updates the cross-section for the fuselage.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
            if not fuselage:
                raise HTTPException(status_code=404, detail="Fuselage not found")
            x_secs = fuselage.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")

            data = request.model_dump()
            # Create new cross-section with the same sort_index as the one being replaced
            new_xsec = FuselageXSecSuperEllipseModel(sort_index=cross_section_index, **data)

            fuselage.x_secs[cross_section_index] = new_xsec
            # Touch parent timestamp
            aeroplane.updated_at = datetime.now()
        return OperationStatusResponse(status="ok", operation="update_fuselage_cross_section")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when updating fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete("/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
               status_code=status.HTTP_200_OK,
               response_model=OperationStatusResponse,
               tags=["fuselage-cross-sections"],
               operation_id="delete_fuselage_cross_section")
async def delete_aeroplane_fuselage_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        fuselage_name: str = Path(..., description="The ID of the fuselage"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
):
    """
    Delete a cross-section.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
            if not fuselage:
                raise HTTPException(status_code=404, detail="Fuselage not found")
            x_secs = fuselage.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")
            # Remove and delete the cross-section
            xsec = x_secs.pop(cross_section_index)
            db.delete(xsec)

            # Update sort_index for remaining cross-sections
            for i, xs in enumerate(x_secs):
                if xs.sort_index != i:
                    xs.sort_index = i
                    db.add(xs)

            aeroplane.updated_at = datetime.now()
        return OperationStatusResponse(status="ok", operation="delete_fuselage_cross_section")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when deleting fuselage cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
