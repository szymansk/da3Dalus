import logging
from typing import Any, Tuple, List

import numpy as np
import aerosandbox as asb
from cadquery import Workplane, CQ

import logging

from cad_designer.aerosandbox.slicing import compute_shape_properties, slice_model_along_x, fit_shape_area_superellipse, \
    plot_superellipse_fit, load_step_model
from cad_designer.airplane.creator.cad_operations import ScaleRotateTranslateCreator

logger = logging.getLogger(__name__)

from pathlib import Path

def asb_mesh_to_stl(
    data: Tuple[np.ndarray, np.ndarray],
    output_path: str,
    scale: float = 1.0,
    correct_normals: bool = True
) -> str:
    """
    Converts a mesh represented by vertices and triangles into an STL file.

    cavets: The normal direction of the STL file may not be correct.

    Args:
        data (Tuple[np.ndarray, np.ndarray]): A tuple containing:
            - vertices (np.ndarray): An array of vertex coordinates (Nx3).
            - triangles (np.ndarray): An array of triangle indices (Mx3).
        output_path (str): The file path where the STL file will be saved.
        scale (float, optional): A scaling factor to apply to the vertices. Defaults to 1.0.
        correct_normals (bool, optional): Whether to correct the normals to ensure they point outward. Defaults to True.

    Returns:
        str: The generated STL content as a string.
    """
    vertices, triangles = data
    vertices = vertices * scale
    center = vertices.mean(axis=0)

    def compute_normal(v1: np.ndarray, v2: np.ndarray, v3: np.ndarray) -> np.ndarray:
        normal = np.cross(v2 - v1, v3 - v1)
        norm = np.linalg.norm(normal)
        return normal / norm if norm != 0 else np.array([0.0, 0.0, 0.0])

    stl_lines = ["solid triangle_mesh"]

    for tri in triangles:
        v1, v2, v3 = (vertices[i] for i in tri)
        normal = compute_normal(v1, v2, v3)
        centroid = (v1 + v2 + v3) / 3
        direction = centroid - center

        # Flip normal if it's pointing inward
        if correct_normals and np.dot(normal, direction) < 0:
            v2, v3 = v3, v2  # flip winding
            normal = compute_normal(v1, v2, v3)

        stl_lines.append(f"  facet normal {normal[0]} {normal[1]} {normal[2]}")
        stl_lines.append("    outer loop")
        stl_lines.append(f"      vertex {v1[0]} {v1[1]} {v1[2]}")
        stl_lines.append(f"      vertex {v2[0]} {v2[1]} {v2[2]}")
        stl_lines.append(f"      vertex {v3[0]} {v3[1]} {v3[2]}")
        stl_lines.append("    endloop")
        stl_lines.append("  endfacet")

    stl_lines.append("endsolid triangle_mesh")

    stl_str = "\n".join(stl_lines)
    Path(output_path).write_text(stl_str)
    logging.info(f"STL written to {output_path} with scale {scale}, normals corrected: {correct_normals}")
    return stl_str

def export_asb_wing_to_stl(wing: asb.Wing, filepath: str | Path = "wing_model.stl") -> str:
    """
    Exports an AeroSandbox Wing object to an STL file.

    This function takes an `asb.Wing` object, converts it into a mesh representation,
    and writes it to an STL file at the specified file path.

    caveats: The normal direction of the STL file may not be correct.

    Args:
        wing (asb.Wing): The AeroSandbox Wing object to be exported.
        filepath (str | Path, optional): The file path where the STL file will be saved.
                                         Defaults to 'wing_model.stl'.

    Returns:
        str: The generated STL content as a string.
    """
    airplane = asb.Airplane(
        name="ConvertedWing",
        wings=[wing]
    )

    stl = asb_mesh_to_stl(
        wing.mesh_body(method='tri'),
        output_path=filepath,
        scale=0.1)

    print(f"✅ STEP export complete: {filepath}")
    return stl

def convert_solid_to_asb_fuselage(shape: Workplane, number_of_slices=100, spacing=None, plot: bool = False, scale: float=1.0) -> asb.Fuselage:
    """
    Converts a CAD solid object into an AeroSandbox fuselage object.

    This function takes a `cadquery.Workplane` object representing a solid shape, slices it along the x-axis,
    and fits superellipse parameters to the slices. The resulting slices are then used to construct an
    AeroSandbox `Fuselage` object.

    Args:
        shape (Workplane): The CAD solid object to be converted.
        number_of_slices (int, optional): The number of slices to divide the solid into. Defaults to 100.
        spacing (optional): The spacing between slices. If None, slices are evenly spaced. Defaults to None.
        plot (bool, optional): Whether to plot the superellipse fit for each slice. Defaults to False.

    Returns:
        asb.Fuselage: The resulting AeroSandbox fuselage object.
    """
    solid = shape.solids().first()
    scaled_solid = CQ(solid.findSolid().scale(scale))
    surface_volume = compute_shape_properties(scaled_solid.toOCC())

    # Perform slicing
    wire_slices = slice_model_along_x(scaled_solid, spacing=spacing, number_of_slices=number_of_slices)

    ellipse_slices = []
    for wires in wire_slices:
        prev_params = None
        for points in wires:
            points_2d = np.array([(y, z) for (_, y, z) in points])
            result = fit_shape_area_superellipse(points_2d, prev_params=prev_params)
            logger.debug(f"Fitted parameters: {result}")
            if plot:
                plot_superellipse_fit(points_3d= np.array(points), fit_result=result, num_samples = 200)
            result['center'] = np.array([points[0][0], result['center'][0], result['center'][1]])
            ellipse_slices.append(result)
            #break # only take one wire per slice
            prev_params = result

    # convert ellipse_slices to FuselageXSec
    fuselage_xsecs = []
    for i, ellipse in enumerate(ellipse_slices):
        fuselage_xsec = asb.FuselageXSec(
            #xyz_c = ellipse['center'],
            xyz_normal = np.array([1.0, 0.0, 0.0]),
            radius = None,
            width = 2. * ellipse['a'],
            height = 2. * ellipse['b'],
            shape = ellipse['n'],
            analysis_specific_options = None,
        ).translate(ellipse['center'])

        fuselage_xsecs.append(fuselage_xsec)

    asb_fuselage = asb.Fuselage(
        name="Fuselage",
        xsecs=fuselage_xsecs,
        color = None, #: Optional[Union[str, Tuple[float]]] = None,
        analysis_specific_options = None #: Optional[Dict[type, Dict[str, Any]]] = None,
    )

    if plot:
        asb_fuselage.draw(backend="plotly", show=True)
    logger.info(f"Fuselage surface area >> initial: {surface_volume['surface_area']}; transformed: {asb_fuselage.area_wetted()}; transformed/initial = {surface_volume['surface_area']/asb_fuselage.area_wetted()}\n"
                f"Fuselage volume       >> initial: {surface_volume['volume']}; transformed: {asb_fuselage.volume()}; transformed/initial = {surface_volume['volume']/asb_fuselage.volume()}")
    return asb_fuselage

def convert_step_to_asb_fuselage(step_file: str, number_of_slices=100, spacing=None, plot: bool = False, scale:float=1.0) -> List[asb.Fuselage]:
    """
    Converts a STEP file containing 3D CAD models into a list of AeroSandbox fuselage objects.

    This function loads a STEP file, extracts solid objects, and converts each solid into an
    AeroSandbox `Fuselage` object by slicing it along the x-axis and fitting superellipse parameters
    to the slices.

    Args:
        step_file (str): Path to the STEP file containing the 3D CAD model.
        number_of_slices (int, optional): The number of slices to divide each solid into. Defaults to 100.
        spacing (optional): The spacing between slices. If None, slices are evenly spaced. Defaults to None.
        plot (bool, optional): Whether to plot the superellipse fit for each slice. Defaults to False.

    Returns:
        List[asb.Fuselage]: A list of AeroSandbox fuselage objects created from the solids in the STEP file.
    """
    # Load model
    model = load_step_model(step_file)
    fuselages = []
    for solid in model.solids().all():
        fuselage = convert_solid_to_asb_fuselage(solid, number_of_slices=number_of_slices, spacing=spacing, plot=plot, scale=scale)
        fuselages.append(fuselage)

    return fuselages