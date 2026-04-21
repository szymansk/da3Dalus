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
from app.services.tessellation_hooks import on_wing_changed

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

                "incidence": 0,
            },
            "length": 20.0,
            "sweep": 0,
            "sweep_angle": 0.0,
            "tip_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 162.0,
                "dihedral_as_rotation_in_degrees": 0,

                "incidence": 0,
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

                "incidence": 0,
            },
            "length": 200,
            "sweep": 2.5,
            "sweep_angle": 0.7161599454704085,
            "tip_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 157,
                "dihedral_as_rotation_in_degrees": 0,

                "incidence": 0,
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

                "incidence": 0,
            },
            "length": 250,
            "sweep": 8,
            "sweep_angle": 1.8328395059420592,
            "tip_airfoil": {
                "airfoil": "../components/airfoils/mh32.dat",
                "chord": 132.88888888888889,
                "dihedral_as_rotation_in_degrees": 0,

                "incidence": 0,
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


def _assert_design_model(
    db: Session, aeroplane_id: AeroPlaneID, wing_name: str, expected: str,
) -> None:
    """Raise 409 Conflict if the wing's design_model doesn't match *expected*.

    Returns silently when the wing does not exist (creation paths) or when
    design_model is NULL (legacy wings not yet classified).
    Raises HTTP 404 via _call_service if the aeroplane does not exist.
    """
    actual = _call_service(wing_service.get_wing_design_model, db, aeroplane_id, wing_name)
    if actual is not None and actual != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This wing uses design_model='{actual}'. "
                f"This endpoint requires design_model='{expected}'."
            ),
        )


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
        request: schemas.AsbWingGeometryWriteSchema = Body(
            ...,
            description="Geometry-only wing definition (ASB minimum).",
        ),
        db: Session = Depends(get_db)
):
    """Create the wing for the aeroplane."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.create_wing, db, aeroplane_id, wing_name, request)
    on_wing_changed(db, aeroplane_id, wing_name)
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
    _assert_design_model(db, aeroplane_id, wing_name, "wc")
    _call_service(wing_service.create_wing_from_wing_configuration, db, aeroplane_id, wing_name, request)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="created", operation="create_aeroplane_wing_from_wingconfig")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/wingconfig",
    status_code=status.HTTP_200_OK,
    tags=["wings"],
    operation_id="get_wing_as_wingconfig",
)
async def get_wing_as_wingconfig(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    db: Session = Depends(get_db),
):
    """Return the wing in WingConfiguration format (segments with root/tip airfoils, length, sweep, dihedral)."""
    return _call_service(wing_service.get_wing_as_wingconfig, db, aeroplane_id, wing_name)


@router.put(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/wingconfig",
    status_code=status.HTTP_200_OK,
    response_model=OperationStatusResponse,
    tags=["wings"],
    operation_id="put_wing_as_wingconfig",
)
async def put_wing_as_wingconfig(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    request: WingConfigurationSchema = Body(
        ...,
        description="WingConfiguration JSON (mm). Replaces the existing wing.",
    ),
    db: Session = Depends(get_db),
):
    """Replace a wing from WingConfiguration JSON (idempotent PUT)."""
    _assert_design_model(db, aeroplane_id, wing_name, "wc")
    _call_service(wing_service.put_wing_as_wingconfig, db, aeroplane_id, wing_name, request)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="updated", operation="put_wing_as_wingconfig")


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
        request: schemas.AsbWingGeometryWriteSchema = Body(
            ...,
            description="Geometry-only wing definition (ASB minimum).",
        ),
        db: Session = Depends(get_db),
):
    """Overwrite an existing wing with the data in the request."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.update_wing, db, aeroplane_id, wing_name, request)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="ok", operation="update_aeroplane_wing")


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            response_model=schemas.AsbWingReadSchema,
            tags=["wings"],
            operation_id="get_aeroplane_wing")
async def get_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
) -> schemas.AsbWingReadSchema:
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
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="ok", operation="delete_aeroplane_wing")


#########################################
# Handle an aeroplane wing cross sections
#########################################
@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections",
    response_model=List[schemas.WingXSecReadSchema],
    status_code=status.HTTP_200_OK,
    tags=["cross-sections"],
    operation_id="get_wing_cross_sections"
)
async def get_aeroplane_wing_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
) -> List[schemas.WingXSecReadSchema]:
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
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.delete_all_cross_sections, db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="ok", operation="delete_all_wing_cross_sections")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_model=schemas.WingXSecReadSchema,
    status_code=status.HTTP_200_OK,
    tags=["cross-sections"],
    operation_id="get_wing_cross_section"
)
async def get_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
) -> schemas.WingXSecReadSchema:
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
        request: schemas.WingXSecGeometryWriteSchema = Body(
            ...,
            description="Geometry-only wing cross-section definition.",
        ),
        db: Session = Depends(get_db)
):
    """Creates a new cross-section for the wing and splice it into the list of cross-sections."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.create_cross_section, db, aeroplane_id, wing_name, cross_section_index, request)
    on_wing_changed(db, aeroplane_id, wing_name)
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
        request: schemas.WingXSecGeometryWriteSchema = Body(
            ...,
            description="Geometry-only wing cross-section definition.",
        ),
        db: Session = Depends(get_db)
):
    """Updates the cross-section for the aeroplane."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.update_cross_section, db, aeroplane_id, wing_name, cross_section_index, request)
    on_wing_changed(db, aeroplane_id, wing_name)
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
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.delete_cross_section, db, aeroplane_id, wing_name, cross_section_index)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="ok", operation="delete_wing_cross_section")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars",
    response_model=List[schemas.SpareDetailSchema],
    status_code=status.HTTP_200_OK,
    tags=["spars"],
    operation_id="get_wing_cross_section_spars",
)
async def get_aeroplane_wing_cross_section_spars(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> List[schemas.SpareDetailSchema]:
    """Returns the spars assigned to the given cross-section."""
    return _call_service(wing_service.get_spares, db, aeroplane_id, wing_name, cross_section_index)


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["spars"],
    operation_id="create_wing_cross_section_spar",
)
async def create_aeroplane_wing_cross_section_spar(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    request: schemas.SpareDetailSchema = Body(..., description="Spar definition to append"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Creates and appends one spar on the selected cross-section."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.create_spare, db, aeroplane_id, wing_name, cross_section_index, request)
    return OperationStatusResponse(status="created", operation="create_wing_cross_section_spar")


@router.put(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars/{spar_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["spars"],
    operation_id="update_wing_cross_section_spar",
)
async def update_aeroplane_wing_cross_section_spar(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    spar_index: int = Path(..., description="The index of the spar to replace"),
    request: schemas.SpareDetailSchema = Body(..., description="Updated spar definition"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Replaces the spar at the given index on the selected cross-section."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.update_spare, db, aeroplane_id, wing_name, cross_section_index, spar_index, request)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="updated", operation="update_wing_cross_section_spar")


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars/{spar_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["spars"],
    operation_id="delete_wing_cross_section_spar",
)
async def delete_aeroplane_wing_cross_section_spar(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    spar_index: int = Path(..., description="The index of the spar to delete"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Deletes the spar at the given index on the selected cross-section."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.delete_spare, db, aeroplane_id, wing_name, cross_section_index, spar_index)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="deleted", operation="delete_wing_cross_section_spar")


# ── TED direct-access endpoints (gh#97) ─────────────────────────
# These expose the full TrailingEdgeDeviceDetailSchema, bypassing the
# ControlSurface ASB-view wrapper. Service functions already existed
# in wing_service.py but had no HTTP routes until now.

@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/trailing_edge_device",
    response_model=schemas.TrailingEdgeDeviceDetailSchema,
    status_code=status.HTTP_200_OK,
    tags=["trailing-edge-devices"],
    operation_id="get_wing_trailing_edge_device",
)
async def get_wing_trailing_edge_device(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    cross_section_index: int = Path(...),
    db: Session = Depends(get_db),
) -> schemas.TrailingEdgeDeviceDetailSchema:
    """Returns the full TED with all geometry and spacing fields."""
    return _call_service(wing_service.get_trailing_edge_device, db, aeroplane_id, wing_name, cross_section_index)


@router.patch(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/trailing_edge_device",
    response_model=schemas.TrailingEdgeDeviceDetailSchema,
    status_code=status.HTTP_200_OK,
    tags=["trailing-edge-devices"],
    operation_id="patch_wing_trailing_edge_device",
)
async def patch_wing_trailing_edge_device(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    cross_section_index: int = Path(...),
    request: schemas.TrailingEdgeDevicePatchSchema = Body(...),
    db: Session = Depends(get_db),
) -> schemas.TrailingEdgeDeviceDetailSchema:
    """Upsert TED fields directly (not through the ControlSurface wrapper)."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    result = _call_service(wing_service.patch_trailing_edge_device, db, aeroplane_id, wing_name, cross_section_index, request)
    on_wing_changed(db, aeroplane_id, wing_name)
    return result


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/trailing_edge_device",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["trailing-edge-devices"],
    operation_id="delete_wing_trailing_edge_device",
)
async def delete_wing_trailing_edge_device(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    cross_section_index: int = Path(...),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Deletes the TED on the selected cross-section."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.delete_trailing_edge_device, db, aeroplane_id, wing_name, cross_section_index)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="deleted", operation="delete_wing_trailing_edge_device")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/trailing_edge_device/servo",
    response_model=schemas.ControlSurfaceServoDetailsSchema,
    status_code=status.HTTP_200_OK,
    tags=["trailing-edge-devices"],
    operation_id="get_wing_trailing_edge_servo",
)
async def get_wing_trailing_edge_servo(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    cross_section_index: int = Path(...),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceServoDetailsSchema:
    """Returns the servo assignment on the TED."""
    return _call_service(wing_service.get_trailing_edge_servo, db, aeroplane_id, wing_name, cross_section_index)


@router.patch(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/trailing_edge_device/servo",
    response_model=schemas.ControlSurfaceServoDetailsSchema,
    status_code=status.HTTP_200_OK,
    tags=["trailing-edge-devices"],
    operation_id="patch_wing_trailing_edge_servo",
)
async def patch_wing_trailing_edge_servo(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    cross_section_index: int = Path(...),
    request: schemas.ControlSurfaceServoDetailsPatchSchema = Body(...),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceServoDetailsSchema:
    """Assign or update the servo on the TED."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    result = _call_service(wing_service.patch_trailing_edge_servo, db, aeroplane_id, wing_name, cross_section_index, request)
    on_wing_changed(db, aeroplane_id, wing_name)
    return result


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/trailing_edge_device/servo",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["trailing-edge-devices"],
    operation_id="delete_wing_trailing_edge_servo",
)
async def delete_wing_trailing_edge_servo(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    cross_section_index: int = Path(...),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Remove the servo assignment from the TED."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(wing_service.delete_trailing_edge_servo, db, aeroplane_id, wing_name, cross_section_index)
    on_wing_changed(db, aeroplane_id, wing_name)
    return OperationStatusResponse(status="deleted", operation="delete_wing_trailing_edge_servo")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_model=schemas.ControlSurfaceSchema,
    status_code=status.HTTP_200_OK,
    tags=["control-surfaces"],
    operation_id="get_wing_cross_section_control_surface",
)
async def get_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceSchema:
    """Returns the control-surface analysis view projected from the canonical TED."""
    return _call_service(
        wing_service.get_control_surface,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
    )


@router.patch(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_model=schemas.ControlSurfaceSchema,
    status_code=status.HTTP_200_OK,
    tags=["control-surfaces"],
    operation_id="patch_wing_cross_section_control_surface",
)
async def patch_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    request: schemas.ControlSurfacePatchSchema = Body(..., description="Control-surface patch payload."),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceSchema:
    """Upserts the control-surface analysis view by patching the canonical TED."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    return _call_service(
        wing_service.patch_control_surface,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
        request,
    )


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["control-surfaces"],
    operation_id="delete_wing_cross_section_control_surface",
)
async def delete_aeroplane_wing_cross_section_control_surface(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Deletes the canonical TED from which control-surface data is projected."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(
        wing_service.delete_control_surface,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
    )
    return OperationStatusResponse(status="ok", operation="delete_wing_cross_section_control_surface")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details",
    response_model=schemas.ControlSurfaceCadDetailsSchema,
    status_code=status.HTTP_200_OK,
    tags=["control-surfaces"],
    operation_id="get_wing_cross_section_control_surface_cad_details",
)
async def get_aeroplane_wing_cross_section_control_surface_cad_details(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceCadDetailsSchema:
    """Returns the CAD detail extension of an existing control surface."""
    return _call_service(
        wing_service.get_control_surface_cad_details,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
    )


@router.patch(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details",
    response_model=schemas.ControlSurfaceCadDetailsSchema,
    status_code=status.HTTP_200_OK,
    tags=["control-surfaces"],
    operation_id="patch_wing_cross_section_control_surface_cad_details",
)
async def patch_aeroplane_wing_cross_section_control_surface_cad_details(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    request: schemas.ControlSurfaceCadDetailsPatchSchema = Body(
        ...,
        description="CAD detail patch payload that extends an existing control surface.",
    ),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceCadDetailsSchema:
    """Patches CAD details on an existing control surface without re-entering control-surface core fields."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    return _call_service(
        wing_service.patch_control_surface_cad_details,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
        request,
    )


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["control-surfaces"],
    operation_id="delete_wing_cross_section_control_surface_cad_details",
)
async def delete_aeroplane_wing_cross_section_control_surface_cad_details(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Removes CAD details while keeping the control-surface core definition."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(
        wing_service.delete_control_surface_cad_details,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
    )
    return OperationStatusResponse(status="ok", operation="delete_wing_cross_section_control_surface_cad_details")


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details/servo_details",
    response_model=schemas.ControlSurfaceServoDetailsSchema,
    status_code=status.HTTP_200_OK,
    tags=["servos"],
    operation_id="get_wing_cross_section_control_surface_cad_details_servo_details",
)
async def get_aeroplane_wing_cross_section_control_surface_cad_details_servo_details(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceServoDetailsSchema:
    """Returns servo details of the control-surface CAD extension."""
    return _call_service(
        wing_service.get_control_surface_cad_details_servo_details,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
    )


@router.patch(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details/servo_details",
    response_model=schemas.ControlSurfaceServoDetailsSchema,
    status_code=status.HTTP_200_OK,
    tags=["servos"],
    operation_id="patch_wing_cross_section_control_surface_cad_details_servo_details",
)
async def patch_aeroplane_wing_cross_section_control_surface_cad_details_servo_details(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    request: schemas.ControlSurfaceServoDetailsPatchSchema = Body(
        ...,
        description="Servo assignment payload (full Servo object or Servo ID reference).",
    ),
    db: Session = Depends(get_db),
) -> schemas.ControlSurfaceServoDetailsSchema:
    """Assigns or updates servo details of the control-surface CAD extension."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    return _call_service(
        wing_service.patch_control_surface_cad_details_servo_details,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
        request,
    )


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details/servo_details",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["servos"],
    operation_id="delete_wing_cross_section_control_surface_cad_details_servo_details",
)
async def delete_aeroplane_wing_cross_section_control_surface_cad_details_servo_details(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    cross_section_index: int = Path(..., description="The index of the cross section"),
    db: Session = Depends(get_db),
) -> OperationStatusResponse:
    """Deletes servo details from the control-surface CAD extension."""
    _assert_design_model(db, aeroplane_id, wing_name, "asb")
    _call_service(
        wing_service.delete_control_surface_cad_details_servo_details,
        db,
        aeroplane_id,
        wing_name,
        cross_section_index,
    )
    return OperationStatusResponse(
        status="ok",
        operation="delete_wing_cross_section_control_surface_cad_details_servo_details",
    )
