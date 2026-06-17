import logging
import os
from typing import Annotated, Literal
from urllib.parse import urljoin
from uuid import uuid4

from fastapi import Path, APIRouter, Body, Depends, Query, Request, HTTPException
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
from app.core.json_safe import NonFiniteSafeJSONResponse
from app.db.session import get_db
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.api_responses import StaticUrlResponse
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.section_geometry import SectionGeometryRequest, SectionGeometryResponse
from app.schemas.spar_sizing import SparSizingParams
from app.schemas.spanwise_loads import SpanwiseLoadsResponse, SpanwiseLoadsWithSizingResponse
from app.schemas.stability import StabilitySummaryResponse, StabilityResultRead
from app.schemas.strip_forces import StripForcesResponse
from app.services import analysis_service
from app.services import section_geometry_service
from app.services import stability_service
from app.services.wing_service import get_aeroplane_or_raise
from app.settings import Settings, get_settings

# Aero solvers (AeroBuildup) can emit non-finite coefficients (NaN / +/-Inf) for
# degenerate inputs; serialize via a response class that renders those as JSON
# null so the API never 500s on "Out of range float values" (gh#815).
router = APIRouter(default_response_class=NonFiniteSafeJSONResponse)
AeroPlaneID = UUID4

_DESC_AEROPLANE_ID = "The ID of the aeroplane"

logger = logging.getLogger(__name__)


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
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
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[OperatingPointSchema, Body(..., description="The operating point")],
    db: Annotated[Session, Depends(get_db)],
    solver: Annotated[
        Literal["vlm", "avl"],
        Query(description="Strip-force solver: 'vlm' (default, in-process) or 'avl' (subprocess)"),
    ] = "vlm",
):
    """Return strip-force distributions for all surfaces.

    Defaults to the in-process VortexLatticeMethod (gh-674); pass
    ``?solver=avl`` to use the AVL subprocess.
    """
    try:
        return await analysis_service.analyze_airplane_strip_forces(
            db, aeroplane_id, operating_point, solver=solver
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/strip_forces",
    response_model=StripForcesResponse,
    tags=["analysis"],
    operation_id="get_wing_strip_forces",
)
async def get_wing_strip_forces(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    wing_name: Annotated[str, Path(..., description="The name of the wing")],
    operating_point: Annotated[OperatingPointSchema, Body(..., description="The operating point")],
    db: Annotated[Session, Depends(get_db)],
    solver: Annotated[
        Literal["vlm", "avl"],
        Query(description="Strip-force solver: 'vlm' (default, in-process) or 'avl' (subprocess)"),
    ] = "vlm",
):
    """Return spanwise strip-force distributions for one wing.

    Defaults to the in-process VortexLatticeMethod (gh-674); pass
    ``?solver=avl`` to use the AVL subprocess.
    """
    try:
        return await analysis_service.analyze_wing_strip_forces(
            db, aeroplane_id, wing_name, operating_point, solver=solver
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}",
    tags=["analysis"],
    operation_id="analyze_wing_aerodynamics",
)
async def analyze_wing_post(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    wing_name: Annotated[str, Path(..., description="The ID of the wing")],
    operating_point: Annotated[
        OperatingPointSchema, Body(..., description="The operating point of the analysis")
    ],
    analysis_tool: Annotated[
        AnalysisToolUrlType, Path(..., description="The tool for aerodynamic analysis")
    ],
    db: Annotated[Session, Depends(get_db)],
):
    """Analyze wings using aerobuildup, avl or vortex lattice and return the analysis results."""
    try:
        return await analysis_service.analyze_wing(
            db, aeroplane_id, wing_name, operating_point, analysis_tool
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/stability_summary/{analysis_tool}",
    tags=["analysis"],
    operation_id="get_stability_summary",
)
async def get_stability_summary(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[
        OperatingPointSchema, Body(..., description="The operating point for the analysis")
    ],
    analysis_tool: Annotated[
        AnalysisToolUrlType, Path(..., description="The analysis tool to use")
    ],
    db: Annotated[Session, Depends(get_db)],
) -> StabilitySummaryResponse:
    """Get static stability summary (neutral point, static margin, stability derivatives)."""
    try:
        return await stability_service.get_stability_summary(
            db, aeroplane_id, operating_point, analysis_tool
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/stability", tags=["analysis"], operation_id="get_cached_stability"
)
async def get_cached_stability(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    db: Annotated[Session, Depends(get_db)],
) -> StabilityResultRead:
    """Get the last cached stability result without triggering a new analysis."""
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_id)
        result = stability_service.get_cached_stability(db, aeroplane.id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cached stability result. Run POST .../stability_summary/{tool} first.",
            )
        return result
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/operating_point/{analysis_tool}",
    tags=["analysis"],
    operation_id="analyze_airplane_at_operating_point",
)
async def analyze_airplane_post(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[
        OperatingPointSchema, Body(..., description="The operating point of the analysis")
    ],
    analysis_tool: Annotated[
        AnalysisToolUrlType, Path(..., description="The tool for aerodynamic analysis")
    ],
    db: Annotated[Session, Depends(get_db)],
):
    """Analyze an airplane using aerobuildup, avl or vortex lattice and return the analysis results."""
    try:
        return await analysis_service.analyze_airplane(
            db, aeroplane_id, operating_point, analysis_tool
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/streamlines", tags=["analysis"], operation_id="get_streamlines_json"
)
async def calculate_streamlines_json(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[OperatingPointSchema, Body(..., description="The operating point")],
    db: Annotated[Session, Depends(get_db)],
):
    """Calculate VLM streamlines and return Plotly figure as JSON."""
    try:
        return await analysis_service.calculate_streamlines_json(
            db,
            aeroplane_id,
            operating_point,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/alpha_sweep", tags=["analysis"], operation_id="analyze_alpha_sweep"
)
async def analyze_airplane_alpha_sweep(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    sweep_request: Annotated[
        AlphaSweepRequest, Body(..., description="Sweep definitions and flight conditions")
    ],
    db: Annotated[Session, Depends(get_db)],
):
    """Performs an angle of attack sweep for a given airplane."""
    try:
        return await analysis_service.analyze_alpha_sweep(db, aeroplane_id, sweep_request)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/alpha_sweep/diagram",
    tags=["analysis"],
    operation_id="analyze_alpha_sweep_diagram",
)
async def analyze_airplane_alpha_sweep_diagram(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    sweep_request: Annotated[
        AlphaSweepRequest, Body(..., description="Sweep definitions and flight conditions")
    ],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request = None,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/simple_sweep",
    tags=["analysis"],
    operation_id="analyze_parameter_sweep",
)
async def analyze_airplane_simple_sweep(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    sweep_request: Annotated[
        SimpleSweepRequest, Body(..., description="Sweep definitions and flight conditions")
    ],
    db: Annotated[Session, Depends(get_db)],
):
    """Performs sweep through the given sweep variable for a given airplane."""
    try:
        return await analysis_service.analyze_simple_sweep(db, aeroplane_id, sweep_request)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


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


@router.get(
    "/aeroplanes/{aeroplane_id}/three_view/url",
    tags=["analysis"],
    operation_id="get_aeroplane_three_view_url",
)
async def get_aeroplane_three_view_url(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request = None,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url",
    tags=["analysis"],
    operation_id="get_streamlines_three_view_url",
)
async def get_streamlines_three_view_url(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[
        OperatingPointSchema, Body(..., description="The operating point of the analysis")
    ],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request = None,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/spanwise_loads",
    response_model=SpanwiseLoadsResponse,
    tags=["analysis"],
    operation_id="get_airplane_spanwise_loads",
)
async def get_airplane_spanwise_loads(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[OperatingPointSchema, Body(..., description="The operating point")],
    db: Annotated[Session, Depends(get_db)],
    solver: Annotated[
        Literal["vlm", "avl"],
        Query(description="Strip-force solver: 'vlm' (default, in-process) or 'avl' (subprocess)"),
    ] = "vlm",
) -> SpanwiseLoadsResponse:
    """Return spanwise shear and bending-moment distributions for all surfaces (gh-1002).

    Integrates the Trefftz-Plane strip forces into running shear V(y) and bending
    moment M(y) referenced to the wing root.  The root bending moment is the
    headline value for carbon-spar sizing on 3D-printed wings.

    Pure post-processing over the strip-forces computation — no new aerodynamic
    model.  Uses the same VLM/AVL solver as ``strip_forces``.
    """
    try:
        return await analysis_service.analyze_airplane_spanwise_loads(
            db, aeroplane_id, operating_point, solver=solver
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/section-geometry",
    response_model=SectionGeometryResponse,
    tags=["analysis"],
    operation_id="get_airplane_section_geometry",
)
def get_airplane_section_geometry(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    request: Annotated[
        SectionGeometryRequest,
        Body(..., description="Section-geometry sampling request (all fields optional)"),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> SectionGeometryResponse:
    """Sample the built section geometry of a wing (gh-1021).

    Slices the real lofted CAD solid at parametric ``(y/span, x/c)`` locations
    and returns thickness, upper/lower surface heights, and mid-height
    (spar-placement reference) in **metres**. When the sample arrays are
    omitted, an evenly spaced default grid is used. Set ``per_segment=true`` to
    additionally receive a per-segment grid.

    Returns 422 when section geometry is unavailable on this platform (cadquery
    excluded on ``linux/aarch64``).
    """
    try:
        return section_geometry_service.compute_section_geometry(db, aeroplane_id, request)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/spanwise_loads_with_sizing",
    response_model=SpanwiseLoadsWithSizingResponse,
    tags=["analysis"],
    operation_id="get_airplane_spanwise_loads_with_spar_sizing",
)
async def get_airplane_spanwise_loads_with_sizing(
    aeroplane_id: Annotated[AeroPlaneID, Path(..., description=_DESC_AEROPLANE_ID)],
    operating_point: Annotated[OperatingPointSchema, Body(..., description="The operating point")],
    db: Annotated[Session, Depends(get_db)],
    solver: Annotated[
        Literal["vlm", "avl"],
        Query(description="Strip-force solver: 'vlm' (default, in-process) or 'avl' (subprocess)"),
    ] = "vlm",
    material_id: Annotated[
        int | None, Query(description="Material component ID for spar sizing")
    ] = None,
    shape: Annotated[
        Literal["tube", "rod", "rectangular", "capped"],
        Query(description="Spar cross-section shape"),
    ] = "tube",
    safety_factor_j: Annotated[
        float, Query(gt=0, description="Safety factor j (default 1.5)")
    ] = 1.5,
    packing_factor: Annotated[
        float, Query(gt=0, le=1.0, description="Packing factor (default 0.8)")
    ] = 0.8,
    sigma_allow_mpa_override: Annotated[
        float | None,
        Query(gt=0, description="Override σ_allow (MPa). If omitted, material value used."),
    ] = None,
    cap_width_mm: Annotated[
        float | None, Query(gt=0, description="Cap/flange width b (mm) — required for shape=capped")
    ] = None,
) -> SpanwiseLoadsWithSizingResponse:
    """Return spanwise loads + spar-sizing results for all surfaces (gh-1008).

    Extends the spanwise-loads endpoint with per-surface spar dimensioning.
    The spar is sized at each strip station using the design bending moment
    M_design = |M(y)| · g_limit · j, where g_limit comes from the aeroplane's
    design assumptions (fallback: 3.0 with a warning).

    Shapes: tube (Da=outer → solve wall), rod (solve d), rectangular (h=outer → solve b),
    capped (H=outer, cap_width_mm=b → solve gurt thickness).

    The material must be a Component of type 'material' with
    allowable_bending_stress_mpa set.
    """
    if material_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="material_id is required for spar sizing",
        )
    spar_params = SparSizingParams(
        material_id=material_id,
        shape=shape,
        safety_factor_j=safety_factor_j,
        packing_factor=packing_factor,
        sigma_allow_mpa_override=sigma_allow_mpa_override,
        cap_width_mm=cap_width_mm,
    )
    try:
        return await analysis_service.analyze_airplane_spanwise_loads(
            db, aeroplane_id, operating_point, solver=solver, spar_params=spar_params
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {exc}"
        ) from exc
