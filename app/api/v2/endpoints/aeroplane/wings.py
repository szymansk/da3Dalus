import logging
from typing import List

from fastapi import APIRouter, Path, Depends, Body, HTTPException
from fastapi import status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session

from app import schemas
from app.schemas.wing import Wing as WingConfigurationSchema
from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.db.session import get_db
from app.services import wing_service

logger = logging.getLogger(__name__)

router = APIRouter()

AeroPlaneID = UUID4


class OperationStatusResponse(BaseModel):
    status: str
    operation: str


_EHAWK_WINGCONFIG_EXAMPLE = {
    "segments": [
        {
            "root_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 162.0,
                "dihedral_as_rotation_in_degrees": 1,
                "dihedral_as_translation": 0,
                "incidence": 0,
                "rotation_point_rel_chord": 0.25,
            },
            "length": 20.0,
            "sweep": 0,
            "sweep_angle": 0.0,
            "tip_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 162.0,
                "dihedral_as_rotation_in_degrees": 0,
                "dihedral_as_translation": 0,
                "incidence": 0,
                "rotation_point_rel_chord": 0.25,
            },
            "spare_list": [
                {
                    "spare_support_dimension_width": 4.42,
                    "spare_support_dimension_height": 4.42,
                    "spare_position_factor": 0.25,
                    "spare_length": None,
                    "spare_start": 0.0,
                    "spare_mode": "standard",
                    "spare_vector": [0.03675826199775033, 0.9992133621593052, 0.014882441237981629],
                    "spare_origin": [40.5, -0.06030645607992891, 3.454954554906206],
                }
            ],
            "trailing_edge_device": None,
            "number_interpolation_points": 201,
            "tip_type": None,
            "wing_segment_type": "root",
        },
        {
            "root_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 162.0,
                "dihedral_as_rotation_in_degrees": 0,
                "dihedral_as_translation": 0,
                "incidence": 0,
                "rotation_point_rel_chord": 0.25,
            },
            "length": 200,
            "sweep": 2.5,
            "sweep_angle": 0.7161599454704085,
            "tip_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 157,
                "dihedral_as_rotation_in_degrees": 0,
                "dihedral_as_translation": 0,
                "incidence": 0,
                "rotation_point_rel_chord": 0.25,
            },
            "spare_list": [
                {
                    "spare_support_dimension_width": 4.42,
                    "spare_support_dimension_height": 4.42,
                    "spare_position_factor": 0.25,
                    "spare_length": None,
                    "spare_start": 0.0,
                    "spare_mode": "follow",
                    "spare_vector": [0.03675826199775033, 0.9992133621593052, 0.014882441237981629],
                    "spare_origin": [41.23516523995501, 19.923960787106175, 3.752603379665839],
                }
            ],
            "trailing_edge_device": None,
            "number_interpolation_points": 201,
            "tip_type": None,
            "wing_segment_type": "segment",
        },
        {
            "root_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 157,
                "dihedral_as_rotation_in_degrees": 0,
                "dihedral_as_translation": 0,
                "incidence": 0,
                "rotation_point_rel_chord": 0.25,
            },
            "length": 250,
            "sweep": 8,
            "sweep_angle": 1.8328395059420592,
            "tip_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 132.88888888888889,
                "dihedral_as_rotation_in_degrees": 0,
                "dihedral_as_translation": 0,
                "incidence": 0,
                "rotation_point_rel_chord": 0.25,
            },
            "spare_list": [
                {
                    "spare_support_dimension_width": 4.42,
                    "spare_support_dimension_height": 4.42,
                    "spare_position_factor": 0.25,
                    "spare_length": None,
                    "spare_start": 0.0,
                    "spare_mode": "follow",
                    "spare_vector": [0.03675826199775033, 0.9992133621593052, 0.014882441237981629],
                    "spare_origin": [48.58681763950507, 219.76663321896723, 6.729091627262164],
                }
            ],
            "trailing_edge_device": {
                "name": "aileron",
                "rel_chord_root": 0.8,
                "rel_chord_tip": 0.8,
                "hinge_spacing": 0.5,
                "side_spacing_root": 2.0,
                "side_spacing_tip": 2.0,
                "_servo": 1,
                "servo_placement": "top",
                "rel_chord_servo_position": 0.414,
                "rel_length_servo_position": 0.486,
                "positive_deflection_deg": 35,
                "negative_deflection_deg": 35,
                "trailing_edge_offset_factor": 1.2,
                "hinge_type": "top",
                "symmetric": False,
            },
            "number_interpolation_points": 201,
            "tip_type": None,
            "wing_segment_type": "segment",
        },
    ],
    "nose_pnt": [0, 0, 0],
    "parameters": "relative",
    "symmetric": True,
}


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


def _call_service(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


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
    return _call_service(wing_service.list_wing_names, db, aeroplane_id)


@router.put("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            status_code=status.HTTP_201_CREATED,
            response_model=OperationStatusResponse,
            tags=["wings"],
            operation_id="create_aeroplane_wing")
async def create_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        request: schemas.AsbWingSchema = Body(..., description="The new wing data"),
        db: Session = Depends(get_db)
):
    """Create the wing for the aeroplane."""
    _call_service(wing_service.create_wing, db, aeroplane_id, wing_name, request)
    return OperationStatusResponse(status="created", operation="create_aeroplane_wing")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
    status_code=status.HTTP_201_CREATED,
    response_model=OperationStatusResponse,
    tags=["wings"],
    operation_id="create_aeroplane_wing_from_wingconfig",
)
async def create_aeroplane_wing_from_wingconfig(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    request: WingConfigurationSchema = Body(
        ...,
        description=(
            "WingConfiguration-JSON (typisch in mm). "
            "Wird intern nach ASB konvertiert und als Wing im Flugzeug gespeichert."
        ),
        examples=[_EHAWK_WINGCONFIG_EXAMPLE],
    ),
    db: Session = Depends(get_db),
):
    """Create a wing from WingConfiguration JSON and attach it to the aeroplane."""
    _call_service(wing_service.create_wing_from_wing_configuration, db, aeroplane_id, wing_name, request)
    return OperationStatusResponse(status="created", operation="create_aeroplane_wing_from_wingconfig")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
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
    _call_service(wing_service.update_wing, db, aeroplane_id, wing_name, request)
    return OperationStatusResponse(status="ok", operation="update_aeroplane_wing")


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
    return _call_service(wing_service.get_wing, db, aeroplane_id, wing_name)


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["wings"],
    operation_id="delete_aeroplane_wing"
)
async def delete_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
):
    """Delete a wing."""
    _call_service(wing_service.delete_wing, db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="ok", operation="delete_aeroplane_wing")


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
    return _call_service(wing_service.get_wing_cross_sections, db, aeroplane_id, wing_name)


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections",
    status_code=status.HTTP_200_OK,
    response_model=OperationStatusResponse,
    tags=["cross-sections"],
    operation_id="delete_all_wing_cross_sections"
)
async def delete_aeroplane_wing_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
):
    """Delete all cross-sections of a wing."""
    _call_service(wing_service.delete_all_cross_sections, db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="ok", operation="delete_all_wing_cross_sections")


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
    return _call_service(wing_service.get_cross_section, db, aeroplane_id, wing_name, cross_section_index)


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_model=OperationStatusResponse,
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
    _call_service(wing_service.create_cross_section, db, aeroplane_id, wing_name, cross_section_index, request)
    return OperationStatusResponse(status="created", operation="create_wing_cross_section")


@router.put(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
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
    _call_service(wing_service.update_cross_section, db, aeroplane_id, wing_name, cross_section_index, request)
    return OperationStatusResponse(status="ok", operation="update_wing_cross_section")


@router.delete("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
               status_code=status.HTTP_200_OK,
               response_model=OperationStatusResponse,
               tags=["cross-sections"],
               operation_id="delete_wing_cross_section")
async def delete_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
):
    """Delete a cross-section."""
    _call_service(wing_service.delete_cross_section, db, aeroplane_id, wing_name, cross_section_index)
    return OperationStatusResponse(status="ok", operation="delete_wing_cross_section")


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
    return _call_service(wing_service.get_control_surface, db, aeroplane_id, wing_name, cross_section_index)


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["control_surface"],
    operation_id="upsert_control_surface"
)
async def create_and_update_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    request: schemas.ControlSurfaceSchema = Body(...),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Creates a new or updates an existing control surface for the given cross-section."""
    _call_service(wing_service.upsert_control_surface, db, aeroplane_id, wing_name, cross_section_index, request)
    return OperationStatusResponse(status="ok", operation="upsert_control_surface")


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["control_surface"],
    operation_id="delete_control_surface"
)
async def delete_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Deletes the control surface for the given cross-section."""
    _call_service(wing_service.delete_control_surface, db, aeroplane_id, wing_name, cross_section_index)
    return OperationStatusResponse(status="ok", operation="delete_control_surface")
