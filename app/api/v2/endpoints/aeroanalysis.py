import logging
import os
from urllib.parse import urljoin
from uuid import uuid4

from fastapi import Path, APIRouter, Body, Depends, Request, HTTPException
from fastapi import status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.db.session import get_db
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.api_responses import StaticUrlResponse
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.stability import StabilitySummaryResponse
from app.schemas.strip_forces import StripForcesResponse
from app.services import analysis_service
from app.services import stability_service
from app.settings import Settings, get_settings

router = APIRouter()
AeroPlaneID = UUID4

logger = logging.getLogger(__name__)


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


def _resolve_base_url(request: Request | None, settings: Settings) -> str:
    base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
    return base_url if base_url != "apiserver" else settings.base_url.rstrip("/")


def _save_png_and_get_static_url(
    aeroplane_id: UUID4,
    image_bytes: bytes,
    filename_prefix: str,
    request: Request | None,
    settings: Settings,
) -> str:
    content_dir = os.path.join("tmp", str(aeroplane_id), "png")
    os.makedirs(content_dir, exist_ok=True)
    filename = f"{filename_prefix}_{uuid4().hex}.png"
    file_path = os.path.join(content_dir, filename)
    with open(file_path, "wb") as file_handle:
        file_handle.write(image_bytes)

    base_url = _resolve_base_url(request, settings)
    return urljoin(base_url, f"/static/{aeroplane_id}/png/{filename}")


@router.post(
    "/aeroplanes/{aeroplane_id}/strip_forces",
    response_model=StripForcesResponse,
    tags=["analysis"],
    operation_id="get_airplane_strip_forces",
)
async def get_airplane_strip_forces(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point"),
    db: Session = Depends(get_db),
):
    """Run AVL analysis for the full airplane and return strip-force distributions for all surfaces."""
    try:
        return await analysis_service.analyze_airplane_strip_forces(
            db, aeroplane_id, operating_point
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/strip_forces",
    response_model=StripForcesResponse,
    tags=["analysis"],
    operation_id="get_wing_strip_forces",
)
async def get_wing_strip_forces(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point"),
    db: Session = Depends(get_db),
):
    """Run AVL analysis and return spanwise strip-force distributions."""
    try:
        return await analysis_service.analyze_wing_strip_forces(
            db, aeroplane_id, wing_name, operating_point
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}",
             tags=["analysis"],
             operation_id="analyze_wing_aerodynamics")
async def analyze_wing_post(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The ID of the wing"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point of the analysis"),
    analysis_tool: AnalysisToolUrlType = Path(..., description="The tool for aerodynamic analysis"),
    db: Session = Depends(get_db)
):
    """Analyze wings using aerobuildup, avl or vortex lattice and return the analysis results."""
    try:
        return await analysis_service.analyze_wing(
            db, aeroplane_id, wing_name, operating_point, analysis_tool
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes/{aeroplane_id}/stability_summary/{analysis_tool}",
             tags=["analysis"],
             operation_id="get_stability_summary",
             response_model=StabilitySummaryResponse)
async def get_stability_summary(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point for the analysis"),
    analysis_tool: AnalysisToolUrlType = Path(..., description="The analysis tool to use"),
    db: Session = Depends(get_db)
) -> StabilitySummaryResponse:
    """Get static stability summary (neutral point, static margin, stability derivatives)."""
    try:
        return await stability_service.get_stability_summary(
            db, aeroplane_id, operating_point, analysis_tool
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes/{aeroplane_id}/operating_point/{analysis_tool}",
             tags=["analysis"],
             operation_id="analyze_airplane_at_operating_point")
async def analyze_airplane_post(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point of the analysis"),
    analysis_tool: AnalysisToolUrlType = Path(..., description="The tool for aerodynamic analysis"),
    db: Session = Depends(get_db)
):
    """Analyze an airplane using aerobuildup, avl or vortex lattice and return the analysis results."""
    try:
        return await analysis_service.analyze_airplane(
            db, aeroplane_id, operating_point, analysis_tool
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes/{aeroplane_id}/streamlines",
             tags=["analysis"],
             operation_id="get_streamlines_json")
async def calculate_streamlines_json(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point"),
    db: Session = Depends(get_db),
):
    """Calculate VLM streamlines and return Plotly figure as JSON."""
    try:
        return await analysis_service.calculate_streamlines_json(
            db, aeroplane_id, operating_point,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.post("/aeroplanes/{aeroplane_id}/alpha_sweep",
             tags=["analysis"],
             operation_id="analyze_alpha_sweep")
async def analyze_airplane_alpha_sweep(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
    db: Session = Depends(get_db),
):
    """Performs an angle of attack sweep for a given airplane."""
    try:
        return await analysis_service.analyze_alpha_sweep(db, aeroplane_id, sweep_request)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc

@router.post("/aeroplanes/{aeroplane_id}/alpha_sweep/diagram",
             tags=["analysis"],
             response_model=StaticUrlResponse,
             operation_id="analyze_alpha_sweep_diagram")
async def analyze_airplane_alpha_sweep_diagram(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> StaticUrlResponse:
    """Performs an angle of attack sweep, saves diagram under tmp, and returns its static URL."""
    base_url = _resolve_base_url(request, settings)

    try:
        full_url = await analysis_service.get_alpha_sweep_diagram_url(
            db, aeroplane_id, sweep_request, base_url
        )
        return StaticUrlResponse(url=full_url)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc

@router.post("/aeroplanes/{aeroplane_id}/simple_sweep",
             tags=["analysis"],
             operation_id="analyze_parameter_sweep")
async def analyze_airplane_simple_sweep(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    sweep_request: SimpleSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
    db: Session = Depends(get_db),
):
    """Performs sweep through the given sweep variable for a given airplane."""
    try:
        return await analysis_service.analyze_simple_sweep(db, aeroplane_id, sweep_request)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


# Stub endpoints (stability_summary, lift_distribution, moment_distribution)
# were removed — they returned HTTP 200 + null, silently misleading clients.
# Follow-up implementation tasks: cad-modelling-service-c9r (stability),
# cad-modelling-service-7va (lift distribution),
# cad-modelling-service-120 (moment distribution).
#
# Duplicate three_view endpoints were removed in favour of the .../url
# variants below. The raw-bytes POST and GET forms were redundant — the
# .../url forms match the convention used by alpha_sweep/diagram and
# streamlines/three_view/url and are what clients should call.


@router.get("/aeroplanes/{aeroplane_id}/three_view/url",
         tags=["analysis"],
         response_model=StaticUrlResponse,
         operation_id="get_aeroplane_three_view_url")
async def get_aeroplane_three_view_url(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> StaticUrlResponse:
    """Generates a three-view diagram, saves it under tmp, and returns its static URL."""
    try:
        img_bytes = await analysis_service.get_three_view_image(db, aeroplane_id)
        image_url = _save_png_and_get_static_url(
            aeroplane_id=aeroplane_id,
            image_bytes=img_bytes,
            filename_prefix="three_view",
            request=request,
            settings=settings,
        )
        return StaticUrlResponse(url=image_url)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc

@router.post("/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url",
             tags=["analysis"],
             response_model=StaticUrlResponse,
             operation_id="get_streamlines_three_view_url")
async def get_streamlines_three_view_url(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point of the analysis"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> StaticUrlResponse:
    """Generates streamlines three-view image, saves it under tmp, and returns its static URL."""
    try:
        img_bytes = await analysis_service.get_streamlines_three_view_image(
            db, aeroplane_id, operating_point
        )
        image_url = _save_png_and_get_static_url(
            aeroplane_id=aeroplane_id,
            image_bytes=img_bytes,
            filename_prefix="streamlines_three_view",
            request=request,
            settings=settings,
        )
        return StaticUrlResponse(url=image_url)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc
