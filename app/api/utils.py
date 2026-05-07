import asyncio
import os
from typing import Literal
from urllib.parse import urljoin

import aerosandbox as asb
import numpy as np
from aerosandbox import Airplane
from plotly.graph_objs import Figure
from plotly.subplots import make_subplots
from pyvista import Plotter

from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.aeroanalysisschema import OperatingPointSchema
from cad_designer.airplane.aircraft_topology.models.analysis_model import AnalysisModel


def _as_array_if_needed(value):
    """Return value as-is if float, otherwise wrap in np.array."""
    return value if isinstance(value, float) else np.array(value)


def _build_operating_point(operating_point: OperatingPointSchema) -> asb.OperatingPoint:
    """Build an Aerosandbox OperatingPoint from the schema."""
    atmosphere = asb.Atmosphere(altitude=operating_point.altitude)
    return asb.OperatingPoint(
        velocity=_as_array_if_needed(operating_point.velocity),
        alpha=_as_array_if_needed(operating_point.alpha),
        beta=_as_array_if_needed(operating_point.beta),
        p=_as_array_if_needed(operating_point.p),
        q=_as_array_if_needed(operating_point.q),
        r=_as_array_if_needed(operating_point.r),
        atmosphere=atmosphere,
    )


def _build_control_run_command(
    asb_airplane,
    overrides: dict[str, float] | None = None,
) -> str | None:
    """Build AVL run_command string to override hardcoded control deflections."""
    from app.services.avl_strip_forces import build_control_deflection_commands

    commands = build_control_deflection_commands(asb_airplane, overrides)
    return "\n".join(commands) if commands else None


def _run_avl(asb_airplane, op_point, operating_point, avl_file_content=None):
    """Run AVL analysis; raises ValueError for parameter sweeps."""
    if isinstance(operating_point.alpha, (list, tuple, np.ndarray)) or isinstance(
        operating_point.beta, (list, tuple, np.ndarray)
    ):
        raise ValueError(
            "AVL analysis does not support parameter sweeps. "
            "Please use AeroBuildup or Vortex Lattice for that."
        )
    run_command = _build_control_run_command(asb_airplane)
    if avl_file_content is not None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            avl_path = Path(tmp_dir) / "airplane.avl"
            avl_path.write_text(avl_file_content)
            avl = asb.AVL(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=operating_point.xyz_ref,
                working_directory=tmp_dir,
            )
            return AnalysisModel.from_avl_dict(avl.run(run_command=run_command)), None
    else:
        avl = asb.AVL(airplane=asb_airplane, op_point=op_point, xyz_ref=operating_point.xyz_ref)
        return AnalysisModel.from_avl_dict(avl.run(run_command=run_command)), None


def _run_aerobuildup(asb_airplane, op_point, operating_point):
    """Run AeroBuildup analysis."""
    abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op_point, xyz_ref=operating_point.xyz_ref)
    return AnalysisModel.from_abu_dict(
        abu.run_with_stability_derivatives(),
        asb_airplan=asb_airplane,
        methode="aerobuildup",
    ), None


def _run_vlm(asb_airplane, op_point, operating_point, draw_streamlines, backend):
    """Run Vortex Lattice Method analysis."""
    vlm = asb.VortexLatticeMethod(
        airplane=asb_airplane, op_point=op_point, xyz_ref=operating_point.xyz_ref
    )
    vlm.verbose = True
    vlm_results = vlm.run_with_stability_derivatives()
    figure = vlm.draw(show=False, backend=backend) if draw_streamlines else None
    return AnalysisModel.from_abu_dict(
        vlm_results,
        asb_airplan=asb_airplane,
        operating_point=op_point,
        methode="vortex_lattice",
    ), figure


def analyse_aerodynamics(
    analysis_tool: AnalysisToolUrlType,
    operating_point: OperatingPointSchema,
    asb_airplane: Airplane,
    draw_streamlines: bool = False,
    backend: Literal["plotly", "pyvista"] = "plotly",
    avl_file_content: str | None = None,
) -> (AnalysisModel, Figure | Plotter):
    """Perform aerodynamic analysis using the specified tool.

    Returns (AnalysisModel, Figure | None).
    Raises ValueError for invalid tool or unsupported parameter sweeps.
    """
    op_point = _build_operating_point(operating_point)
    asb_airplane.xyz_ref = operating_point.xyz_ref

    overrides = operating_point.control_deflections
    if overrides:
        asb_airplane = asb_airplane.with_control_deflections(overrides)

    if analysis_tool == AnalysisToolUrlType.AVL:
        return _run_avl(asb_airplane, op_point, operating_point, avl_file_content)
    if analysis_tool == AnalysisToolUrlType.AEROBUILDUP:
        return _run_aerobuildup(asb_airplane, op_point, operating_point)
    if analysis_tool == AnalysisToolUrlType.VORTEX_LATTICE:
        return _run_vlm(asb_airplane, op_point, operating_point, draw_streamlines, backend)

    raise ValueError(
        f"Invalid analysis tool: {analysis_tool}. "
        "Must be one of: AVL, AeroBuildup, or Vortex Lattice."
    )


def compile_four_view_figure(figure):
    # Create a 2x2 subplot figure
    fig = make_subplots(
        rows=3,
        cols=2,
        specs=[
            [{"type": "scene", "rowspan": 2}, {"type": "scene"}],
            [None, {"type": "scene"}],
            [{"type": "scene", "colspan": 2}, None],
        ],
        subplot_titles=[
            "Side View (y-axis)",
            "Front View (x-axis)",
            "Top View (z-axis)",
            "Overview from top left",
        ],
        row_heights=[0.2, 0.2, 0.6],
        column_widths=[0.4, 0.6],
        vertical_spacing=0.05,  # reduce space between rows
        horizontal_spacing=0.05,  # reduce space between columns
    )
    # Calculate the bounding box of all points in the scene
    x_min, x_max = float("inf"), float("-inf")
    y_min, y_max = float("inf"), float("-inf")
    z_min, z_max = float("inf"), float("-inf")
    for trace in figure.data:
        if hasattr(trace, "x") and trace.x is not None:
            x_min = min(x_min, min(f for f in trace.x if f is not None))
            x_max = max(x_max, max(f for f in trace.x if f is not None))
        if hasattr(trace, "y") and trace.y is not None:
            y_min = min(y_min, min(f for f in trace.y if f is not None))
            y_max = max(y_max, max(f for f in trace.y if f is not None))
        if hasattr(trace, "z") and trace.z is not None:
            z_min = min(z_min, min(f for f in trace.z if f is not None))
            z_max = max(z_max, max(f for f in trace.z if f is not None))
    # Calculate the center and size of the bounding box
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    center_z = (z_min + z_max) / 2
    # Calculate the maximum dimension for consistent scaling
    max_dim = max(x_max - x_min, y_max - y_min, z_max - z_min)
    # Set camera distance based on the maximum dimension
    camera_distance = max_dim  # Adjust this factor as needed
    # Copy the traces from the original figure to each subplot
    for trace in figure.data:
        # Side view (y-axis)
        fig.add_trace(trace, row=1, col=2)
        # Front view (x-axis)
        fig.add_trace(trace, row=2, col=2)
        # Top view (z-axis)
        fig.add_trace(trace, row=1, col=1)
        # Overview from top left
        fig.add_trace(trace, row=3, col=1)
    # Set camera angles for each view and ensure consistent aspect ratio
    # Side view (y-axis)
    fig.update_scenes(
        camera={
            "eye": {"x": center_x, "y": center_y - camera_distance, "z": center_z},
            "up": {"x": 0, "y": 0, "z": 1},
            "center": {"x": center_x, "y": center_y, "z": center_z},
        },
        aspectmode="data",  # Force equal aspect ratio
        row=1,
        col=2,
    )
    # Front view (x-axis)
    fig.update_scenes(
        camera={
            "eye": {"x": center_x - camera_distance * 2, "y": center_y, "z": center_z},
            "up": {"x": 0, "y": 0, "z": 1},
            "center": {"x": center_x, "y": center_y, "z": center_z},
        },
        aspectmode="data",  # Force equal aspect ratio
        row=2,
        col=2,
    )
    # Top view (z-axis)
    fig.update_scenes(
        camera={
            "eye": {"x": center_x, "y": center_y, "z": center_z + camera_distance * 2.0},
            "up": {"x": 0, "y": 1, "z": 0},
            "center": {"x": center_x, "y": center_y, "z": center_z},
        },
        aspectmode="data",  # Force equal aspect ratio
        row=1,
        col=1,
    )
    # Overview from top left iso-view
    fig.update_scenes(
        camera={
            "eye": {
                "x": center_x - camera_distance * 0.577 * 3,  # 1/sqrt(3) to normalize the vector
                "y": center_y - camera_distance * 0.577 * 3,
                "z": center_z + camera_distance * 0.577 * 3,
            },
            "up": {"x": 0, "y": 0, "z": 1},
            "center": {"x": center_x, "y": center_y, "z": center_z},
        },
        aspectmode="data",  # Force equal aspect ratio
        row=3,
        col=1,
    )
    # Update layout
    fig.update_layout(
        margin={"l": 20, "r": 20, "t": 50, "b": 20},  # reduce whitespace
        height=1000,
        width=1000,
        title_text="Four Views of Aerodynamic Analysis",
        showlegend=False,
    )
    axis_style = {
        "showbackground": False,
        "showline": False,
        "zeroline": False,
        "showgrid": False,
        "ticks": "",
        "showticklabels": False,
    }
    fig.update_layout(
        scene={
            "xaxis": axis_style,
            "yaxis": axis_style,
            "zaxis": axis_style,
        },
        scene2={
            "xaxis": axis_style,
            "yaxis": axis_style,
            "zaxis": axis_style,
        },
        scene3={
            "xaxis": axis_style,
            "yaxis": axis_style,
            "zaxis": axis_style,
        },
        scene4={
            "xaxis": axis_style,
            "yaxis": axis_style,
            "zaxis": axis_style,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


async def save_content_and_get_static_url(aeroplane_id, base_url, content, content_type, filename):
    content_dir = os.path.join("tmp", str(aeroplane_id), content_type)
    file_path = os.path.join(content_dir, filename)
    await asyncio.to_thread(_write_file_sync, content_dir, file_path, content)
    relative_url = f"/static/{aeroplane_id}/{content_type}/{filename}"
    return urljoin(base_url, relative_url)


def _write_file_sync(content_dir: str, file_path: str, content: str) -> None:
    """Create directory and write content (used via asyncio.to_thread)."""
    os.makedirs(content_dir, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(content)
