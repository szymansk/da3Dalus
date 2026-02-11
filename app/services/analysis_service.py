"""
Analysis Service - Business logic for aerodynamic analysis operations.

This module contains the core logic for aerodynamic analysis,
separated from HTTP concerns for better testability and reusability.
"""

import io
import logging
from typing import List, Optional, Tuple, Any

import numpy as np
import matplotlib.pyplot as plt
from aerosandbox import Airplane
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.utils import analyse_aerodynamics, compile_four_view_figure, save_content_and_get_static_url
from app.converters.model_schema_converters import aeroplaneSchemaToAsbAirplane_async
from app.core.exceptions import NotFoundError, InternalError
from app.db.exceptions import NotFoundInDbException
from app.db.repository import get_wing_by_name_and_aeroplane_id, get_aeroplane_by_id
from app.schemas import AeroplaneSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema

logger = logging.getLogger(__name__)


async def get_aeroplane_schema_or_raise(db: Session, aeroplane_uuid) -> AeroplaneSchema:
    """
    Get an aeroplane schema by UUID.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        return await get_aeroplane_by_id(aeroplane_uuid, db)
    except NotFoundInDbException as e:
        raise NotFoundError(
            message=str(e),
            details={"aeroplane_id": str(aeroplane_uuid)}
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


async def get_wing_schema_or_raise(
    db: Session,
    aeroplane_uuid,
    wing_name: str
) -> AeroplaneSchema:
    """
    Get an aeroplane schema with only the specified wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        return await get_wing_by_name_and_aeroplane_id(aeroplane_uuid, wing_name, db)
    except NotFoundInDbException as e:
        raise NotFoundError(
            message=str(e),
            details={"aeroplane_id": str(aeroplane_uuid), "wing_name": wing_name}
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing: {e}")
        raise InternalError(message=f"Database error: {e}")


async def analyze_wing(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType
) -> Any:
    """
    Analyze a single wing using the specified analysis tool.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_wing_schema_or_raise(db, aeroplane_uuid, wing_name)
    
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        asb_airplane.xyz_ref = operating_point.xyz_ref
        asb_airplane.wings = [w for w in asb_airplane.wings if w.name == wing_name]
        asb_airplane.fuselages = []
        
        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as e:
        logger.error(f"Error analyzing wing: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_airplane(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType
) -> Any:
    """
    Analyze a complete airplane using the specified analysis tool.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as e:
        logger.error(f"Error analyzing airplane: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def calculate_streamlines_html(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    base_url: str
) -> str:
    """
    Calculate streamlines and save as HTML.
    
    Returns:
        str: URL to the saved HTML file.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, figure = await analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            operating_point,
            asb_airplane,
            draw_streamlines=True
        )
        
        content = figure.to_html()
        filename = f"streamlines_{operating_point.velocity}_{operating_point.alpha}_{operating_point.beta}.html"
        
        full_url = await save_content_and_get_static_url(
            aeroplane_uuid, base_url, content, "html", filename
        )
        return full_url
    except Exception as e:
        logger.error(f"Error calculating streamlines: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_alpha_sweep(
    db: Session,
    aeroplane_uuid,
    sweep_request: AlphaSweepRequest
) -> Any:
    """
    Perform an angle of attack sweep.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        
        operating_point = OperatingPointSchema(
            altitude=sweep_request.altitude,
            velocity=sweep_request.velocity,
            alpha=np.linspace(
                start=sweep_request.alpha_start,
                stop=sweep_request.alpha_end,
                num=sweep_request.alpha_num
            ),
            beta=sweep_request.beta,
            p=sweep_request.p,
            q=sweep_request.q,
            r=sweep_request.r,
            xyz_ref=sweep_request.xyz_ref
        )
        
        result, _ = await analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane
        )
        return result
    except Exception as e:
        logger.error(f"Error in alpha sweep: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_simple_sweep(
    db: Session,
    aeroplane_uuid,
    sweep_request: SimpleSweepRequest
) -> Any:
    """
    Perform a parameter sweep.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
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
            current_val = operating_point.__dict__[sweep_request.sweep_var]
            operating_point.__dict__[sweep_request.sweep_var] = np.linspace(
                start=current_val,
                stop=current_val + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        elif sweep_request.sweep_var == 'x':
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref, 0,
                start=operating_point.xyz_ref[0],
                stop=operating_point.xyz_ref[0] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        elif sweep_request.sweep_var == 'y':
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref, 1,
                start=operating_point.xyz_ref[1],
                stop=operating_point.xyz_ref[1] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        elif sweep_request.sweep_var == 'z':
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref, 2,
                start=operating_point.xyz_ref[2],
                stop=operating_point.xyz_ref[2] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        else:
            from app.core.exceptions import ValidationError
            raise ValidationError(
                message=f"Invalid sweep variable: {sweep_request.sweep_var}",
                details={"valid_vars": ['alpha', 'velocity', 'beta', 'p', 'q', 'r', 'altitude', 'x', 'y', 'z']}
            )
        
        result, _ = await analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane
        )
        return result
    except Exception as e:
        logger.error(f"Error in simple sweep: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def get_streamlines_three_view_image(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema
) -> bytes:
    """
    Generate a four-view diagram with streamlines as PNG.
    
    Returns:
        bytes: PNG image data.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        
        _, figure = await analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            operating_point,
            asb_airplane,
            draw_streamlines=True,
            backend='plotly'
        )
        
        fig = await compile_four_view_figure(figure)
        img_bytes = fig.to_image(format="png", width=1000, height=1000, scale=2)
        return img_bytes
    except Exception as e:
        logger.error(f"Error generating streamlines view: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def get_three_view_image(db: Session, aeroplane_uuid) -> bytes:
    """
    Generate a three-view diagram as PNG.
    
    Returns:
        bytes: PNG image data.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        
        fig = plt.figure(figsize=(10, 10))
        asb_airplane.draw_three_view(show=False)
        
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=300, bbox_inches='tight')
        img_bytes.seek(0)
        plt.close(fig)
        
        return img_bytes.getvalue()
    except Exception as e:
        logger.error(f"Error generating three-view: {e}")
        raise InternalError(message=f"Error generating diagram: {e}")
