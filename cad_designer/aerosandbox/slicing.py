import cadquery as cq
import os
import matplotlib.pyplot as plt
import numpy as np
from typing import Sequence

import aerosandbox as asb
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

from numpy.typing import NDArray
from scipy.optimize import minimize
from scipy.integrate import quad
from scipy.special import gamma

from OCP.BRepAdaptor import BRepAdaptor_CompCurve
from OCP.GCPnts import GCPnts_UniformAbscissa
from OCP.TopoDS import TopoDS_Wire
from OCP.gp import gp_Pnt

from cad_designer.cq_plugins.display import display

import logging
logger = logging.getLogger(__name__)

def discretize_wire(wire: TopoDS_Wire, num_points: int) -> list[gp_Pnt]:
    comp_curve = BRepAdaptor_CompCurve(wire)
    abscissa = GCPnts_UniformAbscissa(comp_curve, num_points)

    if not abscissa.IsDone():
        raise RuntimeError("Discretization failed.")

    points = []
    for i in range(1, abscissa.NbPoints() + 1):
        param = abscissa.Parameter(i)
        point = comp_curve.Value(param)
        points.append(point)
    return points

def load_step_model(filepath: str) -> cq.Workplane:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"STEP file not found at: {filepath}")
    return cq.importers.importStep(filepath)

def get_x_bounds(shape: cq.Shape) -> tuple[float, float]:
    bb = shape.BoundingBox()
    return bb.xmin, bb.xmax

def slice_model_along_x(shape: cq.Workplane, spacing: float = 0.1, number_of_slices: int = None, points_per_slice: int = 30) -> list[list[tuple[float, float, float]]]:
    if number_of_slices is not None:
        if number_of_slices < 2:
            number_of_slices = 2
        xmin, xmax = get_x_bounds(shape.val())
        spacing = (xmax - xmin) / (number_of_slices-1)
        logger.info(f"Slicing with {number_of_slices} slices set spacing = {spacing:.5f}")
    slices = []
    x = 0
    # getting all wires on the first X plane
    wires = shape.faces("<X").wires().all()
    while True:
        # getting all wires on the first X plane
        slice = []
        for wire in wires:
            points = discretize_wire(wire.toOCC(), points_per_slice)
            tuple_points = [(point.X(), point.Y(), point.Z()) for point in points]
            slice.append(tuple_points)
        logger.debug(f"Slice at x={x}: {slice}")

        if len(slices) > 0 and slice == slices[-1]:
            logger.info(f"Slice at x={x} is identical to the previous slice, skipping.")
            break
        slices.append(slice)

        # Perform the section split
        x += spacing
        wires = shape.faces("<X").workplane(offset=-x).split(keepTop=True).faces(">X").wires().all()

    return slices

def to_superellipse(
    vertices: Sequence[tuple[float, float]],
    exponent: float = 2.5,
    a: float = 1.0,
    b: float = 1.0
) -> NDArray[np.float64]:
    vertices = np.array(vertices)
    center = np.mean(vertices, axis=0)
    normalized = vertices - center
    scale = np.max(np.abs(normalized), axis=0)
    normalized /= scale  # normalize to [-1, 1] box

    angles = np.arctan2(normalized[:, 1], normalized[:, 0])
    super_radii = (np.abs(np.cos(angles) / a) ** exponent +
                   np.abs(np.sin(angles) / b) ** exponent) ** (-1 / exponent)
    x_new = super_radii * np.cos(angles)
    y_new = super_radii * np.sin(angles)

    # Rescale and reposition
    new_shape = np.stack([x_new, y_new], axis=1)
    new_shape *= scale
    new_shape += center
    return new_shape

def superellipse_radius(theta: np.ndarray, a: float, b: float, n: float) -> np.ndarray:
    return (np.abs(np.cos(theta) / a) ** n + np.abs(np.sin(theta) / b) ** n) ** (-1 / n)

def approximate_perimeter(a: float, b: float, n: float) -> float:
    # Numerically integrate the perimeter of the superellipse
    def integrand(theta):
        r = (np.abs(np.cos(theta) / a) ** n + np.abs(np.sin(theta) / b) ** n) ** (-1 / n)
        dr_dtheta = n * r * (
                (np.abs(np.sin(theta) / b) ** (n - 1) * np.cos(theta) / b) -
                (np.abs(np.cos(theta) / a) ** (n - 1) * np.sin(theta) / a)
        )
        return np.sqrt(r ** 2 + dr_dtheta ** 2)

    return quad(integrand, 0, 2 * np.pi, limit=200)[0]

def approximate_area(a: float, b: float, n: float) -> float:
    # Approximation using Gamma function
    return 4 * a * b * (gamma(1 + 1/n)**2) / gamma(1 + 2/n)

def polygon_area(points: np.ndarray) -> float:
    # Shoelace formula for polygon area
    x = points[:, 0]
    y = points[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def fit_symmetric_superellipse(points: np.ndarray, initial_n: float = 2.0) -> dict:
    """
    Fits a symmetric superellipse to a given set of 2D points, ensuring symmetry about the Z-axis.

    Args:
        points (np.ndarray): A 2D array of shape (N, 2) representing the points to fit.
        initial_n (float): The initial guess for the superellipse exponent (n).

    Returns:
        dict: A dictionary containing the fitted parameters:
            - 'center' (np.ndarray): The center of the fitted superellipse.
            - 'a' (float): The semi-major axis length.
            - 'b' (float): The semi-minor axis length.
            - 'n' (float): The superellipse exponent.
            - 'success' (bool): Whether the optimization was successful.
            - 'fun' (float): The value of the objective function at the solution.
    """
    # Force center along Z-axis (Y = 0)
    center_z = np.mean(points[:, 1])
    center = np.array([0.0, center_z])
    shifted = points - center
    angles = np.arctan2(shifted[:, 1], shifted[:, 0])
    radii = np.linalg.norm(shifted, axis=1)

    # Mirror points to enforce symmetry
    angles = np.concatenate([angles, -angles])
    radii = np.concatenate([radii, radii])

    def objective(params: np.ndarray) -> float:
        a, b, n = params
        fit_r = superellipse_radius(angles, a, b, n)
        perimeter_fit = approximate_perimeter(a, b, n)
        perimeter_actual = np.sum(np.linalg.norm(np.roll(shifted, -1, axis=0) - shifted, axis=1))
        radius_loss = np.mean((radii - fit_r)**2)
        length_loss = (perimeter_fit - perimeter_actual)**2
        return radius_loss + 0.01 * length_loss

    result = minimize(
        objective,
        x0=[1.0, 1.0, initial_n],
        bounds=[(1e-3, None), (1e-3, None), (0.5, 10.0)],
        method='L-BFGS-B'
    )

    return {
        "center": center,
        "a": result.x[0],
        "b": result.x[1],
        "n": result.x[2],
        "success": result.success,
        "fun": result.fun
    }

def fit_superellipse(points: np.ndarray, initial_n: float = 2.0) -> dict:
    """
    Fits a superellipse to a given set of 2D points.

    Args:
        points (np.ndarray): A 2D array of shape (N, 2) representing the points to fit.
        initial_n (float): The initial guess for the superellipse exponent (n).

    Returns:
        dict: A dictionary containing the fitted parameters:
            - 'center' (np.ndarray): The center of the fitted superellipse.
            - 'a' (float): The semi-major axis length.
            - 'b' (float): The semi-minor axis length.
            - 'n' (float): The superellipse exponent.
            - 'success' (bool): Whether the optimization was successful.
            - 'fun' (float): The value of the objective function at the solution.
    """
    center = np.mean(points, axis=0)
    shifted = points - center
    angles = np.arctan2(shifted[:, 1], shifted[:, 0])
    radii = np.linalg.norm(shifted, axis=1)

    def objective(params: np.ndarray) -> float:
        a, b, n = params
        fit_r = superellipse_radius(angles, a, b, n)
        perimeter_fit = approximate_perimeter(a, b, n)
        perimeter_actual = np.sum(np.linalg.norm(np.roll(shifted, -1, axis=0) - shifted, axis=1))
        radius_loss = np.mean((radii - fit_r) ** 2)
        length_loss = (perimeter_fit - perimeter_actual) ** 2
        return radius_loss + 0.01 * length_loss  # weight for perimeter match

    result = minimize(
        objective,
        x0=[1.0, 1.0, initial_n],
        bounds=[(1e-3, None), (1e-3, None), (0.5, 10.0)],
        method='L-BFGS-B'
    )

    return {
        "center": center,
        "a": result.x[0],
        "b": result.x[1],
        "n": result.x[2],
        "success": result.success,
        "fun": result.fun
    }

def fit_shape_area_superellipse(points: np.ndarray, initial_n: float = 2.0) -> dict:
    """
    Fits a symmetric superellipse to a given set of 2D points, ensuring symmetry about the Z-axis.

    Args:
        points (np.ndarray): A 2D array of shape (N, 2) representing the points to fit.
        initial_n (float): The initial guess for the superellipse exponent (n).

    Returns:
        dict: A dictionary containing the fitted parameters:
            - 'center' (np.ndarray): The center of the fitted superellipse.
            - 'a' (float): The semi-major axis length.
            - 'b' (float): The semi-minor axis length.
            - 'n' (float): The superellipse exponent.
            - 'success' (bool): Whether the optimization was successful.
            - 'fun' (float): The value of the objective function at the solution.
    """
    # Force symmetry about Z-axis
    center_z = np.mean(points[:, 1])
    center = np.array([0.0, center_z])
    shifted = points - center

    angles = np.arctan2(shifted[:, 1], shifted[:, 0])
    radii = np.linalg.norm(shifted, axis=1)

    # Mirror points to enforce symmetry
    angles = np.concatenate([angles, -angles])
    radii = np.concatenate([radii, radii])

    area_actual = polygon_area(shifted)

    def objective(params: np.ndarray) -> float:
        a, b, n = params
        fit_r = superellipse_radius(angles, a, b, n)
        area_fit = approximate_area(a, b, n)
        shape_loss = np.mean((radii - fit_r) ** 2)
        area_loss = ((area_fit - area_actual) / area_actual) ** 2

        scale = np.mean(radii) ** 2
        return shape_loss / scale + 0.01 * area_loss

    result = minimize(
        objective,
        x0=[1.0, 1.0, initial_n],
        bounds=[(1e-3, None), (1e-3, None), (0.5, 10.0)],
        method='L-BFGS-B'
    )

    return {
        "center": center,
        "a": result.x[0],
        "b": result.x[1],
        "n": result.x[2],
        "success": result.success,
        "fun": result.fun
    }

def plot_superellipse_fit(points_3d: np.ndarray, fit_result: dict, num_samples: int = 300) -> None:
    center = fit_result["center"]
    a, b, n = fit_result["a"], fit_result["b"], fit_result["n"]

    # Convert 3D to 2D (assuming fixed X)
    points_2d = np.array([(y, z) for _, y, z in points_3d])

    # Generate superellipse points
    theta = np.linspace(0, 2 * np.pi, num_samples)
    r = (np.abs(np.cos(theta)/a)**n + np.abs(np.sin(theta)/b)**n)**(-1/n)
    x = r * np.cos(theta) + center[0]
    y = r * np.sin(theta) + center[1]

    # Plot
    plt.figure()
    plt.plot(points_2d[:, 0], points_2d[:, 1], 'go', label="Original Points")
    plt.plot(x, y, 'r-', label="Fitted Superellipse")
    plt.axis('equal')
    plt.title("Superellipse Fit to Wire")
    plt.xlabel("Y")
    plt.ylabel("Z")
    plt.grid(True)
    plt.legend()
    plt.show()


def compute_shape_properties(shape):
    props = GProp_GProps()

    # Volume
    BRepGProp.VolumeProperties_s(shape, props)
    volume = props.Mass()

    # Surface Area
    BRepGProp.SurfaceProperties_s(shape, props)
    surface_area = props.Mass()

    return {
        "volume": volume,
        "surface_area": surface_area,
    }

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Replace with your actual STEP file path
    #step_path = "../../components/aircraft/RV-7/fuselage.step"
    step_path = "../../components/aircraft/eHawk/e-Hawk Rumpf v29.step"

    # Load model
    model = load_step_model(step_path)

    surface_volume = compute_shape_properties(model.solids().first().toOCC())

    # Perform slicing
    wire_slices = slice_model_along_x(model, spacing=0.1, number_of_slices=100)

    ellipse_slices = []
    for wires in wire_slices:
        for points in wires:
            points_2d = np.array([(y, z) for (_, y, z) in points])
            result = fit_shape_area_superellipse(points_2d)
            logger.debug(f"Fitted parameters: {result}")
            plot_superellipse_fit(points_3d= np.array(points), fit_result=result, num_samples = 200)
            result['center'] = np.array([points[0][0], result['center'][0], result['center'][1]])
            ellipse_slices.append(result)
            #break # only take one wire per slice

    # convert ellipse_slices to FuselageXSec
    fuselage_xsecs = []
    for i, ellipse in enumerate(ellipse_slices):
        fuselage_xsec = asb.FuselageXSec(
            xyz_c = ellipse['center'],
            xyz_normal = np.array([1.0, 0.0, 0.0]),
            radius = None,
            width = 2. * ellipse['a'],
            height = 2. * ellipse['b'],
            shape = ellipse['n'],
            analysis_specific_options = None,
        )

        fuselage_xsecs.append(fuselage_xsec)

    asb_fuselage = asb.Fuselage(
        name="Fuselage",
        xsecs=fuselage_xsecs,
        color = None, #: Optional[Union[str, Tuple[float]]] = None,
        analysis_specific_options = None #: Optional[Dict[type, Dict[str, Any]]] = None,
    )

    asb_fuselage.draw(backend="plotly", show=True)
    logger.info(f"Fuselage surface area >> initial: {surface_volume['surface_area']}; transformed: {asb_fuselage.area_wetted()}; transformed/initial = {surface_volume['surface_area']/asb_fuselage.area_wetted()}\n"
                f"Fuselage volume       >> initial: {surface_volume['volume']}; transformed: {asb_fuselage.volume()}; transformed/initial = {surface_volume['volume']/asb_fuselage.volume()}")


    pass

