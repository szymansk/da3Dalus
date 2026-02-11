import logging
from typing import List

from fastapi import APIRouter, Path, Depends, Body
from fastapi import Response
from fastapi import status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app import schemas
from app.db.session import get_db
from app.services import wing_service

logger = logging.getLogger(__name__)

router = APIRouter()

AeroPlaneID = UUID4


@router.get("/aeroplanes/{aeroplane_id}/wings",
            status_code=status.HTTP_200_OK,
            response_model=List[str],
            tags=["wings"],
            operation_id="get_aeroplane_wings")
async def get_aeroplane_wings(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> List[str]:
    """Returns a list of aeroplane's wing names."""
    return wing_service.list_wing_names(db, aeroplane_id)


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
    """Create the wing for the aeroplane."""
    wing_service.create_wing(db, aeroplane_id, wing_name, request)
    return


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
    """Overwrite an existing wing with the data in the request."""
    wing_service.update_wing(db, aeroplane_id, wing_name, request)
    return


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            response_model=schemas.AsbWingSchema,
            tags=["wings"],
            operation_id="get_aeroplane_wing")
async def get_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
) -> schemas.AsbWingSchema:
    """Returns the aeroplane wing."""
    return wing_service.get_wing(db, aeroplane_id, wing_name)


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
    """Delete a wing."""
    wing_service.delete_wing(db, aeroplane_id, wing_name)
    return


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
    """Returns the wing's cross-sections as an ordered list."""
    return wing_service.get_wing_cross_sections(db, aeroplane_id, wing_name)


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
    """Delete all cross-sections of a wing."""
    wing_service.delete_all_cross_sections(db, aeroplane_id, wing_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    """Returns the aeroplane wing cross-sections as a list of names."""
    return wing_service.get_cross_section(db, aeroplane_id, wing_name, cross_section_index)


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
):
    """Creates a new cross-section for the wing and splice it into the list of cross-sections."""
    wing_service.create_cross_section(db, aeroplane_id, wing_name, cross_section_index, request)
    return


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
    """Updates the cross-section for the aeroplane."""
    wing_service.update_cross_section(db, aeroplane_id, wing_name, cross_section_index, request)
    return


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
    """Delete a cross-section."""
    wing_service.delete_cross_section(db, aeroplane_id, wing_name, cross_section_index)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    """Returns the control surface for the given cross-section."""
    return wing_service.get_control_surface(db, aeroplane_id, wing_name, cross_section_index)


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
    """Creates a new or updates an existing control surface for the given cross-section."""
    wing_service.upsert_control_surface(db, aeroplane_id, wing_name, cross_section_index, request)
    return Response(status_code=status.HTTP_201_CREATED)


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
    """Deletes the control surface for the given cross-section."""
    wing_service.delete_control_surface(db, aeroplane_id, wing_name, cross_section_index)
    return Response(status_code=status.HTTP_204_NO_CONTENT)