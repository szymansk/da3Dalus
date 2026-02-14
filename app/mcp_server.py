"""Native FastMCP tool server for the da3Dalus CAD modelling service."""

from __future__ import annotations

import base64
import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable

from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, Response
from fastmcp import FastMCP
from pydantic import UUID4

from app import schemas
from app.api.v2.endpoints import aeroanalysis
from app.api.v2.endpoints import cad
from app.api.v2.endpoints import flight_profiles
from app.api.v2.endpoints import operating_points
from app.api.v2.endpoints.aeroplane import base as aeroplane_base
from app.api.v2.endpoints.aeroplane import fuselages as aeroplane_fuselages
from app.api.v2.endpoints.aeroplane import wings as aeroplane_wings
from app.db.session import SessionLocal
from app.schemas.AeroplaneRequest import (
    AeroplaneMassRequest,
    AeroplaneSettings,
    AlphaSweepRequest,
    AnalysisToolUrlType,
    CreatorUrlType,
    ExporterUrlType,
    SimpleSweepRequest,
)
from app.schemas.aeroanalysisschema import (
    GenerateOperatingPointSetRequest,
    OperatingPointSchema,
    OperatingPointSetSchema,
    StoredOperatingPointCreate,
)
from app.schemas.flight_profile import FlightProfileType, RCFlightProfileCreate, RCFlightProfileUpdate
from app.settings import get_settings


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]


TOOL_SPECS: list[MCPToolSpec] = []


def mcp_tool(name: str, description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register metadata for a native FastMCP tool function."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        TOOL_SPECS.append(MCPToolSpec(name=name, description=description, handler=fn))
        return fn

    return decorator


async def _call_endpoint(endpoint_fn: Callable[..., Any], **kwargs: Any) -> Any:
    """Call a FastAPI endpoint function with a managed database session."""
    with SessionLocal() as db:
        endpoint_parameters = inspect.signature(endpoint_fn).parameters
        call_kwargs = dict(kwargs)
        if "db" in endpoint_parameters:
            call_kwargs["db"] = db

        result = endpoint_fn(**call_kwargs)
        if inspect.isawaitable(result):
            result = await result
        return _normalize_result(result)


def _normalize_result(result: Any) -> Any:
    """Convert FastAPI-specific return types into MCP-friendly JSON values."""
    if result is None:
        return {"status": "ok"}

    if isinstance(result, JSONResponse):
        if not result.body:
            return {"status_code": result.status_code}
        return json.loads(result.body.decode("utf-8"))

    if isinstance(result, FileResponse):
        return {
            "file_path": str(result.path),
            "filename": result.filename,
            "media_type": result.media_type,
        }

    if isinstance(result, Response):
        if result.media_type and result.media_type.startswith("image/"):
            return {
                "media_type": result.media_type,
                "encoding": "base64",
                "data": base64.b64encode(result.body).decode("ascii"),
            }

        if result.body:
            if result.media_type == "application/json":
                return json.loads(result.body.decode("utf-8"))
            return {
                "media_type": result.media_type,
                "content": result.body.decode("utf-8", errors="replace"),
            }

        return {"status_code": result.status_code}

    return jsonable_encoder(result)


# Aeroplane base tools
@mcp_tool(
    name="get_all_aeroplanes",
    description="List all aeroplanes with IDs and timestamps, sorted alphabetically by name.",
)
async def get_all_aeroplanes_tool() -> Any:
    return await _call_endpoint(aeroplane_base.get_aeroplanes)


@mcp_tool(
    name="create_aeroplane",
    description="Create a new aeroplane by name and return its UUID.",
)
async def create_aeroplane_tool(name: str) -> Any:
    return await _call_endpoint(aeroplane_base.create_aeroplane, name=name)


@mcp_tool(
    name="get_aeroplane_by_id",
    description="Get the full aeroplane definition for a specific aeroplane UUID.",
)
async def get_aeroplane_by_id_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(aeroplane_base.get_aeroplane, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="delete_aeroplane",
    description="Delete an aeroplane and all associated data by aeroplane UUID.",
)
async def delete_aeroplane_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(aeroplane_base.delete_aeroplane, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="get_aeroplane_total_mass",
    description="Get the stored total mass for an aeroplane in kilograms.",
)
async def get_aeroplane_total_mass_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(aeroplane_base.get_aeroplane_total_mass_in_kg, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="set_aeroplane_total_mass",
    description="Create or overwrite the total aeroplane mass in kilograms.",
)
async def set_aeroplane_total_mass_tool(aeroplane_id: UUID4, total_mass_kg: AeroplaneMassRequest) -> Any:
    return await _call_endpoint(
        aeroplane_base.create_aeroplane_total_mass_kg,
        aeroplane_id=aeroplane_id,
        total_mass_kg=total_mass_kg,
    )


# Wing tools
@mcp_tool(
    name="get_aeroplane_wings",
    description="List all wing names for a specific aeroplane UUID.",
)
async def get_aeroplane_wings_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(aeroplane_wings.get_aeroplane_wings, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="create_aeroplane_wing",
    description="Create a new wing for an aeroplane using a complete wing definition.",
)
async def create_aeroplane_wing_tool(aeroplane_id: UUID4, wing_name: str, request: schemas.AsbWingSchema) -> Any:
    return await _call_endpoint(
        aeroplane_wings.create_aeroplane_wing,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        request=request,
    )


@mcp_tool(
    name="update_aeroplane_wing",
    description="Overwrite an existing wing with a full replacement wing definition.",
)
async def update_aeroplane_wing_tool(aeroplane_id: UUID4, wing_name: str, request: schemas.AsbWingSchema) -> Any:
    return await _call_endpoint(
        aeroplane_wings.update_aeroplane_wing,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        request=request,
    )


@mcp_tool(
    name="get_aeroplane_wing",
    description="Get one wing definition by aeroplane UUID and wing name.",
)
async def get_aeroplane_wing_tool(aeroplane_id: UUID4, wing_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_wings.get_aeroplane_wing,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
    )


@mcp_tool(
    name="delete_aeroplane_wing",
    description="Delete one wing from an aeroplane by wing name.",
)
async def delete_aeroplane_wing_tool(aeroplane_id: UUID4, wing_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_wings.delete_aeroplane_wing,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
    )


@mcp_tool(
    name="get_wing_cross_sections",
    description="Get all wing cross-sections for a wing as an ordered list.",
)
async def get_wing_cross_sections_tool(aeroplane_id: UUID4, wing_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_wings.get_aeroplane_wing_cross_sections,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
    )


@mcp_tool(
    name="delete_all_wing_cross_sections",
    description="Delete all cross-sections from a wing.",
)
async def delete_all_wing_cross_sections_tool(aeroplane_id: UUID4, wing_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_wings.delete_aeroplane_wing_cross_sections,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
    )


@mcp_tool(
    name="get_wing_cross_section",
    description="Get one wing cross-section by index.",
)
async def get_wing_cross_section_tool(aeroplane_id: UUID4, wing_name: str, cross_section_index: int) -> Any:
    return await _call_endpoint(
        aeroplane_wings.get_aeroplane_wing_cross_section,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
    )


@mcp_tool(
    name="create_wing_cross_section",
    description="Insert a new wing cross-section at a given index (-1 appends at the end).",
)
async def create_wing_cross_section_tool(
    aeroplane_id: UUID4,
    wing_name: str,
    cross_section_index: int,
    request: schemas.WingXSecSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_wings.create_aeroplane_wing_cross_section,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
        request=request,
    )


@mcp_tool(
    name="update_wing_cross_section",
    description="Replace an existing wing cross-section at a specific index.",
)
async def update_wing_cross_section_tool(
    aeroplane_id: UUID4,
    wing_name: str,
    cross_section_index: int,
    request: schemas.WingXSecSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_wings.update_aeroplane_wing_cross_section,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
        request=request,
    )


@mcp_tool(
    name="delete_wing_cross_section",
    description="Delete one wing cross-section by index.",
)
async def delete_wing_cross_section_tool(aeroplane_id: UUID4, wing_name: str, cross_section_index: int) -> Any:
    return await _call_endpoint(
        aeroplane_wings.delete_aeroplane_wing_cross_section,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
    )


@mcp_tool(
    name="get_control_surface",
    description="Get the control-surface settings for one wing cross-section.",
)
async def get_control_surface_tool(aeroplane_id: UUID4, wing_name: str, cross_section_index: int) -> Any:
    return await _call_endpoint(
        aeroplane_wings.get_aeroplane_wing_cross_section_control_surface,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
    )


@mcp_tool(
    name="upsert_control_surface",
    description="Create or update the control-surface settings for one wing cross-section.",
)
async def upsert_control_surface_tool(
    aeroplane_id: UUID4,
    wing_name: str,
    cross_section_index: int,
    request: schemas.ControlSurfaceSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_wings.create_and_update_aeroplane_wing_cross_section_control_surface,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
        request=request,
    )


@mcp_tool(
    name="delete_control_surface",
    description="Delete the control-surface settings from one wing cross-section.",
)
async def delete_control_surface_tool(aeroplane_id: UUID4, wing_name: str, cross_section_index: int) -> Any:
    return await _call_endpoint(
        aeroplane_wings.delete_aeroplane_wing_cross_section_control_surface,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        cross_section_index=cross_section_index,
    )


# Fuselage tools
@mcp_tool(
    name="get_aeroplane_fuselages",
    description="List all fuselage names for a specific aeroplane UUID.",
)
async def get_aeroplane_fuselages_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(aeroplane_fuselages.get_aeroplane_fuselages, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="create_aeroplane_fuselage",
    description="Create a new fuselage for an aeroplane using a complete fuselage definition.",
)
async def create_aeroplane_fuselage_tool(
    aeroplane_id: UUID4,
    fuselage_name: str,
    request: schemas.FuselageSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.create_aeroplane_fuselage,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
        request=request,
    )


@mcp_tool(
    name="update_aeroplane_fuselage",
    description="Overwrite an existing fuselage with a full replacement fuselage definition.",
)
async def update_aeroplane_fuselage_tool(
    aeroplane_id: UUID4,
    fuselage_name: str,
    request: schemas.FuselageSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.update_aeroplane_fuselage,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
        request=request,
    )


@mcp_tool(
    name="get_aeroplane_fuselage",
    description="Get one fuselage definition by aeroplane UUID and fuselage name.",
)
async def get_aeroplane_fuselage_tool(aeroplane_id: UUID4, fuselage_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.get_aeroplane_fuselage,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
    )


@mcp_tool(
    name="delete_aeroplane_fuselage",
    description="Delete one fuselage from an aeroplane by fuselage name.",
)
async def delete_aeroplane_fuselage_tool(aeroplane_id: UUID4, fuselage_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.delete_aeroplane_fuselage,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
    )


@mcp_tool(
    name="get_fuselage_cross_sections",
    description="Get all fuselage cross-sections for one fuselage.",
)
async def get_fuselage_cross_sections_tool(aeroplane_id: UUID4, fuselage_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.get_aeroplane_fuselage_cross_sections,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
    )


@mcp_tool(
    name="delete_all_fuselage_cross_sections",
    description="Delete all cross-sections from a fuselage.",
)
async def delete_all_fuselage_cross_sections_tool(aeroplane_id: UUID4, fuselage_name: str) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.delete_aeroplane_fuselage_cross_sections,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
    )


@mcp_tool(
    name="get_fuselage_cross_section",
    description="Get one fuselage cross-section by index.",
)
async def get_fuselage_cross_section_tool(aeroplane_id: UUID4, fuselage_name: str, cross_section_index: int) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.get_aeroplane_fuselage_cross_section,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
        cross_section_index=cross_section_index,
    )


@mcp_tool(
    name="create_fuselage_cross_section",
    description="Insert a new fuselage cross-section at a given index (-1 appends at the end).",
)
async def create_fuselage_cross_section_tool(
    aeroplane_id: UUID4,
    fuselage_name: str,
    cross_section_index: int,
    request: schemas.FuselageXSecSuperEllipseSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.create_aeroplane_fuselage_cross_section,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
        cross_section_index=cross_section_index,
        request=request,
    )


@mcp_tool(
    name="update_fuselage_cross_section",
    description="Replace an existing fuselage cross-section at a specific index.",
)
async def update_fuselage_cross_section_tool(
    aeroplane_id: UUID4,
    fuselage_name: str,
    cross_section_index: int,
    request: schemas.FuselageXSecSuperEllipseSchema,
) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.update_aeroplane_fuselage_cross_section,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
        cross_section_index=cross_section_index,
        request=request,
    )


@mcp_tool(
    name="delete_fuselage_cross_section",
    description="Delete one fuselage cross-section by index.",
)
async def delete_fuselage_cross_section_tool(aeroplane_id: UUID4, fuselage_name: str, cross_section_index: int) -> Any:
    return await _call_endpoint(
        aeroplane_fuselages.delete_aeroplane_fuselage_cross_section,
        aeroplane_id=aeroplane_id,
        fuselage_name=fuselage_name,
        cross_section_index=cross_section_index,
    )


# CAD export tools
@mcp_tool(
    name="create_wing_loft_export",
    description="Start an asynchronous wing export task for one aeroplane wing and selected export format.",
)
async def create_wing_loft_export_tool(
    aeroplane_id: UUID4,
    wing_name: str,
    creator_url_type: CreatorUrlType = CreatorUrlType.WING_LOFT,
    exporter_url_type: ExporterUrlType = ExporterUrlType.STL,
    leading_edge_offset_factor: float = 0.1,
    trailing_edge_offset_factor: float = 0.15,
    aeroplane_settings: AeroplaneSettings | None = None,
) -> Any:
    return await _call_endpoint(
        cad.create_wing_loft,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        creator_url_type=creator_url_type,
        exporter_url_type=exporter_url_type,
        leading_edge_offset_factor=leading_edge_offset_factor,
        trailing_edge_offset_factor=trailing_edge_offset_factor,
        aeroplane_settings=aeroplane_settings,
    )


@mcp_tool(
    name="get_aeroplane_task_status",
    description="Get the current status of an asynchronous CAD export task.",
)
async def get_aeroplane_task_status_tool(aeroplane_id: str) -> Any:
    return await _call_endpoint(cad.get_aeroplane_task_status, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="download_export_zip",
    description="Get metadata for the generated export ZIP file of a completed task.",
)
async def download_export_zip_tool(aeroplane_id: str) -> Any:
    return await _call_endpoint(cad.download_aeroplane_zip, aeroplane_id=aeroplane_id)


# Aero analysis tools (implemented endpoints only)
@mcp_tool(
    name="analyze_wing_aerodynamics",
    description="Run aerodynamic analysis for one wing at a specific operating point using the selected analysis tool.",
)
async def analyze_wing_aerodynamics_tool(
    aeroplane_id: UUID4,
    wing_name: str,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> Any:
    return await _call_endpoint(
        aeroanalysis.analyze_wing_post,
        aeroplane_id=aeroplane_id,
        wing_name=wing_name,
        operating_point=operating_point,
        analysis_tool=analysis_tool,
    )


@mcp_tool(
    name="analyze_airplane_at_operating_point",
    description="Run full-airplane aerodynamic analysis at a specific operating point using the selected analysis tool.",
)
async def analyze_airplane_at_operating_point_tool(
    aeroplane_id: UUID4,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> Any:
    return await _call_endpoint(
        aeroanalysis.analyze_airplane_post,
        aeroplane_id=aeroplane_id,
        operating_point=operating_point,
        analysis_tool=analysis_tool,
    )


@mcp_tool(
    name="get_streamlines_as_html",
    description="Generate VLM streamlines and return the URL of an HTML visualization.",
)
async def get_streamlines_as_html_tool(aeroplane_id: UUID4, operating_point: OperatingPointSchema) -> Any:
    return await _call_endpoint(
        aeroanalysis.calculate_streamlines,
        aeroplane_id=aeroplane_id,
        operating_point=operating_point,
        request=None,
        settings=get_settings(),
    )


@mcp_tool(
    name="analyze_alpha_sweep",
    description="Run an angle-of-attack sweep analysis for one aeroplane.",
)
async def analyze_alpha_sweep_tool(aeroplane_id: UUID4, sweep_request: AlphaSweepRequest) -> Any:
    return await _call_endpoint(
        aeroanalysis.analyze_airplane_alpha_sweep,
        aeroplane_id=aeroplane_id,
        sweep_request=sweep_request,
    )


@mcp_tool(
    name="analyze_alpha_sweep_diagram",
    description="Generate an angle-of-attack sweep diagram and return its static URL.",
)
async def analyze_alpha_sweep_diagram_tool(aeroplane_id: UUID4, sweep_request: AlphaSweepRequest) -> Any:
    return await _call_endpoint(
        aeroanalysis.analyze_airplane_alpha_sweep_diagram,
        aeroplane_id=aeroplane_id,
        sweep_request=sweep_request,
        request=None,
        settings=get_settings(),
    )


@mcp_tool(
    name="analyze_parameter_sweep",
    description="Run a parameter sweep for one variable (alpha, velocity, beta, p, q, or r).",
)
async def analyze_parameter_sweep_tool(aeroplane_id: UUID4, sweep_request: SimpleSweepRequest) -> Any:
    return await _call_endpoint(
        aeroanalysis.analyze_airplane_simple_sweep,
        aeroplane_id=aeroplane_id,
        sweep_request=sweep_request,
    )


@mcp_tool(
    name="get_streamlines_three_view",
    description="Generate a streamlines-based three-view PNG and return it as base64 data.",
)
async def get_streamlines_three_view_tool(aeroplane_id: UUID4, operating_point: OperatingPointSchema) -> Any:
    return await _call_endpoint(
        aeroanalysis.get_streamlines_three_view,
        aeroplane_id=aeroplane_id,
        operating_point=operating_point,
    )


@mcp_tool(
    name="get_aeroplane_three_view",
    description="Generate a three-view PNG image of the aeroplane and return it as base64 data.",
)
async def get_aeroplane_three_view_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(aeroanalysis.get_aeroplane_three_view, aeroplane_id=aeroplane_id)


@mcp_tool(
    name="get_aeroplane_three_view_url",
    description="Generate a three-view diagram image and return its static URL.",
)
async def get_aeroplane_three_view_url_tool(aeroplane_id: UUID4) -> Any:
    return await _call_endpoint(
        aeroanalysis.get_aeroplane_three_view_url,
        aeroplane_id=aeroplane_id,
        request=None,
        settings=get_settings(),
    )


@mcp_tool(
    name="get_streamlines_three_view_url",
    description="Generate a streamlines three-view image and return its static URL.",
)
async def get_streamlines_three_view_url_tool(aeroplane_id: UUID4, operating_point: OperatingPointSchema) -> Any:
    return await _call_endpoint(
        aeroanalysis.get_streamlines_three_view_url,
        aeroplane_id=aeroplane_id,
        operating_point=operating_point,
        request=None,
        settings=get_settings(),
    )


# Operating-point tools
@mcp_tool(
    name="generate_default_operating_point_set",
    description="Generate a default operating-point set for an aircraft UUID from its assigned flight profile.",
)
async def generate_default_operating_point_set_tool(
    aircraft_id: UUID4,
    request: GenerateOperatingPointSetRequest | None = None,
) -> Any:
    return await _call_endpoint(
        operating_points.generate_default_operating_point_set,
        aircraft_id=aircraft_id,
        request=request or GenerateOperatingPointSetRequest(),
    )


@mcp_tool(
    name="create_operating_point",
    description="Create and persist one stored operating point record.",
)
async def create_operating_point_tool(op_data: StoredOperatingPointCreate) -> Any:
    return await _call_endpoint(operating_points.create_operating_point, op_data=op_data)


@mcp_tool(
    name="list_operating_points",
    description="List stored operating points, optionally filtered by aircraft UUID with pagination.",
)
async def list_operating_points_tool(
    aircraft_id: UUID4 | None = None,
    skip: int = 0,
    limit: int = 200,
) -> Any:
    return await _call_endpoint(
        operating_points.list_operating_points,
        aircraft_id=aircraft_id,
        skip=skip,
        limit=limit,
    )


@mcp_tool(
    name="get_operating_point",
    description="Get one stored operating point by numeric operating-point ID.",
)
async def get_operating_point_tool(op_id: int) -> Any:
    return await _call_endpoint(operating_points.read_operating_point, op_id=op_id)


@mcp_tool(
    name="update_operating_point",
    description="Replace one stored operating point by numeric operating-point ID.",
)
async def update_operating_point_tool(op_id: int, op_data: StoredOperatingPointCreate) -> Any:
    return await _call_endpoint(operating_points.update_operating_point, op_id=op_id, op_data=op_data)


@mcp_tool(
    name="delete_operating_point",
    description="Delete one stored operating point by numeric operating-point ID.",
)
async def delete_operating_point_tool(op_id: int) -> Any:
    return await _call_endpoint(operating_points.delete_operating_point, op_id=op_id)


@mcp_tool(
    name="create_operating_pointset",
    description="Create and persist an operating-point set with references to stored operating points.",
)
async def create_operating_pointset_tool(opset_data: OperatingPointSetSchema) -> Any:
    return await _call_endpoint(operating_points.create_operating_pointset, opset_data=opset_data)


@mcp_tool(
    name="list_operating_pointsets",
    description="List stored operating-point sets, optionally filtered by aircraft UUID with pagination.",
)
async def list_operating_pointsets_tool(
    aircraft_id: UUID4 | None = None,
    skip: int = 0,
    limit: int = 200,
) -> Any:
    return await _call_endpoint(
        operating_points.list_operating_pointsets,
        aircraft_id=aircraft_id,
        skip=skip,
        limit=limit,
    )


@mcp_tool(
    name="get_operating_pointset",
    description="Get one operating-point set by numeric set ID.",
)
async def get_operating_pointset_tool(opset_id: int) -> Any:
    return await _call_endpoint(operating_points.read_operating_pointset, opset_id=opset_id)


@mcp_tool(
    name="update_operating_pointset",
    description="Replace one operating-point set by numeric set ID.",
)
async def update_operating_pointset_tool(opset_id: int, opset_data: OperatingPointSetSchema) -> Any:
    return await _call_endpoint(
        operating_points.update_operating_pointset,
        opset_id=opset_id,
        opset_data=opset_data,
    )


@mcp_tool(
    name="delete_operating_pointset",
    description="Delete one operating-point set by numeric set ID.",
)
async def delete_operating_pointset_tool(opset_id: int) -> Any:
    return await _call_endpoint(operating_points.delete_operating_pointset, opset_id=opset_id)


# Flight-profile tools
@mcp_tool(
    name="create_flight_profile",
    description="Create a new RC flight profile intent and return the persisted profile.",
)
async def create_flight_profile_tool(payload: RCFlightProfileCreate) -> Any:
    return await _call_endpoint(flight_profiles.create_flight_profile, payload=payload)


@mcp_tool(
    name="list_flight_profiles",
    description="List RC flight profiles with optional type filtering and pagination.",
)
async def list_flight_profiles_tool(
    profile_type: FlightProfileType | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    return await _call_endpoint(
        flight_profiles.list_flight_profiles,
        profile_type=profile_type,
        skip=skip,
        limit=limit,
    )


@mcp_tool(
    name="get_flight_profile",
    description="Get a single RC flight profile by numeric profile ID.",
)
async def get_flight_profile_tool(profile_id: int) -> Any:
    return await _call_endpoint(flight_profiles.get_flight_profile, profile_id=profile_id)


@mcp_tool(
    name="update_flight_profile",
    description="Patch an existing RC flight profile by numeric profile ID.",
)
async def update_flight_profile_tool(profile_id: int, payload: RCFlightProfileUpdate) -> Any:
    return await _call_endpoint(
        flight_profiles.update_flight_profile,
        profile_id=profile_id,
        payload=payload,
    )


@mcp_tool(
    name="delete_flight_profile",
    description="Delete an RC flight profile by numeric profile ID.",
)
async def delete_flight_profile_tool(profile_id: int) -> Any:
    return await _call_endpoint(flight_profiles.delete_flight_profile, profile_id=profile_id)


@mcp_tool(
    name="assign_flight_profile_to_aircraft",
    description="Assign a flight profile to an aircraft UUID, replacing any existing assignment.",
)
async def assign_flight_profile_to_aircraft_tool(aircraft_id: UUID4, profile_id: int) -> Any:
    return await _call_endpoint(
        flight_profiles.assign_flight_profile_to_aircraft,
        aircraft_id=aircraft_id,
        profile_id=profile_id,
    )


@mcp_tool(
    name="detach_flight_profile_from_aircraft",
    description="Detach the currently assigned flight profile from an aircraft UUID.",
)
async def detach_flight_profile_from_aircraft_tool(aircraft_id: UUID4) -> Any:
    return await _call_endpoint(flight_profiles.detach_flight_profile_from_aircraft, aircraft_id=aircraft_id)


MCP_TOOL_NAMES: tuple[str, ...] = tuple(spec.name for spec in TOOL_SPECS)


def create_mcp_server() -> FastMCP:
    """Create a native FastMCP server with explicitly registered tools."""
    mcp = FastMCP(name="da3dalus-cad-tools")

    for spec in TOOL_SPECS:
        mcp.tool(name=spec.name, description=spec.description)(spec.handler)

    return mcp


mcp: FastMCP | None = None


def get_mcp() -> FastMCP:
    global mcp
    if mcp is None:
        mcp = create_mcp_server()
    return mcp


def run_mcp_server() -> None:
    """Start the FastMCP server as a separate HTTP service."""
    server = get_mcp()
    server.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")


mcp = get_mcp()


if __name__ == "__main__":
    run_mcp_server()
