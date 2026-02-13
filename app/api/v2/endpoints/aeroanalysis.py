import logging
import os
from urllib.parse import urljoin
from uuid import uuid4

from fastapi import Path, APIRouter, Body, Depends, Request
from pydantic import UUID4
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, PlainTextResponse, Response

from app.db.session import get_db
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.services import analysis_service
from app.settings import Settings, get_settings

router = APIRouter()
AeroPlaneID = UUID4

logger = logging.getLogger(__name__)


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
    return await analysis_service.analyze_wing(
        db, aeroplane_id, wing_name, operating_point, analysis_tool
    )


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
    return await analysis_service.analyze_airplane(
        db, aeroplane_id, operating_point, analysis_tool
    )


@router.post("/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/html_view",
             tags=["analysis"],
             response_class=PlainTextResponse,
             operation_id="get_streamlines_as_html")
async def calculate_streamlines(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point of the analysis"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings)
) -> PlainTextResponse:
    """
    Calculates streamlines for an airplane using the Vortex Lattice Method (VLM).
    Returns the full URL to the served HTML file.
    """
    base_url = str(request.base_url).rstrip('/')
    base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip('/')
    
    full_url = await analysis_service.calculate_streamlines_html(
        db, aeroplane_id, operating_point, base_url
    )
    return full_url


@router.post("/aeroplanes/{aeroplane_id}/alpha_sweep",
             tags=["analysis"],
             operation_id="analyze_alpha_sweep")
async def analyze_airplane_alpha_sweep(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
    db: Session = Depends(get_db),
):
    """Performs an angle of attack sweep for a given airplane."""
    return await analysis_service.analyze_alpha_sweep(db, aeroplane_id, sweep_request)

@router.post("/aeroplanes/{aeroplane_id}/alpha_sweep/diagram",
             tags=["analysis"],
             response_class=JSONResponse,
             operation_id="analyze_alpha_sweep_diagram")
async def analyze_airplane_alpha_sweep_diagram(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Performs an angle of attack sweep, saves diagram under tmp, and returns its static URL."""
    base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
    base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip("/")

    full_url = await analysis_service.get_alpha_sweep_diagram_url(
        db, aeroplane_id, sweep_request, base_url
    )
    return JSONResponse(content={"url": full_url})

@router.post("/aeroplanes/{aeroplane_id}/simple_sweep",
             tags=["analysis"],
             operation_id="analyze_parameter_sweep")
async def analyze_airplane_simple_sweep(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    sweep_request: SimpleSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
    db: Session = Depends(get_db),
):
    """Performs sweep through the given sweep variable for a given airplane."""
    return await analysis_service.analyze_simple_sweep(db, aeroplane_id, sweep_request)


@router.get("/aeroplanes/{aeroplane_id}/stability_summary",
         operation_id="get_aeroplane_stability_summary")
async def get_stability_summary(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db),
):
    """Returns a summary of static stability parameters."""
    pass


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}/lift_distribution",
         operation_id="get_wing_lift_distribution")
async def get_lift_distribution(
    aeroplane_id: AeroPlaneID = Path(...),
    wing_name: str = Path(...),
    db: Session = Depends(get_db),
):
    """Returns the spanwise lift distribution for a given wing."""
    pass

#TODO: implement an enpoint that returns a diagramm of the spanwise lift distribution for a given wing over a front view of the wing. The diagramm should be returned as a static URL to a PNG image. The service layer should generate the diagramm using matplotlib, save it under tmp and return the URL to the saved image. The endpoint should be a GET endpoint with the path /aeroplanes/{aeroplane_id}/wings/{wing_name}/lift_distribution/diagram and should return a JSON response with the URL to the diagramm.


@router.get("/aeroplanes/{aeroplane_id}/moment_distribution",
         operation_id="get_aeroplane_moment_distribution")
async def get_moment_distribution(
    aeroplane_id: AeroPlaneID = Path(...),
    db: Session = Depends(get_db),
):
    """Returns the pitching moment distribution along the longitudinal axis."""
    #TODO: Implement this endpoint in the service layer and return the moment distribution as a list of values along the longitudinal axis in a semantic meaningfull JSON response.
    pass

@router.post("/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view",
         response_class=Response,
         tags=["analysis"],
         operation_id="get_streamlines_three_view")
async def get_streamlines_three_view(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point of the analysis"),
    db: Session = Depends(get_db),
):
    """Generates a four-view diagram of the aeroplane based on aerodynamic analysis and returns it as a PNG image."""
    img_bytes = await analysis_service.get_streamlines_three_view_image(
        db, aeroplane_id, operating_point
    )
    return Response(content=img_bytes, media_type="image/png")


@router.get("/aeroplanes/{aeroplane_id}/three_view",
         response_class=Response,
         operation_id="get_aeroplane_three_view",
         responses={200: {"content": {"image/png": {}}}})
async def get_aeroplane_three_view(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db),
):
    """Generates a three-view diagram of the aeroplane and returns it as a PNG image."""
    img_bytes = await analysis_service.get_three_view_image(db, aeroplane_id)
    return Response(content=img_bytes, media_type="image/png")


@router.get("/aeroplanes/{aeroplane_id}/three_view/url",
         tags=["analysis"],
         response_class=JSONResponse,
         operation_id="get_aeroplane_three_view_url")
async def get_aeroplane_three_view_url(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Generates a three-view diagram, saves it under tmp, and returns its static URL."""
    img_bytes = await analysis_service.get_three_view_image(db, aeroplane_id)

    content_dir = os.path.join("tmp", str(aeroplane_id), "png")
    os.makedirs(content_dir, exist_ok=True)
    filename = f"three_view_{uuid4().hex}.png"
    file_path = os.path.join(content_dir, filename)
    with open(file_path, "wb") as f:
        f.write(img_bytes)

    base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
    base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip("/")

    return JSONResponse(content={"url": urljoin(base_url, f"/static/{aeroplane_id}/png/{filename}")})

@router.post("/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url",
             tags=["analysis"],
             response_class=JSONResponse,
             operation_id="get_streamlines_three_view_url")
async def get_streamlines_three_view_url(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    operating_point: OperatingPointSchema = Body(..., description="The operating point of the analysis"),
    db: Session = Depends(get_db),
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Generates streamlines three-view image, saves it under tmp, and returns its static URL."""
    img_bytes = await analysis_service.get_streamlines_three_view_image(
        db, aeroplane_id, operating_point
    )

    content_dir = os.path.join("tmp", str(aeroplane_id), "png")
    os.makedirs(content_dir, exist_ok=True)
    filename = f"streamlines_three_view_{uuid4().hex}.png"
    file_path = os.path.join(content_dir, filename)
    with open(file_path, "wb") as f:
        f.write(img_bytes)

    base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
    base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip("/")

    return JSONResponse(content={"url": urljoin(base_url, f"/static/{aeroplane_id}/png/{filename}")})
