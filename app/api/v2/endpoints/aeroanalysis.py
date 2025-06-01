import http
import logging
import os.path

from aerosandbox import Airplane
from fastapi import Path, APIRouter, Body, HTTPException, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.api.v2.endpoints.aeroplane import AeroPlaneID
from app.converters.model_schema_converters import aeroplaneModelToAeroplaneSchema, aeroplaneSchemaToAsbAirplane
from app.db.session import get_db
from app.models import AeroplaneModel, WingModel, WingXSecModel
from app.models.aeroplanemodel import FuselageModel
from app.schemas import AeroplaneSchema, AsbWingSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema

import aerosandbox as asb

from cad_designer.airplane.aircraft_topology.models.analysis_model import AnalysisModel

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}")
async def analyze_wing_post(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                            wing_name: str = Path(..., description="The ID of the wing"),
                            operating_point: OperatingPointSchema = Body(...,
                                                                         description="The operating point of the analysis"),
                            analysis_tool: AnalysisToolUrlType = Path(..., description="The tool for aerodynamic analysis (AeroBuildup (best), AVL, or Vortex Lattice)"),
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
        #aeroplane_id_str = str(aeroplane_id)
        # if tasks.get(aeroplane_id_str) is not None:
        #     raise HTTPException(
        #         status_code=http.HTTPStatus.LOCKED,
        #         detail={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}",
        #                 "status": "other task is running"}
        #     )
        #with tasks_lock:
        #    tasks[aeroplane_id_str] = {'status': 'PENDING'}

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

            plane_schema:AeroplaneSchema = await aeroplaneModelToAeroplaneSchema(plane)

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

        # Create the atmosphere
        atmosphere = asb.Atmosphere(
            altitude=operating_point.altitude
        )

        # Create the operating point
        op_point = asb.OperatingPoint(
            velocity=operating_point.velocity,
            alpha=operating_point.alpha,
            beta=operating_point.beta,
            p=operating_point.p,
            q=operating_point.q,
            r=operating_point.r,
            atmosphere=atmosphere
        )

        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane(plane_schema=plane_schema)
        asb_airplane.xyz_ref = operating_point.xyz_ref
        asb_airplane.wings = [w for w in asb_airplane.wings if w.name == wing_name]
        asb_airplane.fuselages = [] # We onl analyze a single wing, so no fuselages are needed

        if analysis_tool == AnalysisToolUrlType.AVL:
            # Run the AVL analysis
            avl = asb.AVL(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref
            )

            # Get the results
            avl_results = avl.run()
            analysis_model = AnalysisModel.from_avl_dict(avl_results)
        elif analysis_tool == AnalysisToolUrlType.AEROBUILDUP:
            abu = asb.AeroBuildup(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref
            )

            # Get the results
            abu_results = abu.run_with_stability_derivatives()
            analysis_model = AnalysisModel.from_abu_dict(
                abu_results,
                asb_airplan=asb_airplane,
                methode='aerobuildup',
            )
        elif analysis_tool == AnalysisToolUrlType.VORTEX_LATTICE:
            vlm = asb.VortexLatticeMethod(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref
            )

            # Get the results
            vlm_results = vlm.run_with_stability_derivatives()
            analysis_model = AnalysisModel.from_abu_dict(
                vlm_results,
                asb_airplan=asb_airplane,
                operation_point=op_point,
                methode='vortex_lattice',
            )
            pass

        # Return the results
        return analysis_model

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        #with tasks_lock:
        #    if aeroplane_id_str in tasks:
        #        del tasks[aeroplane_id_str]
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )

@router.post("/aeroplanes/{aeroplane_id}/{analysis_tool}")
async def analyze_airplane_post(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                            operating_point: OperatingPointSchema = Body(...,
                                                                         description="The operating point of the analysis"),
                            analysis_tool: AnalysisToolUrlType = Path(..., description="The tool for aerodynamic analysis (AeroBuildup (best), AVL, or Vortex Lattice)"),
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

            plane_schema:AeroplaneSchema = await aeroplaneModelToAeroplaneSchema(plane)
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when getting aeroplane wing: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

        # Create the atmosphere
        atmosphere = asb.Atmosphere(
            altitude=operating_point.altitude
        )

        # Create the operating point
        op_point = asb.OperatingPoint(
            velocity=operating_point.velocity,
            alpha=operating_point.alpha,
            beta=operating_point.beta,
            p=operating_point.p,
            q=operating_point.q,
            r=operating_point.r,
            atmosphere=atmosphere
        )

        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane(plane_schema=plane_schema)
        asb_airplane.xyz_ref = operating_point.xyz_ref

        if analysis_tool == AnalysisToolUrlType.AVL:
            # Run the AVL analysis
            avl = asb.AVL(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref
            )

            # Get the results
            avl_results = avl.run()
            analysis_model = AnalysisModel.from_avl_dict(avl_results)
        elif analysis_tool == AnalysisToolUrlType.AEROBUILDUP:
            abu = asb.AeroBuildup(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref
            )

            # Get the results
            abu_results = abu.run_with_stability_derivatives()
            analysis_model = AnalysisModel.from_abu_dict(
                abu_results,
                asb_airplan=asb_airplane,
                methode='aerobuildup',
            )
        elif analysis_tool == AnalysisToolUrlType.VORTEX_LATTICE:
            vlm = asb.VortexLatticeMethod(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref
            )

            # Get the results
            vlm_results = vlm.run_with_stability_derivatives()

            analysis_model = AnalysisModel.from_abu_dict(
                vlm_results,
                asb_airplan=asb_airplane,
                methode='vortex_lattice',
            )
            pass

        # Return the results
        return analysis_model

    except Exception as err:
        logger.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )



@router.post("/aeroplanes/{aeroplane_id}/{analysis_tool}/alpha_sweep")
async def analyze_airplane_alpha_sweep(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        analysis_tool: AnalysisToolUrlType = AnalysisToolUrlType.AVL,
        sweep_request: AlphaSweepRequest = Body(..., description="Sweep definitions and flight conditions"),
        db: Session = Depends(get_db),
):
    """
    Performs an angle of attack sweep for a given airplane.
    """
    pass


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
