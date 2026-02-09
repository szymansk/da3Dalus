import http
import logging
import io
from typing import List

import numpy as np
import matplotlib.pyplot as plt

from aerosandbox import Airplane
from fastapi import Path, APIRouter, Body, HTTPException, Depends, Request
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, PlainTextResponse, Response

from app.api.utils import analyse_aerodynamics, compile_four_view_figure, save_content_and_get_static_url
from app.converters.model_schema_converters import aeroplaneSchemaToAsbAirplane_async
from app.db.exceptions import NotFoundInDbException
from app.db.repository import get_wing_by_name_and_aeroplane_id, get_aeroplane_by_id
from app.db.session import get_db
from app.schemas import AeroplaneSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema

from app.settings import Settings, get_settings
from cad_designer.airplane.aircraft_topology.models.analysis_model import AnalysisModel

router = APIRouter()
AeroPlaneID = UUID4

logger = logging.getLogger(__name__)


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}",
             tags=["analysis"],
             operation_id="analyze_wing_aerodynamics",)
async def analyze_wing_post(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                            wing_name: str = Path(..., description="The ID of the wing"),
                            operating_point: OperatingPointSchema = Body(...,
                                                                         description="The operating point of the analysis"),
                            analysis_tool: AnalysisToolUrlType = Path(...,
                                                                      description="The tool for aerodynamic analysis (AeroBuildup (best), AVL, or Vortex Lattice)"),
                            db: Session = Depends(get_db)):
    """
    Analyze wings using aerobuildup, avl or vortex lattice and return the analysis results.

    Args:
        aeroplane_id: The ID of the aeroplane
        wing_name: The name of the wing to analyze
        analysis_tool: The analysis tool to use (AVL, AeroBuildup, or Vortex Lattice)

    Returns:
        AnalysisModel: The AVL analysis results
    """
    try:
        plane_schema = await get_wing_by_name_and_aeroplane_id(aeroplane_id, wing_name, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        asb_airplane.xyz_ref = operating_point.xyz_ref
        asb_airplane.wings = [w for w in asb_airplane.wings if w.name == wing_name]
        asb_airplane.fuselages = []  # We onl analyze a single wing, so no fuselages are needed

        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )


@router.post("/aeroplanes/{aeroplane_id}/operating_point/{analysis_tool}",
             tags=["analysis"],
             operation_id="analyze_airplane_at_operating_point")
async def analyze_airplane_post(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                                operating_point: OperatingPointSchema = Body(...,
                                                                             description="The operating point of the analysis"),
                                analysis_tool: AnalysisToolUrlType = Path(...,
                                                                          description="The tool for aerodynamic analysis (AeroBuildup (best), AVL, or Vortex Lattice)"),
                                db: Session = Depends(get_db)):
    """
    Analyze an airplane using aerobuildup, avl or vortex lattice and return the analysis results.

    Args:
        aeroplane_id: The ID of the aeroplane
        analysis_tool: The analysis tool to use (AVL, AeroBuildup, or Vortex Lattice)

    Returns:
        AnalysisModel: The AVL analysis results
    """
    try:
        plane_schema: AeroplaneSchema = await get_aeroplane_by_id(aeroplane_id, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )

@router.post("/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/html_view",
             tags=["analysis"],
             response_class=PlainTextResponse,
             operation_id="get_streamlines_as_html",
             )
async def calculate_streamlines(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                                operating_point: OperatingPointSchema = Body(...,
                                                                             description="The operating point of the analysis"),
                                db: Session = Depends(get_db),
                                request: Request = None,
                                settings: Settings = Depends(get_settings)) -> PlainTextResponse:
    """
    Calculates streamlines for an airplane using the Vortex Lattice Method (VLM).

    This endpoint performs aerodynamic analysis for the given airplane and operating point,
    saves the resulting streamlines visualization as an HTML file in tmp/<airplane_id>/html,
    and returns the full URL (including base URL) to the served HTML file.

    Args:
        aeroplane_id (AeroPlaneID): The ID of the aeroplane to analyze.
        operating_point (OperatingPointSchema): The operating point containing flight conditions.
        request (Request): The FastAPI request object, used to get the base URL.

    Returns:
        JSONResponse: A json containing the full URL (including base URL) to the served HTML file.

    Raises:
        HTTPException: If the aeroplane or wing is not found, or if there is a database or unexpected error.
    """
    try:
        plane_schema: AeroplaneSchema = await get_aeroplane_by_id(aeroplane_id, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, figure = await analyse_aerodynamics(AnalysisToolUrlType.VORTEX_LATTICE,
                                                    operating_point,
                                                    asb_airplane,
                                                    draw_streamlines=True)
        content = figure.to_html()
        filename = f"streamlines_{operating_point.velocity}_{operating_point.alpha}_{operating_point.beta}.html"
        content_type = "html"
        base_url = str(request.base_url).rstrip('/')
        base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip('/')

        full_url = await save_content_and_get_static_url(aeroplane_id, base_url, content, content_type, filename)

        return full_url

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )


@router.post("/aeroplanes/{aeroplane_id}/alpha_sweep",
             tags=["analysis"],
             operation_id="analyze_alpha_sweep")
async def analyze_airplane_alpha_sweep(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
        db: Session = Depends(get_db),
):
    """
    Performs an angle of attack sweep for a given airplane.
    """
    try:
        plane_schema: AeroplaneSchema = await get_aeroplane_by_id(aeroplane_id, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)

        operating_point = OperatingPointSchema(
            altitude=sweep_request.altitude,
            velocity=sweep_request.velocity,
            alpha=np.linspace(start=sweep_request.alpha_start,
                              stop=sweep_request.alpha_end,
                              num=sweep_request.alpha_num),
            beta=sweep_request.beta,
            p=sweep_request.p,
            q=sweep_request.q,
            r=sweep_request.r,
            xyz_ref=sweep_request.xyz_ref
        )

        result, _ = await analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane)
        return result

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )


@router.post("/aeroplanes/{aeroplane_id}/simple_sweep",
             tags=["analysis"],
             operation_id="analyze_parameter_sweep")
async def analyze_airplane_simple_sweep(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        sweep_request: SimpleSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
        db: Session = Depends(get_db),
):
    """
    Performs sweep through the given sweep variable for a given airplane.
    """
    try:
        plane_schema: AeroplaneSchema = await get_aeroplane_by_id(aeroplane_id, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)

        operating_point = OperatingPointSchema(
            name=f"sweep over {sweep_request.sweep_var}",
            description=None,
            altitude=sweep_request.altitude,
            velocity=sweep_request.velocity,
            alpha=sweep_request.alpha,
            beta=sweep_request.beta,
            p=sweep_request.p,
            q=sweep_request.q,
            r=sweep_request.r,
            xyz_ref=sweep_request.xyz_ref
        )

        def vary_index(
                values: List[float],
                index: int,
                start: float,
                stop: float,
                num: int
        ) -> List[List[float]]:
            return [
                [val if i != index else v for i, val in enumerate(values)]
                for v in np.linspace(start, stop, num)
            ]

        if sweep_request.sweep_var in ['alpha', 'velocity', 'beta', 'p', 'q', 'r', 'altitude']:
            operating_point.__dict__[sweep_request.sweep_var] = (
                np.linspace(start=operating_point.__dict__[sweep_request.sweep_var],
                            stop=operating_point.__dict__[
                                     sweep_request.sweep_var] + sweep_request.step_size * sweep_request.num,
                            num=sweep_request.num))

        elif sweep_request.sweep_var == 'x':
            operating_point.xyz_ref = vary_index(operating_point.xyz_ref,
                       0,
                       start=operating_point.xyz_ref[0],
                       stop=operating_point.xyz_ref[0] + sweep_request.step_size * sweep_request.num,
                       num=sweep_request.num)
        elif sweep_request.sweep_var == 'y':
            operating_point.xyz_ref = vary_index(operating_point.xyz_ref,
                       1,
                       start=operating_point.xyz_ref[1],
                       stop=operating_point.xyz_ref[1] + sweep_request.step_size * sweep_request.num,
                       num=sweep_request.num)
        elif sweep_request.sweep_var == 'z':
            operating_point.xyz_ref = vary_index(operating_point.xyz_ref,
                       2,
                       start=operating_point.xyz_ref[2],
                       stop=operating_point.xyz_ref[2] + sweep_request.sweep_step * sweep_request.sweep_num,
                       num=sweep_request.sweep_num)
        else:
            raise ValueError(
                f"Invalid sweep variable: {sweep_request.sweep_var}. Must be one of: alpha, velocity, beta, p, q, r, altitude, x, y, z.")

        result, _ = await analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane)
        return result

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )


@router.get("/aeroplanes/{aeroplane_id}/stability_summary",
         operation_id="get_aeroplane_stability_summary")
async def get_stability_summary(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db),
):
    """
    Returns a summary of static stability parameters.
    """
    pass


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}/lift_distribution",
         operation_id="get_wing_lift_distribution")
async def get_lift_distribution(
        aeroplane_id: AeroPlaneID = Path(...),
        wing_name: str = Path(...),
        db: Session = Depends(get_db),
):
    """
    Returns the spanwise lift distribution for a given wing.
    """
    pass


@router.get("/aeroplanes/{aeroplane_id}/moment_distribution",
         operation_id="get_aeroplane_moment_distribution")
async def get_moment_distribution(
        aeroplane_id: AeroPlaneID = Path(...),
        db: Session = Depends(get_db),
):
    """
    Returns the pitching moment distribution along the longitudinal axis.
    """
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
    """
    Generates a four-view diagram of the aeroplane based on aerodynamic analysis and returns it as a PNG image.

    The four views are:
    1. Side view (y-axis)
    2. Front view (x-axis)
    3. Top view (z-axis)
    4. Overview from top left

    Args:
        aeroplane_id (AeroPlaneID): The ID of the aeroplane to analyze.
        operating_point (OperatingPointSchema): The operating point containing flight conditions.
        analysis_tool (AnalysisToolUrlType): The tool for aerodynamic analysis.

    Returns:
        Response: A PNG image with all four views in a 2x2 grid.

    Raises:
        HTTPException: If the aeroplane is not found, or if there is a database or unexpected error.
    """
    try:
        plane_schema: AeroplaneSchema = await get_aeroplane_by_id(aeroplane_id, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    try:
        # Convert to aerosandbox Airplane
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)

        # Perform aerodynamic analysis
        _, figure = await analyse_aerodynamics(AnalysisToolUrlType.VORTEX_LATTICE,
                                               operating_point, asb_airplane,
                                               draw_streamlines=True,
                                               backend='plotly')

        fig = await compile_four_view_figure(figure)

        # Convert the figure to a PNG image
        img_bytes = fig.to_image(format="png", width=1000, height=1000, scale=2)

        # Return the PNG image
        return Response(content=img_bytes, media_type="image/png")

    except Exception as err:
        logger.error(f"Error generating four-view diagram: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )


@router.get("/aeroplanes/{aeroplane_id}/three_view",
         response_class=Response,
         operation_id="get_aeroplane_three_view",
            responses={200: {"content": {"image/png": {}}}})
async def get_aeroplane_three_view(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db),
):
    """
    Generates a three-view diagram of the aeroplane and returns it as a PNG image.

    This endpoint loads the aeroplane from the database, converts it to an aerosandbox Airplane object,
    generates a three-view diagram using the draw_three_view method, and returns the diagram as a PNG image.

    Args:
        aeroplane_id (AeroPlaneID): The ID of the aeroplane to visualize.

    Returns:
        Response: A PNG image of the three-view diagram.

    Raises:
        HTTPException: If the aeroplane is not found, or if there is a database or unexpected error.
    """
    try:
        plane_schema: AeroplaneSchema = await get_aeroplane_by_id(aeroplane_id, db)
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except NotFoundInDbException as not_found_error:
        raise HTTPException(status_code=404, detail=str(not_found_error))
    except Exception as e:
        logger.error(f"Unexpected error when getting aeroplane: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    try:
        # Convert to aerosandbox Airplane
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)

        # Generate the three-view diagram
        # The draw_three_view method returns the axes, but we need to get the figure
        fig = plt.figure(figsize=(10, 10))
        axs = asb_airplane.draw_three_view(show=False)

        # Convert the figure to a PNG image
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=300, bbox_inches='tight')
        img_bytes.seek(0)

        # Close the figure to free memory
        plt.close(fig)

        # Return the PNG image
        return Response(content=img_bytes.getvalue(), media_type="image/png")

    except Exception as err:
        logger.error(f"Error generating three-view diagram: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
