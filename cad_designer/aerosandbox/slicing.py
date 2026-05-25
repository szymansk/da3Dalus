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
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.GCPnts import GCPnts_UniformAbscissa
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Shape, TopoDS_Wire
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

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


# ---------------------------------------------------------------------------
# gh-727: Shell-tolerant slicing + XZ-profile + adaptive station picking
# ---------------------------------------------------------------------------


def _ensure_sliceable_shape(model: cq.Workplane) -> TopoDS_Shape:
    """Return a single TopoDS_Shape ready for plane-cuts.

    Accepts a Workplane wrapping either a Solid (existing CAD pipeline)
    or a collection of Surface-patches (OpenVSP STEP exports). When
    given only surfaces, sews them into a closed-as-possible Shell so
    ``BRepAlgoAPI_Section`` produces continuous outline edges.
    """
    solids = model.solids().vals()
    if solids:
        return solids[0].wrapped
    faces = model.faces().vals()
    if not faces:
        raise ValueError("STEP model has neither solids nor faces to slice.")
    sewing = BRepBuilderAPI_Sewing(0.001)
    for f in faces:
        sewing.Add(f.wrapped)
    sewing.Perform()
    return sewing.SewedShape()


def _section_outline_edges(shape: TopoDS_Shape, origin: tuple[float, float, float], normal: tuple[float, float, float]) -> list[cq.Edge]:
    """Intersect ``shape`` with the plane ``(origin, normal)`` and
    return every resulting edge wrapped as a cadquery ``Edge``.
    """
    plane = gp_Pln(gp_Pnt(*origin), gp_Dir(*normal))
    section = BRepAlgoAPI_Section(shape, plane)
    section.ComputePCurveOn1(True)
    section.Approximation(False)
    section.Build()
    edges: list[cq.Edge] = []
    exp = TopExp_Explorer(section.Shape(), TopAbs_EDGE)
    while exp.More():
        edges.append(cq.Edge(exp.Current()))
        exp.Next()
    return edges


def slice_at_x(
    shape: TopoDS_Shape, x: float, points_per_edge: int = 30
) -> list[list[tuple[float, float, float]]]:
    """Cut the shape at world X = ``x`` and return one polyline per
    outline edge (4 edges typical on a VSP fuselage — one per quadrant
    of the cross-section).
    """
    edges = _section_outline_edges(shape, (x, 0.0, 0.0), (1.0, 0.0, 0.0))
    polylines: list[list[tuple[float, float, float]]] = []
    for e in edges:
        poly = []
        for k in range(points_per_edge):
            t = k / float(points_per_edge - 1) if points_per_edge > 1 else 0.0
            p = e.positionAt(t)
            poly.append((p.x, p.y, p.z))
        polylines.append(poly)
    return polylines


def extract_xz_profile(
    shape: TopoDS_Shape, points_per_edge: int = 30
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Cut the shape at Y = 0 and return the side-profile as
    ``(top_outline, bottom_outline)``.

    Each outline is a list of ``(x, z)`` tuples sorted by X. ``top``
    is the upper envelope (max Z per X-bin), ``bottom`` the lower
    envelope. Use for curvature-aware station picking and as a
    construction reference for fuselage editing tools.
    """
    edges = _section_outline_edges(shape, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    pts_xz: list[tuple[float, float]] = []
    for e in edges:
        for k in range(points_per_edge):
            t = k / float(points_per_edge - 1) if points_per_edge > 1 else 0.0
            p = e.positionAt(t)
            pts_xz.append((p.x, p.z))
    if not pts_xz:
        return [], []
    # Sort by X, then split top/bottom by binning. Each X-bin yields a
    # max-Z (top) + min-Z (bottom) sample point.
    pts_xz.sort()
    xs = [p[0] for p in pts_xz]
    x_min, x_max = xs[0], xs[-1]
    # Bin width chosen so each bin gets ~3 samples — keeps the
    # envelope smooth without aliasing.
    n_bins = max(8, len(pts_xz) // 3)
    if x_max - x_min < 1e-9:
        return [], []
    bin_w = (x_max - x_min) / n_bins
    top: list[tuple[float, float]] = []
    bot: list[tuple[float, float]] = []
    for i in range(n_bins):
        x_lo = x_min + i * bin_w
        x_hi = x_lo + bin_w + 1e-9
        in_bin = [p for p in pts_xz if x_lo <= p[0] < x_hi]
        if not in_bin:
            continue
        x_center = sum(p[0] for p in in_bin) / len(in_bin)
        z_max = max(p[1] for p in in_bin)
        z_min = min(p[1] for p in in_bin)
        top.append((x_center, z_max))
        bot.append((x_center, z_min))
    return top, bot


def _curvature_density(
    outline: list[tuple[float, float]],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return ``(x_samples, |d²z/dx²|)`` for a side-profile outline.

    Uses central finite differences on the outline samples. Returns
    arrays of length ``len(outline) - 2`` (the endpoints have no
    central neighbours).
    """
    if len(outline) < 3:
        return np.array([]), np.array([])
    arr = np.asarray(outline, dtype=float)
    xs, zs = arr[:, 0], arr[:, 1]
    # Central second-derivative ≈ (z[i+1] - 2z[i] + z[i-1]) / Δ²
    dz2 = np.zeros(len(outline) - 2)
    for i in range(1, len(outline) - 1):
        dx1, dx2 = xs[i] - xs[i - 1], xs[i + 1] - xs[i]
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        # Non-uniform-spacing second derivative
        dz2[i - 1] = abs(
            2 * (zs[i - 1] / (dx1 * (dx1 + dx2))
                 - zs[i] / (dx1 * dx2)
                 + zs[i + 1] / (dx2 * (dx1 + dx2)))
        )
    return xs[1:-1], dz2


def adaptive_x_stations(
    top: list[tuple[float, float]],
    bot: list[tuple[float, float]],
    n_stations: int,
    curvature_weight: float = 0.7,
) -> list[float]:
    """Place ``n_stations`` X-positions weighted by side-profile curvature.

    Combines |d²z/dx²| of top + bottom envelopes into a per-X density.
    Mixes that density with a flat (uniform) baseline via
    ``curvature_weight``: ``0`` → uniform spacing, ``1`` → pure
    curvature-driven, default ``0.7`` → biased toward high-curvature
    but no zero-density gaps.

    Always includes the X bounds as stations so the endcaps land on
    actual outline endpoints.
    """
    if n_stations < 2:
        raise ValueError("adaptive_x_stations needs n_stations >= 2")
    if not top and not bot:
        raise ValueError("adaptive_x_stations needs at least one outline")

    # Pull curvature samples from both envelopes; concatenate + sort.
    samples_x: list[float] = []
    samples_w: list[float] = []
    for outline in (top, bot):
        xs, dz2 = _curvature_density(outline)
        samples_x.extend(xs.tolist())
        samples_w.extend(dz2.tolist())

    if not samples_x:
        # Pure uniform — no curvature info available.
        all_outline = top or bot
        x_min, x_max = all_outline[0][0], all_outline[-1][0]
        return [x_min + (x_max - x_min) * i / (n_stations - 1) for i in range(n_stations)]

    # Normalize curvature weights into a PDF-like density on [x_min, x_max].
    arr_x = np.asarray(samples_x)
    arr_w = np.asarray(samples_w)
    sort_idx = np.argsort(arr_x)
    arr_x = arr_x[sort_idx]
    arr_w = arr_w[sort_idx]

    x_min, x_max = arr_x.min(), arr_x.max()
    # Resample the curvature density onto a fine uniform X grid so we
    # can integrate it deterministically.
    n_grid = max(200, 4 * n_stations)
    grid = np.linspace(x_min, x_max, n_grid)
    density_curve = np.interp(grid, arr_x, arr_w, left=0.0, right=0.0)
    # Smooth a touch — neighbour-averaging cancels finite-difference noise.
    if len(density_curve) >= 5:
        kernel = np.array([1, 2, 4, 2, 1], dtype=float)
        kernel /= kernel.sum()
        density_curve = np.convolve(density_curve, kernel, mode="same")
    # Normalize density_curve so its mean = 1, then mix with uniform.
    mean_c = density_curve.mean()
    if mean_c > 1e-9:
        density_curve = density_curve / mean_c
    else:
        density_curve = np.ones_like(density_curve)
    mixed = curvature_weight * density_curve + (1.0 - curvature_weight) * 1.0

    # Integrate the mixed density to get a cumulative-distribution-like
    # mapping x → cdf; pick stations by equidistantly sampling cdf
    # values and inverting back to x.
    dx = grid[1] - grid[0] if len(grid) > 1 else 0.0
    cdf = np.cumsum(mixed) * dx
    cdf -= cdf[0]
    if cdf[-1] < 1e-12:
        # Degenerate — fall back to uniform.
        return [x_min + (x_max - x_min) * i / (n_stations - 1) for i in range(n_stations)]
    cdf /= cdf[-1]
    targets = np.linspace(0.0, 1.0, n_stations)
    return [float(np.interp(t, cdf, grid)) for t in targets]

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

    Two paths:

    * **Solid input** — uses the original ``Workplane.split(keepTop=True)``
      path which returns one closed wire per slice. Kept verbatim to
      preserve the RV-7 / Punisher / eHawk quality-test fidelity.
    * **Shell input** (gh-727) — falls back to ``BRepAlgoAPI_Section``
      which returns N quadrant edges per slice. Used for OpenVSP STEP
      Open Shells where ``.split()`` fails.
    """
    if not shape.solids().vals():
        # Shell-only path (gh-727)
        sliceable = _ensure_sliceable_shape(shape)
        bb = cq.Shape(sliceable).BoundingBox()
        xmin, xmax = bb.xmin, bb.xmax
        if number_of_slices is not None:
            number_of_slices = max(number_of_slices, 2)
            spacing = (xmax - xmin) / (number_of_slices - 1)
        slices = []
        x = xmin
        max_iterations = int((xmax - xmin) / spacing) + 2 if spacing > 0 else 1000
        for _ in range(max_iterations):
            if x > xmax + spacing * 0.01:
                break
            try:
                polylines = slice_at_x(sliceable, x, points_per_edge=points_per_slice)
            except Exception as exc:
                logger.warning(f"Section slice failed at x={x:.5f}: {exc}")
                x += spacing
                continue
            if polylines:
                slices.append(polylines)
            x += spacing
        logger.info(f"Section slicing complete: {len(slices)} slices "
                    f"from x={xmin:.4f} to x={xmax:.4f}")
        return slices

    # Solid path — preserve original behaviour byte-for-byte
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
        bounds=[(1e-3, None), (1e-3, None), (0.5, 8.0)],
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
        bounds=[(1e-3, None), (1e-3, None), (0.5, 8.0)],
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

        # Smoothness term (gh-727: normalised relative, not absolute.
        # Old absolute form ``(a-a_p)²`` was unit-dependent — for mm
        # inputs (typical from VSP STEP exports) a 30 mm change gave a
        # 900-unit penalty that dominated the shape-loss entirely and
        # locked subsequent slices to the previous a/b. Relative form
        # is scale-invariant: a 10% change costs 0.01 regardless of
        # whether the body is in mm or m.)
        if prev_params:
            a_p, b_p, n_p = prev_params["a"], prev_params["b"], prev_params["n"]
            smoothness_loss = (
                ((a / max(a_p, 1e-9)) - 1.0) ** 2
                + ((b / max(b_p, 1e-9)) - 1.0) ** 2
                + ((n - n_p) / max(n_p, 1e-9)) ** 2
            )
            loss += smoothness_weight * smoothness_loss

        return loss

    # gh-727: data-driven initial guess. The old x0=[1,1,n] anchored
    # the optimizer at 1 unit half-axes — fine when inputs are in
    # metres (0–2 m typical), catastrophic when inputs are in mm (100–
    # 300 mm typical) because the smoothness term then pinned every
    # subsequent slice to the previous a/b. Bounding-box-derived
    # initial puts L-BFGS-B in the right neighborhood for any scale.
    if shifted.size:
        a_init = max(float(np.max(np.abs(shifted[:, 0]))), 1e-3)
        b_init = max(float(np.max(np.abs(shifted[:, 1]))), 1e-3)
    else:
        a_init = b_init = 1.0
    x0 = [a_init, b_init, initial_n]

    result = minimize(
        objective,
        x0=x0,
        bounds=[(1e-3, None), (1e-3, None), (0.5, 8.0)],
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
    *,
    adaptive: bool = False,
    curvature_weight: float = 0.7,
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

    # Compute original geometry properties (Shell-tolerant: Volume is
    # only defined for closed Solids — fall back to surface-area alone
    # when given an Open Shell from VSP).
    solids = model.solids().vals()
    if solids:
        # cq.Solid.wrapped is the OCP shape; older code used the
        # since-removed ``.toOCC()`` accessor on Workplane().solids().first().
        first_solid = solids[0]
        occ_shape = getattr(first_solid, "wrapped", None) or first_solid.toOCC()
        original_props = compute_shape_properties(occ_shape)
    else:
        from OCP.GProp import GProp_GProps as _GProp
        from OCP.BRepGProp import BRepGProp as _BRepGProp
        faces_shape = _ensure_sliceable_shape(model)
        sa_props = _GProp()
        _BRepGProp.SurfaceProperties_s(faces_shape, sa_props)
        original_props = {"volume": 0.0, "surface_area": sa_props.Mass()}
        logger.info(
            "No Solid found in STEP — falling back to Shell-only metrics "
            "(volume will be 0; surface area = %.4f).",
            original_props["surface_area"],
        )

    # gh-727: two slicer dispatches.
    #
    # ``via_shell`` (Section-based) is required for VSP STEP imports —
    # those carry only Surface patches, no Solid. Section-Edges from
    # one slice are 4 quadrants of ONE outline and must be flattened.
    #
    # The legacy Workplane.split path is byte-stable for the existing
    # RV-7 / Punisher / eHawk fuselage-slice tests — there a single
    # wire_set entry is one closed wire (outer contour); inner loops
    # / disjoint section components also show up here but we keep the
    # historic "take first wire" semantics.
    has_solid = bool(model.solids().vals())
    via_shell = (not has_solid) or adaptive
    if via_shell:
        sliceable = _ensure_sliceable_shape(model)
        if adaptive:
            top, bot = extract_xz_profile(sliceable)
            x_stations = adaptive_x_stations(
                top, bot, n_stations=number_of_slices,
                curvature_weight=curvature_weight,
            )
        else:
            bb = cq.Shape(sliceable).BoundingBox()
            x_stations = [
                bb.xmin + (bb.xmax - bb.xmin) * i / (number_of_slices - 1)
                for i in range(number_of_slices)
            ]
        wire_slices = []
        for x in x_stations:
            polylines = slice_at_x(sliceable, x, points_per_edge=points_per_slice)
            if polylines:
                wire_slices.append(polylines)
    else:
        wire_slices = slice_model_along_x(
            model, number_of_slices=number_of_slices, points_per_slice=points_per_slice
        )

    # Fit superellipses and build xsec dicts.
    #
    # * ``via_shell`` slices have polylines = quadrant edges of one
    #   outline → flatten into one point cloud.
    # * Solid-path slices have polylines = full closed wires
    #   (potentially with inner loops or multiple disjoint sections);
    #   keep historic "take first wire" semantics so the existing
    #   fuselage-slice quality tests stay byte-stable.
    xsec_dicts = []
    prev_params = None
    for wire_set in wire_slices:
        if not wire_set:
            continue
        if via_shell:
            slice_points = [pt for poly in wire_set for pt in poly]
        else:
            slice_points = list(wire_set[0])
        if not slice_points:
            continue
        x = float(slice_points[0][0])
        points_2d = np.array([(y, z) for (_, y, z) in slice_points])
        fit = fit_shape_area_superellipse(points_2d, prev_params=prev_params)
        xyz = [x, float(fit["center"][0]), float(fit["center"][1])]
        xsec_dicts.append({
            "xyz": xyz,
            "a": float(fit["a"]),
            "b": float(fit["b"]),
            "n": float(np.clip(fit["n"], 0.5, 8.0)),
        })
        prev_params = fit

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

