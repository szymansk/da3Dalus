import logging
from pathlib import Path as _FsPath
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi import status
from fastapi.responses import FileResponse
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings

from app import schemas
from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ServiceException,
    ValidationError,
)
from app.db.session import get_db
from app.services import fuselage_service

logger = logging.getLogger(__name__)

router = APIRouter()

AeroPlaneID = UUID4


class OperationStatusResponse(BaseModel):
    status: str
    operation: str


def _raise_http_from_domain(exc: ServiceException) -> None:
    """Translate domain exceptions into HTTPException for the response."""
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


def _call_service(func, *args, **kwargs):
    """Call a service function, converting domain exceptions to HTTP."""
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


# Handle an aeroplane fuselages
@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages",
    status_code=status.HTTP_200_OK,
    tags=["fuselages"],
    operation_id="get_aeroplane_fuselages",
    responses={
        404: {"description": "Aeroplane not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_aeroplane_fuselages(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> List[str]:
    """
    Returns a list of aeroplane's fuselage names.
    """
    return _call_service(fuselage_service.list_fuselage_names, db, aeroplane_id)


# Handle an aeroplane fuselage
@router.put(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
    status_code=status.HTTP_201_CREATED,
    response_model=OperationStatusResponse,
    tags=["fuselages"],
    operation_id="create_aeroplane_fuselage",
    responses={
        404: {"description": "Aeroplane not found"},
        409: {"description": "Fuselage name conflict"},
        500: {"description": "Internal server error"},
    },
)
async def create_aeroplane_fuselage(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    request: Annotated[schemas.FuselageSchema, Body(..., description="The new fuselage data")],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Create the fuselage for the aeroplane.
    """
    _call_service(fuselage_service.create_fuselage, db, aeroplane_id, fuselage_name, request)
    return OperationStatusResponse(status="created", operation="create_aeroplane_fuselage")


@router.post(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["fuselages"],
    operation_id="update_aeroplane_fuselage",
    responses={
        404: {"description": "Aeroplane or fuselage not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_aeroplane_fuselage(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    request: Annotated[schemas.FuselageSchema, Body(..., description="The new fuselage data")],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Overwrite an existing fuselage with the data in the request.
    """
    _call_service(fuselage_service.update_fuselage, db, aeroplane_id, fuselage_name, request)
    return OperationStatusResponse(status="ok", operation="update_aeroplane_fuselage")


@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
    tags=["fuselages"],
    operation_id="get_aeroplane_fuselage",
    responses={
        404: {"description": "Aeroplane or fuselage not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_aeroplane_fuselage(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    db: Annotated[Session, Depends(get_db)],
) -> schemas.FuselageSchema:
    """
    Returns the aeroplane fuselage.
    """
    return _call_service(fuselage_service.get_fuselage, db, aeroplane_id, fuselage_name)


@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/step",
    tags=["fuselages"],
    operation_id="get_aeroplane_fuselage_step",
    responses={
        200: {
            "content": {"model/step": {}},
            "description": "STEP file bytes",
        },
        404: {"description": "Aeroplane / fuselage / STEP file not found"},
    },
)
async def get_aeroplane_fuselage_step(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The fuselage name")],
    db: Annotated[Session, Depends(get_db)],
):
    """Download the per-geom STEP file (gh-729).

    Only available when the fuselage was imported from an OpenVSP
    ``.vsp3`` file and the STEP export succeeded at import time.
    Returns 404 for CAD-created fuselages or when the file is
    missing from disk.
    """
    # Resolve the schema first — that yields a 404 for unknown
    # fuselage names with a structured error body.
    fuselage = _call_service(fuselage_service.get_fuselage, db, aeroplane_id, fuselage_name)
    if not getattr(fuselage, "step_path", None):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Fuselage {fuselage_name!r} has no STEP file "
                "(only OpenVSP-imported fuselages do)."
            ),
        )
    full_path = _FsPath(settings.ARTIFACTS_BASE_DIR) / fuselage.step_path
    # Containment check — defence in depth against a manipulated
    # ``step_path`` somehow escaping the artifacts root.
    artifacts_root = _FsPath(settings.ARTIFACTS_BASE_DIR).resolve()
    resolved = full_path.resolve()
    if artifacts_root not in resolved.parents and resolved != artifacts_root:
        logger.warning(
            "STEP path %r escapes artifacts root — refusing to serve.",
            fuselage.step_path,
        )
        raise HTTPException(status_code=404, detail="STEP file unavailable.")
    if not resolved.exists():
        raise HTTPException(
            status_code=404,
            detail=f"STEP file for fuselage {fuselage_name!r} is missing on disk.",
        )
    return FileResponse(
        path=str(resolved),
        media_type="model/step",
        filename=f"{fuselage_name}.stp",
    )


@router.delete(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["fuselages"],
    operation_id="delete_aeroplane_fuselage",
    responses={
        404: {"description": "Aeroplane or fuselage not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_aeroplane_fuselage(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete a fuselage.
    """
    _call_service(fuselage_service.delete_fuselage, db, aeroplane_id, fuselage_name)
    return OperationStatusResponse(status="ok", operation="delete_aeroplane_fuselage")


#########################################
# Handle an aeroplane fuselage cross sections
#########################################
@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections",
    status_code=status.HTTP_200_OK,
    tags=["fuselage-cross-sections"],
    operation_id="get_fuselage_cross_sections",
    responses={
        404: {"description": "Aeroplane or fuselage not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_aeroplane_fuselage_cross_sections(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    db: Annotated[Session, Depends(get_db)],
) -> List[schemas.FuselageXSecSuperEllipseSchema]:
    """
    Returns the fuselage's cross-sections as a list.
    """
    return _call_service(
        fuselage_service.get_fuselage_cross_sections, db, aeroplane_id, fuselage_name
    )


@router.delete(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections",
    status_code=status.HTTP_200_OK,
    response_model=OperationStatusResponse,
    tags=["fuselage-cross-sections"],
    operation_id="delete_all_fuselage_cross_sections",
    responses={
        404: {"description": "Aeroplane or fuselage not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_aeroplane_fuselage_cross_sections(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete all cross-sections of a fuselage.
    """
    _call_service(fuselage_service.delete_all_cross_sections, db, aeroplane_id, fuselage_name)
    return OperationStatusResponse(status="ok", operation="delete_all_fuselage_cross_sections")


@router.get(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    status_code=status.HTTP_200_OK,
    tags=["fuselage-cross-sections"],
    operation_id="get_fuselage_cross_section",
    responses={
        404: {"description": "Aeroplane, fuselage, or cross-section not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_aeroplane_fuselage_cross_section(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    cross_section_index: Annotated[int, Path(..., description="The index of the cross section")],
    db: Annotated[Session, Depends(get_db)],
) -> schemas.FuselageXSecSuperEllipseSchema:
    """
    Returns the aeroplane fuselage cross-section at the specified index.
    """
    return _call_service(
        fuselage_service.get_cross_section,
        db,
        aeroplane_id,
        fuselage_name,
        cross_section_index,
    )


@router.post(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["fuselage-cross-sections"],
    operation_id="create_fuselage_cross_section",
    responses={
        404: {"description": "Aeroplane or fuselage not found"},
        500: {"description": "Internal server error"},
    },
)
async def create_aeroplane_fuselage_cross_section(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    cross_section_index: Annotated[
        int,
        Path(
            ...,
            description="The index where it will be spliced into the list of cross sections. (-1 is the end of the list, 0 is the start of the list)",
        ),
    ],
    request: Annotated[
        schemas.FuselageXSecSuperEllipseSchema,
        Body(..., description="Fuselage cross section request"),
    ],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Creates a new cross-section for the fuselage and splice it into the list of cross-sections.
    """
    _call_service(
        fuselage_service.create_cross_section,
        db,
        aeroplane_id,
        fuselage_name,
        cross_section_index,
        request,
    )
    return OperationStatusResponse(status="created", operation="create_fuselage_cross_section")


@router.put(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    response_model=OperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["fuselage-cross-sections"],
    operation_id="update_fuselage_cross_section",
    responses={
        404: {"description": "Aeroplane, fuselage, or cross-section not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_aeroplane_fuselage_cross_section(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    cross_section_index: Annotated[int, Path(..., description="The index of the cross section")],
    request: Annotated[schemas.FuselageXSecSuperEllipseSchema, Body(...)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Updates the cross-section for the fuselage.
    """
    _call_service(
        fuselage_service.update_cross_section,
        db,
        aeroplane_id,
        fuselage_name,
        cross_section_index,
        request,
    )
    return OperationStatusResponse(status="ok", operation="update_fuselage_cross_section")


@router.delete(
    "/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections/{cross_section_index}",
    status_code=status.HTTP_200_OK,
    response_model=OperationStatusResponse,
    tags=["fuselage-cross-sections"],
    operation_id="delete_fuselage_cross_section",
    responses={
        404: {"description": "Aeroplane, fuselage, or cross-section not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_aeroplane_fuselage_cross_section(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description="The ID of the aeroplane")],
    fuselage_name: Annotated[str, Path(..., description="The ID of the fuselage")],
    cross_section_index: Annotated[int, Path(..., description="The index of the cross section")],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete a cross-section.
    """
    _call_service(
        fuselage_service.delete_cross_section,
        db,
        aeroplane_id,
        fuselage_name,
        cross_section_index,
    )
    return OperationStatusResponse(status="ok", operation="delete_fuselage_cross_section")
