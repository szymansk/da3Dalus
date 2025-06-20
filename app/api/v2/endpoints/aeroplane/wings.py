import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Path, Depends, Body, HTTPException
from fastapi import Response
from fastapi import status
from pydantic import UUID4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import schemas
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel, WingModel, WingXSecModel, ControlSurfaceModel

logger = logging.getLogger(__name__)

router = APIRouter()

AeroPlaneID = UUID4

# Handle an aeroplane wings
@router.get("/aeroplanes/{aeroplane_id}/wings",
            status_code=status.HTTP_200_OK,
            response_model=List[str],
            tags=["wings"],
            operation_id="get_aeroplane_wings")
async def get_aeroplane_wings(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> List[str]:
    """
    Returns a list of aeroplane's wing names.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wings = aeroplane.wings
        return [w.name for w in wings]
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane wings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane wings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Handle an aeroplane wing
@router.put("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            status_code=status.HTTP_201_CREATED,
            response_class=Response,
            tags=["wings"],
            operation_id="create_aeroplane_wing")
async def create_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        request: schemas.AsbWingSchema = Body(..., description="The new wing data"),
        db: Session = Depends(get_db)
):
    """
    Create the wing for the aeroplane.
    """
    try:
        # perform read and write in a single transaction to avoid nested begin
        with db.begin():
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            if any(w.name == wing_name for w in plane.wings):
                raise HTTPException(400, "Wing name must be unique for this aeroplane")

            wing = WingModel.from_dict(name=wing_name, data=request.model_dump())
            plane.wings.append(wing)
            db.add(wing)
            plane.updated_at = datetime.now()
        return
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when creating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["wings"],
    operation_id="update_aeroplane_wing"
)
async def update_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        request: schemas.AsbWingSchema = Body(..., description="The new wing data"),
        db: Session = Depends(get_db),
):
    """
    Overwrite an existing wing with the data in the request.
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

            wing = next((w for w in plane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(404, "Wing not found")

            new_wing = WingModel.from_dict(name=wing_name, data=request.model_dump())
            plane.wings.remove(wing)
            plane.wings.append(new_wing)
            plane.updated_at = datetime.now()
        return
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error("DB error updating wing: %s", e)
        raise HTTPException(500, f"Database error: {e}")
    except Exception as e:
        logger.error("Unexpected error updating wing: %s", e)
        raise HTTPException(500, f"Unexpected error: {e}")


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            response_model=schemas.AsbWingSchema,
            tags=["wings"],
            operation_id="get_aeroplane_wing")
async def get_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
) -> schemas.AsbWingSchema:
    """
    Returns the aeroplane wing.
    """
    try:
        # Load the parent aeroplane
        plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not plane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        # Find the wing belonging to this aeroplane
        wing = next((w for w in plane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        return schemas.AsbWingSchema.model_validate(wing, from_attributes=True)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["wings"],
    operation_id="delete_aeroplane_wing"
)
async def delete_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
):
    """
    Delete a wing.
    """
    try:
        # Find the plane and the wing belonging to it
        with db.begin():
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in plane.wings if str(w.name) == str(wing_name)), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            db.delete(wing)
            plane.updated_at = datetime.now()
        return
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when deleting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


#########################################
# Handle an aeroplane wing cross sections
#########################################
@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections",
    response_model=List[schemas.WingXSecSchema],
    status_code=status.HTTP_200_OK,
    tags=["cross-sections"],
    operation_id="get_wing_cross_sections"
)
async def get_aeroplane_wing_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
) -> List[schemas.WingXSecSchema]:
    """
    Returns the wing's cross-sections as an ordered list.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        # Serialize cross-sections
        return [
            schemas.WingXSecSchema.model_validate(xs, from_attributes=True)
            for xs in wing.x_secs
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["cross-sections"],
    operation_id="delete_all_wing_cross_sections"
)
async def delete_aeroplane_wing_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
):
    """
    Delete all cross-sections of a wing.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            # Remove all cross-sections (using delete-orphan cascade)
            wing.x_secs.clear()
            # Touch parent timestamp
            aeroplane.updated_at = datetime.now()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when deleting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_model=schemas.WingXSecSchema,
    status_code=status.HTTP_200_OK,
    tags=["cross-sections"],
    operation_id="get_wing_cross_section"
)
async def get_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
) -> schemas.WingXSecSchema:
    """
    Returns the aeroplane wing cross-sections as a list of names.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        x_secs = wing.x_secs
        if cross_section_index < 0 or cross_section_index >= len(x_secs):
            raise HTTPException(status_code=404, detail="Cross-section not found")
        xs = x_secs[cross_section_index]
        return schemas.WingXSecSchema.model_validate(xs, from_attributes=True)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when getting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["cross-sections"],
    operation_id="create_wing_cross_section"
)
async def create_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(...,
                                        description="The index where it will be spliced into the list of cross sections. (-1 is the end of the list, 0 is the start of the list)"),
        request: schemas.WingXSecSchema = Body(..., description="Wing cross section request"),
        db: Session = Depends(get_db)
) :
    """
    Creates a new cross-section for the wing and splice it into the list of cross-sections.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            # build new WingXSec from request data
            data = request.model_dump()
            cs_dict = data.pop("control_surface", None)
            new_xsec = WingXSecModel(**data)

            if cs_dict is not None:
                # Accept both dict and pydantic model
                if hasattr(cs_dict, "model_dump"):
                    cs_dict = cs_dict.model_dump()
                new_xsec.control_surface = ControlSurfaceModel(**cs_dict)

            # determine insertion index
            existing = wing.x_secs  # already ordered by sort_index
            if cross_section_index == -1 or cross_section_index >= len(existing):
                insertion_index = len(existing)
            else:
                insertion_index = cross_section_index
            # shift sort_index of following cross-sections
            for xs in existing[insertion_index:]:
                xs.sort_index = xs.sort_index + 1
                db.add(xs)
            # assign sort_index and insert new cross-section
            new_xsec.sort_index = insertion_index
            if insertion_index == len(existing):
                wing.x_secs.append(new_xsec)
            else:
                wing.x_secs.insert(insertion_index, new_xsec)
            # touch parent timestamp
            aeroplane.updated_at = datetime.now()
            db.add(new_xsec)
        return
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when creating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.put(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["cross-sections"],
    operation_id="update_wing_cross_section"
)
async def update_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        request: schemas.WingXSecSchema = Body(...),
        db: Session = Depends(get_db)
):
    """
    Updates the cross-section for the aeroplane.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            x_secs = wing.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")

            data = request.model_dump()
            cs_dict = data.pop("control_surface", None)
            new_xsec = WingXSecModel(sort_index=cross_section_index, **data)

            # Handle control surface
            existing_xsec = x_secs[cross_section_index]
            if cs_dict is not None:
                # Accept both dict and pydantic model
                if hasattr(cs_dict, "model_dump"):
                    cs_dict = cs_dict.model_dump()
                new_xsec.control_surface = ControlSurfaceModel(**cs_dict)
            elif existing_xsec.control_surface is not None:
                # Preserve existing control surface if not provided in request
                cs_data = schemas.ControlSurfaceSchema.model_validate(
                    existing_xsec.control_surface, from_attributes=True
                ).model_dump()
                new_xsec.control_surface = ControlSurfaceModel(**cs_data)

            wing.x_secs[cross_section_index] = new_xsec
            # Touch parent timestamp
            aeroplane.updated_at = datetime.now()
        return
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when updating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["cross-sections"],
               operation_id="delete_wing_cross_section")
async def delete_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
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
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            x_secs = wing.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")
            # Remove and delete the cross-section
            xsec = x_secs.pop(cross_section_index)
            db.delete(xsec)
            aeroplane.updated_at = datetime.now()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when deleting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_model=schemas.ControlSurfaceSchema,
    status_code=status.HTTP_200_OK,
    tags=["control_surface"],
    operation_id="get_control_surface"
)
async def get_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
):
    """
    Returns the control surface for the given cross-section.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        x_secs = wing.x_secs
        if cross_section_index < 0 or cross_section_index >= len(x_secs):
            raise HTTPException(status_code=404, detail="Cross-section not found")
        xs = x_secs[cross_section_index]
        cs = xs.control_surface
        if not cs:
            raise HTTPException(status_code=404, detail="Control surface not found")
        # Use Pydantic model for response
        return schemas.ControlSurfaceSchema.model_validate(cs, from_attributes=True)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting control surface: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting control surface: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["control_surface"],
    operation_id="upsert_control_surface"
)
async def create_and_update_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    request: schemas.ControlSurfaceSchema = Body(...),
    db: Session = Depends(get_db),
) -> Response:
    """
    Creates a new or updates an existing control surface for the given cross-section.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            x_secs = wing.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")
            xs = x_secs[cross_section_index]
            data = request.model_dump()
            # update existing or create new control surface
            if xs.control_surface:
                cs = xs.control_surface
                for key, value in data.items():
                    setattr(cs, key, value)
            else:
                cs = ControlSurfaceModel(**data)
                xs.control_surface = cs
                db.add(cs)
            aeroplane.updated_at = datetime.now()
        return Response(status_code=status.HTTP_201_CREATED)
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating/updating control surface: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when creating/updating control surface: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["control_surface"],
    operation_id="delete_control_surface"
)
async def delete_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> Response:
    """
    Deletes the control surface for the given cross-section.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            x_secs = wing.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")
            xs = x_secs[cross_section_index]
            cs = xs.control_surface
            if not cs:
                raise HTTPException(status_code=404, detail="Control surface not found")
            xs.control_surface = None
            db.delete(cs)
            aeroplane.updated_at = datetime.now()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting control surface: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when deleting control surface: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")