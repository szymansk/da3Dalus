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


async def analyse_aerodynamics(analysis_tool: AnalysisToolUrlType,
                               operating_point: OperatingPointSchema,
                               asb_airplane: Airplane,
                               draw_streamlines: bool = False,
                               backend: Literal['plotly','pyvista'] = 'plotly') -> (AnalysisModel, Figure|Plotter):
    """
    Perform aerodynamic analysis on an airplane using the specified analysis tool.

    Args:
        analysis_tool (AnalysisToolUrlType): The tool to use for aerodynamic analysis.
            Options include AVL, AeroBuildup, or Vortex Lattice.
        operating_point (OperatingPointSchema): The operating point containing flight conditions
            such as velocity, altitude, and angles of attack.
        asb_airplane (Airplane): The airplane model to analyze, represented as an aerosandbox Airplane object.
        draw_streamlines (bool, optional): Whether to generate a streamline visualization. Defaults to False.

    Returns:
        tuple: A tuple containing:
            - AnalysisModel: The results of the aerodynamic analysis.
            - Figure: A Plotly figure object containing the streamline visualization
              (if requested and only for Vortex Lattice analysis),
              or None if `draw_streamlines` is False.

    Raises:
        ValueError: If an invalid analysis tool is specified or if unsupported parameter sweeps are attempted.
    """
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
            figure = vlm.draw(show=False, backend=backend)
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


async def compile_four_view_figure(figure):
    # Create a 2x2 subplot figure
    fig = make_subplots(
        rows=3, cols=2,
        specs=[[{'type': 'scene', "rowspan": 2}, {'type': 'scene'}],
               [None, {'type': 'scene'}],
               [{'type': 'scene', 'colspan': 2}, None]],
        subplot_titles=["Side View (y-axis)", "Front View (x-axis)",
                        "Top View (z-axis)", "Overview from top left"],
        row_heights=[0.2, 0.2, 0.6],
        column_widths=[0.4, 0.6],
        vertical_spacing=0.05,  # reduce space between rows
        horizontal_spacing=0.05  # reduce space between columns
    )
    # Calculate the bounding box of all points in the scene
    x_min, x_max = float('inf'), float('-inf')
    y_min, y_max = float('inf'), float('-inf')
    z_min, z_max = float('inf'), float('-inf')
    for trace in figure.data:
        if hasattr(trace, 'x') and trace.x is not None:
            x_min = min(x_min, min(f for f in trace.x if f is not None))
            x_max = max(x_max, max(f for f in trace.x if f is not None))
        if hasattr(trace, 'y') and trace.y is not None:
            y_min = min(y_min, min(f for f in trace.y if f is not None))
            y_max = max(y_max, max(f for f in trace.y if f is not None))
        if hasattr(trace, 'z') and trace.z is not None:
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
        camera=dict(
            eye=dict(x=center_x, y=center_y - camera_distance, z=center_z),
            up=dict(x=0, y=0, z=1),
            center=dict(x=center_x, y=center_y, z=center_z)
        ),
        aspectmode='data',  # Force equal aspect ratio
        row=1, col=2
    )
    # Front view (x-axis)
    fig.update_scenes(
        camera=dict(
            eye=dict(x=center_x - camera_distance * 2, y=center_y, z=center_z),
            up=dict(x=0, y=0, z=1),
            center=dict(x=center_x, y=center_y, z=center_z)
        ),
        aspectmode='data',  # Force equal aspect ratio
        row=2, col=2
    )
    # Top view (z-axis)
    fig.update_scenes(
        camera=dict(
            eye=dict(x=center_x, y=center_y, z=center_z + camera_distance * 2.),
            up=dict(x=0, y=1, z=0),
            center=dict(x=center_x, y=center_y, z=center_z)
        ),
        aspectmode='data',  # Force equal aspect ratio
        row=1, col=1
    )
    # Overview from top left iso-view
    fig.update_scenes(
        camera=dict(
            eye=dict(
                x=center_x - camera_distance * 0.577 * 3,  # 1/sqrt(3) to normalize the vector
                y=center_y - camera_distance * 0.577 * 3,
                z=center_z + camera_distance * 0.577 * 3
            ),
            up=dict(x=0, y=0, z=1),
            center=dict(x=center_x, y=center_y, z=center_z)
        ),
        aspectmode='data',  # Force equal aspect ratio
        row=3, col=1
    )
    # Update layout
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),  # reduce whitespace
        height=1000,
        width=1000,
        title_text="Four Views of Aerodynamic Analysis",
        showlegend=False
    )
    axis_style = dict(
        showbackground=False,
        showline=False,
        zeroline=False,
        showgrid=False,
        ticks='',
        showticklabels=False
    )
    fig.update_layout(
        scene=dict(
            xaxis=axis_style,
            yaxis=axis_style,
            zaxis=axis_style
        ),
        scene2=dict(
            xaxis=axis_style,
            yaxis=axis_style,
            zaxis=axis_style
        ),
        scene3=dict(
            xaxis=axis_style,
            yaxis=axis_style,
            zaxis=axis_style
        ),
        scene4=dict(
            xaxis=axis_style,
            yaxis=axis_style,
            zaxis=axis_style
        ),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    return fig


async def save_content_and_get_static_url(aeroplane_id, base_url, content, content_type, filename):
    # Create directory structure
    content_dir = os.path.join("tmp", str(aeroplane_id), content_type)
    os.makedirs(content_dir, exist_ok=True)
    # Save HTML content to file
    file_path = os.path.join(content_dir, filename)
    with open(file_path, "w") as f:
        f.write(content)
    # Return URL to the served HTML file
    relative_url = f"/static/{aeroplane_id}/{content_type}/{filename}"
    full_url = urljoin(base_url, relative_url)
    return full_url
