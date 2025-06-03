import http
import logging
import os.path
from typing import List

import numpy as np
from aerosandbox import Airplane
from fastapi import Path, APIRouter, Body, HTTPException, Depends
from plotly.graph_objs import Figure
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.responses import HTMLResponse

from app.api.v2.endpoints.aeroplane import AeroPlaneID
from app.converters.model_schema_converters import aeroplaneModelToAeroplaneSchema_async, \
    aeroplaneSchemaToAsbAirplane_async
from app.db.session import get_db
from app.models import AeroplaneModel, WingModel, WingXSecModel
from app.models.aeroplanemodel import FuselageModel
from app.schemas import AeroplaneSchema, AsbWingSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema

import aerosandbox as asb

from cad_designer.airplane.aircraft_topology.models.analysis_model import AnalysisModel

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}",
             tags=["mcon"],
             operation_id="analyze_wing_aerodynamics_at_operating_point",)
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
        try:
            # Load the parent aeroplane
            plane: AeroplaneModel = (db.query(AeroplaneModel)
                                     .options(joinedload(AeroplaneModel.wings)
                                              .joinedload(WingModel.x_secs)
                                              .joinedload(WingXSecModel.control_surface))
                                     .options(joinedload(AeroplaneModel.fuselages)
                                              .joinedload(FuselageModel.x_secs))
                                     .filter(AeroplaneModel.uuid == aeroplane_id).first())
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            plane_schema: AeroplaneSchema = await aeroplaneModelToAeroplaneSchema_async(plane)

            # Find the wing belonging to this aeroplane
            wing: AsbWingSchema = next((w for w in plane_schema.wings.values() if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

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
             tags=["mcp"],
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
        try:
            # Load the parent aeroplane
            plane: AeroplaneModel = (db.query(AeroplaneModel)
                                     .options(joinedload(AeroplaneModel.wings)
                                              .joinedload(WingModel.x_secs)
                                              .joinedload(WingXSecModel.control_surface))
                                     .options(joinedload(AeroplaneModel.fuselages)
                                              .joinedload(FuselageModel.x_secs))
                                     .filter(AeroplaneModel.uuid == aeroplane_id).first())
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            plane_schema: AeroplaneSchema = await aeroplaneModelToAeroplaneSchema_async(plane)
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )

@router.post("/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines",
             response_class=HTMLResponse)
async def calculate_streamlines(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                                operating_point: OperatingPointSchema = Body(...,
                                                                             description="The operating point of the analysis"),
                                db: Session = Depends(get_db)):
    """
    Calculates streamlines for an airplane using the Vortex Lattice Method (VLM).

    This endpoint performs aerodynamic analysis for the given airplane and operating point,
    and returns the resulting streamlines as an HTML response.

    Args:
        aeroplane_id (AeroPlaneID): The ID of the aeroplane to analyze.
        operating_point (OperatingPointSchema): The operating point containing flight conditions.

    Returns:
        HTMLResponse: An HTML representation of the streamlines visualization.

    Raises:
        HTTPException: If the aeroplane or wing is not found, or if there is a database or unexpected error.
    """
    try:
        try:
            # Load the parent aeroplane
            plane: AeroplaneModel = (db.query(AeroplaneModel)
                                     .options(joinedload(AeroplaneModel.wings)
                                              .joinedload(WingModel.x_secs)
                                              .joinedload(WingXSecModel.control_surface))
                                     .options(joinedload(AeroplaneModel.fuselages)
                                              .joinedload(FuselageModel.x_secs))
                                     .filter(AeroplaneModel.uuid == aeroplane_id).first())
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            plane_schema: AeroplaneSchema = await aeroplaneModelToAeroplaneSchema_async(plane)
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, figure = await analyse_aerodynamics(AnalysisToolUrlType.VORTEX_LATTICE,
                                                    operating_point,
                                                    asb_airplane,
                                                    draw_streamlines=True)
        html_content = figure.to_html()

        return HTMLResponse(content=html_content)

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )

async def analyse_aerodynamics(analysis_tool: AnalysisToolUrlType,
                               operating_point: OperatingPointSchema,
                               asb_airplane: Airplane,
                               draw_streamlines: bool = False) -> (AnalysisModel, Figure):
    # Create the atmosphere
    atmosphere = asb.Atmosphere(
        altitude=operating_point.altitude
    )
    # Create the operating point
    op_point = asb.OperatingPoint(
        velocity=operating_point.velocity if isinstance(operating_point.velocity, float) else np.array(operating_point.velocity),
        alpha=operating_point.alpha if isinstance(operating_point.alpha, float) else np.array(operating_point.alpha),
        beta=operating_point.beta if isinstance(operating_point.beta, float) else np.array(operating_point.beta),
        p=operating_point.p if isinstance(operating_point.p, float) else np.array(operating_point.p),
        q=operating_point.q if isinstance(operating_point.q, float) else np.array(operating_point.q),
        r=operating_point.r if isinstance(operating_point.r, float) else np.array(operating_point.r),
        atmosphere=atmosphere
    )

    asb_airplane.xyz_ref = operating_point.xyz_ref
    if analysis_tool == AnalysisToolUrlType.AVL:
        # Run the AVL analysis
        avl = asb.AVL(
            airplane=asb_airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref
        )
        if (isinstance(operating_point.alpha, (list, tuple, np.ndarray)) or
                isinstance(operating_point.beta, (list, tuple, np.ndarray))):
            raise ValueError(
                "AVL analysis does not support parameter sweeps. Please use AeroBuildup or Vortex Lattice for that.")

        # Get the results
        avl_results = avl.run()
        return AnalysisModel.from_avl_dict(avl_results), None
    elif analysis_tool == AnalysisToolUrlType.AEROBUILDUP:
        abu = asb.AeroBuildup(
            airplane=asb_airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref
        )

        # Get the results
        abu_results = abu.run_with_stability_derivatives()
        return AnalysisModel.from_abu_dict(
            abu_results,
            asb_airplan=asb_airplane,
            methode='aerobuildup',
        ), None
    elif analysis_tool == AnalysisToolUrlType.VORTEX_LATTICE:
        vlm = asb.VortexLatticeMethod(
            airplane=asb_airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref
        )

        # Get the results
        vlm.verbose = True
        vlm_results = vlm.run_with_stability_derivatives()
        if draw_streamlines:
            figure = vlm.draw(show=False, backend='plotly')
        else:
            figure = None

        return AnalysisModel.from_abu_dict(
            vlm_results,
            asb_airplan=asb_airplane,
            operating_point=op_point,
            methode='vortex_lattice',
        ), figure
    else:
        raise ValueError(
            f"Invalid analysis tool: {analysis_tool}. Must be one of: AVL, AeroBuildup, or Vortex Lattice.")

@router.post("/aeroplanes/{aeroplane_id}/alpha_sweep",
             tags=["mcp"],
             operation_id="analyze_airplane_perform_alpha_sweep")
async def analyze_airplane_alpha_sweep(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
        db: Session = Depends(get_db),
):
    """
    Performs an angle of attack sweep for a given airplane.
    """
    try:
        try:
            # Load the parent aeroplane
            plane: AeroplaneModel = (db.query(AeroplaneModel)
                                     .options(joinedload(AeroplaneModel.wings)
                                              .joinedload(WingModel.x_secs)
                                              .joinedload(WingXSecModel.control_surface))
                                     .options(joinedload(AeroplaneModel.fuselages)
                                              .joinedload(FuselageModel.x_secs))
                                     .filter(AeroplaneModel.uuid == aeroplane_id).first())
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            plane_schema: AeroplaneSchema = await aeroplaneModelToAeroplaneSchema_async(plane)
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

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
             tags=["mcp"],
             operation_id="analyze_airplane_perform_parameter_sweep")
async def analyze_airplane_simple_sweep(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        sweep_request: SimpleSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
        db: Session = Depends(get_db),
):
    """
    Performs sweep through the given sweep variable for a given airplane.
    """
    try:
        try:
            # Load the parent aeroplane
            plane: AeroplaneModel = (db.query(AeroplaneModel)
                                     .options(joinedload(AeroplaneModel.wings)
                                              .joinedload(WingModel.x_secs)
                                              .joinedload(WingXSecModel.control_surface))
                                     .options(joinedload(AeroplaneModel.fuselages)
                                              .joinedload(FuselageModel.x_secs))
                                     .filter(AeroplaneModel.uuid == aeroplane_id).first())
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            plane_schema: AeroplaneSchema = await aeroplaneModelToAeroplaneSchema_async(plane)
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

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


@router.get("/aeroplanes/{aeroplane_id}/stability_summary")
async def get_stability_summary(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db),
):
    """
    Returns a summary of static stability parameters.
    """
    pass


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}/lift_distribution")
async def get_lift_distribution(
        aeroplane_id: AeroPlaneID = Path(...),
        wing_name: str = Path(...),
        db: Session = Depends(get_db),
):
    """
    Returns the spanwise lift distribution for a given wing.
    """
    pass


@router.get("/aeroplanes/{aeroplane_id}/moment_distribution")
async def get_moment_distribution(
        aeroplane_id: AeroPlaneID = Path(...),
        db: Session = Depends(get_db),
):
    """
    Returns the pitching moment distribution along the longitudinal axis.
    """
    pass
