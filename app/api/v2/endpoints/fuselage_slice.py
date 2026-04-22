"""Endpoint for slicing a STEP file into a fuselage definition."""

from typing import Annotated
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.exceptions import InternalError, ServiceException, ValidationError
from app.schemas.fuselage_slice import FuselageSliceResponse
from app.services import fuselage_slice_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fuselages", tags=["fuselages"])


@router.post(
    "/slice",
    status_code=status.HTTP_200_OK,
    operation_id="slice_step_to_fuselage",
    summary="Slice a STEP file into superellipse cross-sections (asb.Fuselage format)"
)
async def slice_step_to_fuselage(
    file: Annotated[UploadFile, File(..., description="STEP file (.step or .stp)")],
    number_of_slices: Annotated[int, Form(ge=2, le=500, description="Number of cross-section slices")] = 50,
    points_per_slice: Annotated[int, Form(ge=10, le=200, description="Points per wire discretization")] = 30,
    slice_axis: Annotated[str, Form(description="Slice axis: 'x', 'y', 'z', or 'auto' (longest axis)")] = "auto",
    fuselage_name: Annotated[str, Form(description="Name for the resulting fuselage")] = "Imported Fuselage",
) -> FuselageSliceResponse:
    """Upload a STEP file, slice it along the fuselage longitudinal axis,
    fit symmetric superellipses to each cross-section, and return a
    FuselageSchema JSON with fidelity metrics.

    The result can be saved via `PUT /aeroplanes/{id}/fuselages/{name}`.
    """
    if slice_axis not in ("x", "y", "z", "auto"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid slice_axis: {slice_axis}. Must be 'x', 'y', 'z', or 'auto'.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    try:
        return svc.slice_step_file(
            file_content=content,
            filename=file.filename or "upload.step",
            number_of_slices=number_of_slices,
            points_per_slice=points_per_slice,
            slice_axis=slice_axis,
            fuselage_name=fuselage_name,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    except InternalError as exc:
        if "not available on this platform" in str(exc.message):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=exc.message) from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
    except ServiceException as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
