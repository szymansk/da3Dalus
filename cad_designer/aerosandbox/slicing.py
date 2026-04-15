import cadquery as cq
import os
import matplotlib.pyplot as plt
import numpy as np
from typing import Sequence, Optional

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

def get_bounding_box_dims(shape: cq.Shape) -> dict[str, float]:
    """Return bounding box dimensions per axis."""
    bb = shape.BoundingBox()
    return {
        "x": bb.xmax - bb.xmin,
        "y": bb.ymax - bb.ymin,
        "z": bb.zmax - bb.zmin,
    }


def detect_longest_axis(shape: cq.Shape) -> str:
    """Detect the longest bounding box axis (x, y, or z)."""
    dims = get_bounding_box_dims(shape)
    return max(dims, key=dims.get)


def slice_model_along_x(
    shape: cq.Workplane,
    spacing: float = 0.1,
    number_of_slices: int = None,
    points_per_slice: int = 30,
) -> list[list[tuple[float, float, float]]]:
    """Slice a model along the X axis into cross-section wire points.

    Bug fixes applied:
    - Starts at xmin (not x=0)
    - Terminates at xmax (not on identical-slice heuristic)
    """
    xmin, xmax = get_x_bounds(shape.val())

    if number_of_slices is not None:
        number_of_slices = max(number_of_slices, 2)
        spacing = (xmax - xmin) / (number_of_slices - 1)
        logger.info(f"Slicing with {number_of_slices} slices, spacing = {spacing:.5f}")

    slices = []
    x = xmin
    max_iterations = int((xmax - xmin) / spacing) + 2 if spacing > 0 else 1000

    for _ in range(max_iterations):
        if x > xmax + spacing * 0.01:
            break

        try:
            offset_from_min_face = x - xmin
            if offset_from_min_face < 1e-9:
                wires = shape.faces("<X").wires().all()
            else:
                wires = (
                    shape.faces("<X")
                    .workplane(offset=-offset_from_min_face)
                    .split(keepTop=True)
                    .faces(">X")
                    .wires()
                    .all()
                )
        except Exception as exc:
            logger.warning(f"Slicing failed at x={x:.5f}: {exc}")
            x += spacing
            continue

        wire_slice = []
        for wire in wires:
            points = discretize_wire(wire.toOCC(), points_per_slice)
            tuple_points = [(pt.X(), pt.Y(), pt.Z()) for pt in points]
            wire_slice.append(tuple_points)

        if wire_slice:
            slices.append(wire_slice)
            logger.debug(f"Slice at x={x:.5f}: {len(wire_slice)} wire(s)")

        x += spacing

    logger.info(f"Slicing complete: {len(slices)} slices from x={xmin:.4f} to x={xmax:.4f}")
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

def fit_shape_area_superellipse(points: np.ndarray, initial_n: float = 2.0, prev_params: Optional[dict] = None, smoothness_weight: float = 0.1) -> dict:
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
        loss = shape_loss / (np.mean(radii) ** 2) + 0.01 * area_loss

        # Smoothness term
        if prev_params:
            a_p, b_p, n_p = prev_params["a"], prev_params["b"], prev_params["n"]
            smoothness_loss = (a - a_p) ** 2 + (b - b_p) ** 2 + (n - n_p) ** 2
            loss += smoothness_weight * smoothness_loss

        return loss

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

def slice_step_to_fuselage(
    step_path: str,
    number_of_slices: int = 50,
    points_per_slice: int = 30,
    slice_axis: str = "auto",
    fuselage_name: str = "Imported Fuselage",
) -> tuple[list[dict], dict]:
    """Load STEP file, slice along longitudinal axis, fit symmetric
    superellipses, and return FuselageXSec dicts + fidelity metrics.

    The pipeline:
    1. load_step_model(step_path)
    2. Auto-detect or apply specified slice_axis
    3. slice_model_along_x(model, number_of_slices, points_per_slice)
    4. For each slice: fit_shape_area_superellipse(points_2d)
    5. Convert fitted params to FuselageXSec format (xyz, a, b, n)
    6. Compute volume/area for original and reconstructed geometry

    Args:
        step_path: Path to STEP file.
        number_of_slices: Number of cross-sections to cut.
        points_per_slice: Points per wire discretization.
        slice_axis: "x", "y", "z", or "auto" (longest bounding box axis).
        fuselage_name: Name for the resulting fuselage.

    Returns:
        (xsec_dicts, metrics) where xsec_dicts is a list of
        {"xyz": [x,y,z], "a": float, "b": float, "n": float} dicts
        and metrics contains volume/area comparison.
    """
    model = load_step_model(step_path)

    # Auto-detect or validate slice axis
    if slice_axis == "auto":
        slice_axis = detect_longest_axis(model.val())
        logger.info(f"Auto-detected slice axis: {slice_axis}")

    # Rotate model so slicing always happens along X
    if slice_axis == "y":
        model = model.rotateAboutCenter((0, 0, 1), 90)
        logger.info("Rotated model: Y → X")
    elif slice_axis == "z":
        model = model.rotateAboutCenter((0, 1, 0), -90)
        logger.info("Rotated model: Z → X")
    elif slice_axis != "x":
        raise ValueError(f"Invalid slice_axis: {slice_axis}. Must be 'x', 'y', 'z', or 'auto'.")

    # Compute original geometry properties
    original_props = compute_shape_properties(model.solids().first().toOCC())

    # Slice
    wire_slices = slice_model_along_x(
        model, number_of_slices=number_of_slices, points_per_slice=points_per_slice
    )

    # Fit superellipses and build xsec dicts
    xsec_dicts = []
    prev_params = None
    for wire_set in wire_slices:
        for points in wire_set:
            points_2d = np.array([(y, z) for (_, y, z) in points])
            fit = fit_shape_area_superellipse(points_2d, prev_params=prev_params)
            xyz = [float(points[0][0]), float(fit["center"][0]), float(fit["center"][1])]
            xsec_dicts.append({
                "xyz": xyz,
                "a": float(fit["a"]),
                "b": float(fit["b"]),
                "n": float(np.clip(fit["n"], 0.5, 10.0)),
            })
            prev_params = fit
            break  # take first wire per slice (outermost contour)

    # Reconstruct as asb.Fuselage for fidelity comparison
    fuselage_xsecs = []
    for xsec in xsec_dicts:
        fuselage_xsecs.append(asb.FuselageXSec(
            xyz_c=xsec["xyz"],
            xyz_normal=np.array([1.0, 0.0, 0.0]),
            radius=None,
            width=2.0 * xsec["a"],
            height=2.0 * xsec["b"],
            shape=xsec["n"],
        ))

    asb_fuselage = asb.Fuselage(name=fuselage_name, xsecs=fuselage_xsecs)

    reconstructed_volume = asb_fuselage.volume()
    reconstructed_area = asb_fuselage.area_wetted()

    metrics = {
        "original_volume": original_props["volume"],
        "original_area": original_props["surface_area"],
        "reconstructed_volume": reconstructed_volume,
        "reconstructed_area": reconstructed_area,
        "volume_ratio": reconstructed_volume / original_props["volume"] if original_props["volume"] > 0 else 0,
        "area_ratio": reconstructed_area / original_props["surface_area"] if original_props["surface_area"] > 0 else 0,
    }

    logger.info(
        f"Fuselage '{fuselage_name}': {len(xsec_dicts)} sections, "
        f"volume ratio={metrics['volume_ratio']:.3f}, area ratio={metrics['area_ratio']:.3f}"
    )

    return xsec_dicts, metrics


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])

    step_path = "../../components/aircraft/eHawk/e-Hawk Rumpf v29.step"
    xsecs, metrics = slice_step_to_fuselage(step_path, number_of_slices=50)

    print(f"\n{'='*60}")
    print(f"Sections: {len(xsecs)}")
    print(f"Volume:   original={metrics['original_volume']:.6f}  reconstructed={metrics['reconstructed_volume']:.6f}  ratio={metrics['volume_ratio']:.3f}")
    print(f"Area:     original={metrics['original_area']:.6f}  reconstructed={metrics['reconstructed_area']:.6f}  ratio={metrics['area_ratio']:.3f}")

