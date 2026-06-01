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


def _section_outline_edges(
    shape: TopoDS_Shape, origin: tuple[float, float, float], normal: tuple[float, float, float]
) -> list[cq.Edge]:
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
    # Clamp ``points_per_edge`` against a sane ceiling — caller-supplied
    # values bound the inner loop, SonarQube flags that as a controllable
    # iteration source. 4096 is well past any visual-quality need.
    n_pts = max(2, min(int(points_per_edge), 4096))
    edges = _section_outline_edges(shape, (x, 0.0, 0.0), (1.0, 0.0, 0.0))
    polylines: list[list[tuple[float, float, float]]] = []
    for e in edges:
        poly = []
        for k in range(n_pts):
            t = k / float(n_pts - 1) if n_pts > 1 else 0.0
            p = e.positionAt(t)
            poly.append((p.x, p.y, p.z))
        polylines.append(poly)
    return polylines


def arc_length_weights(points_2d: np.ndarray) -> np.ndarray:
    """Per-point weight equal to the distance to its nearest neighbour
    (gh-732). Approximates arc-length-uniform sampling without
    discarding any data.

    Background. ``slice_at_x`` discretises each Section-edge into a
    fixed ``points_per_edge`` count by *parameter*. A short edge
    (e.g. the 2 mm tall plateau line at the front of the cessna
    cockpit) gets the same 30 points as a 1 m long body edge — so the
    flattened cloud has 40 over-sampled points clustered on the
    plateau plus 80 thinly-spread body points. Unweighted statistics
    (mean centre, RMS residual) over-represent the plateau by 5–10×.

    Solution: weight each point by how much arc length it actually
    represents. The nearest-neighbour distance is a robust local
    estimate of that arc spacing. Sum of weights then approximates
    the total perimeter, and weighted means / variances behave as
    if we'd sampled the outline uniformly by arc length.

    Returns a 1-D weight array of length ``len(points_2d)``. All
    weights are strictly positive (a tiny floor avoids division by
    zero in pathological inputs).
    """
    pts = np.asarray(points_2d, dtype=float)
    if len(pts) < 2:
        return np.ones(len(pts))
    diffs = pts[:, None, :] - pts[None, :, :]
    dists = np.linalg.norm(diffs, axis=-1)
    np.fill_diagonal(dists, np.inf)
    nn = dists.min(axis=1)
    # Tiny positive floor to keep the weights well-defined when two
    # samples happen to coincide exactly.
    floor = 1e-6 * float(nn.max() if nn.size and np.isfinite(nn.max()) else 1.0)
    return np.maximum(nn, floor)


def thin_oversampled_points(points_2d: np.ndarray, radius_ratio: float = 0.2) -> np.ndarray:
    """Drop points that are over-sampled relative to the cloud's
    natural inter-point spacing (gh-732).

    Background. ``slice_at_x`` discretises each Section-edge into
    ``points_per_edge`` (default 30) points by *parameter*, not by
    arc length. A long edge spreads its 30 points over its full
    physical length (~50 mm spacing on a Cessna fuselage), while a
    short edge — like the canopy-base plateau line that appears at
    the front of the cockpit (~2 mm tall in z) — also gets 30 points
    but all clustered together. When all polylines are flattened
    into one cloud for the super-ellipse fit, the over-sampled
    plateau dominates the arithmetic centroid and pulls it upward,
    producing the deformed ``xsec[27]`` we see on the cessna.

    Heuristic. The MAXIMUM nearest-neighbour distance ``max_nn`` is
    a good estimate of the natural spacing in the well-sampled
    regions of the outline (long edges). Points whose neighbours
    are way closer than that live in an over-sampled cluster.

    Walk the cloud; for each point, count how many other points are
    within ``radius = max_nn * radius_ratio``. With a well-spaced
    outline that count is 0–2 (no over-sampling). In a dense plateau
    cluster the count blows up. Greedy thinning then keeps the first
    representative of each cluster and drops the rest.

    Returns the thinned 2-D array. Pass-through for tiny clouds.
    """
    pts = np.asarray(points_2d, dtype=float)
    if len(pts) < 8:
        return pts

    diffs = pts[:, None, :] - pts[None, :, :]
    dists = np.linalg.norm(diffs, axis=-1)
    np.fill_diagonal(dists, np.inf)
    nn = dists.min(axis=1)
    max_nn = float(nn.max())
    if max_nn <= 0 or not np.isfinite(max_nn):
        return pts

    radius = max_nn * radius_ratio
    keep = np.ones(len(pts), dtype=bool)
    for i in range(len(pts)):
        if not keep[i]:
            continue
        # Drop every later point within radius — that point is one
        # of the over-sampled duplicates of ``i``.
        too_close = (dists[i] < radius) & keep
        too_close[: i + 1] = False
        keep[too_close] = False
    return pts[keep]


def select_outer_contour(
    polylines: list[list[tuple[float, float, float]]],
) -> list[list[tuple[float, float, float]]]:
    """Drop inner / disjoint contours so the super-ellipse fitter sees
    only the OUTER fuselage skin (gh-732).

    A Section-cut at a VSP fuselage's canopy / cowling transition can
    produce multiple disjoint closed outlines: the main fuselage skin
    AND a separate small loop for the canopy bubble (when VSP renders
    the canopy as a separate inner feature). Flattening all points
    into one cloud biases the super-ellipse centroid upward and
    yields a deformed xsec.

    Heuristic: cluster polylines by centroid proximity (threshold =
    25 % of the slice's overall yz-extent diagonal), then keep only
    the cluster whose collective point cloud has the largest extent.
    Single-cluster slices pass through unchanged.
    """
    # A single closed outline cuts as ~4 polylines (one per quadrant);
    # below this threshold treat the slice as single-contour and pass
    # through unchanged. Multi-contour slices (canopy + cowling +
    # fuselage at the same x) produce ≥ 8 edges and need filtering.
    if len(polylines) <= 6:
        return polylines

    centroids = []
    for poly in polylines:
        if not poly:
            centroids.append(np.array([0.0, 0.0]))
            continue
        pts = np.array([(p[1], p[2]) for p in poly])
        centroids.append(pts.mean(axis=0))
    centroids = np.array(centroids)

    all_yz = np.array([(p[1], p[2]) for poly in polylines for p in poly if poly])
    if all_yz.size == 0:
        return polylines
    diag = float(np.linalg.norm(np.ptp(all_yz, axis=0)))
    # 50 % of the bbox diagonal is conservative: keeps the 4 quadrants
    # of a single outline together (their pairwise centroid distance
    # is ≲ half the diagonal) while still separating a canopy bubble
    # (sitting clearly above the fuselage by ≳ a full body diagonal).
    threshold = 0.50 * max(diag, 1e-9)

    cluster_id = [-1] * len(polylines)
    n_clusters = 0
    for i in range(len(polylines)):
        if cluster_id[i] != -1:
            continue
        cluster_id[i] = n_clusters
        for j in range(i + 1, len(polylines)):
            if cluster_id[j] != -1:
                continue
            if float(np.linalg.norm(centroids[j] - centroids[i])) < threshold:
                cluster_id[j] = n_clusters
        n_clusters += 1

    if n_clusters <= 1:
        return polylines

    # Pick the cluster that **encloses the longitudinal axis** —
    # i.e. whose centroid is closest to (y=0, z=fuselage_axis_z). The
    # fuselage's outer skin always wraps around the axis; canopy /
    # cowling sub-features are offset above (z > 0) with their
    # centroids well clear of the body's centerline. Initial naive
    # "largest extent" heuristic was wrong: a tall narrow canopy can
    # legitimately have a larger y-z diagonal than the fuselage skin
    # at the same x.
    #
    # Reference centerline: the all-points centroid is a robust
    # estimator because the fuselage outline contributes more points
    # than the small inner sub-features.
    all_pts = np.array([(p[1], p[2]) for poly in polylines for p in poly if poly])
    axis_ref = all_pts.mean(axis=0)
    best_cluster = -1
    best_distance = float("inf")
    for k in range(n_clusters):
        cluster_centroids = np.array(
            [centroids[i] for i in range(len(polylines)) if cluster_id[i] == k]
        )
        if cluster_centroids.size == 0:
            continue
        cluster_centroid = cluster_centroids.mean(axis=0)
        distance = float(np.linalg.norm(cluster_centroid - axis_ref))
        if distance < best_distance:
            best_distance = distance
            best_cluster = k

    return [poly for i, poly in enumerate(polylines) if cluster_id[i] == best_cluster]


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
    # Same loop-bound clamp as ``slice_at_x`` (gh-727).
    n_pts = max(2, min(int(points_per_edge), 4096))
    edges = _section_outline_edges(shape, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    pts_xz: list[tuple[float, float]] = []
    for e in edges:
        for k in range(n_pts):
            t = k / float(n_pts - 1) if n_pts > 1 else 0.0
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
            2
            * (
                zs[i - 1] / (dx1 * (dx1 + dx2))
                - zs[i] / (dx1 * dx2)
                + zs[i + 1] / (dx2 * (dx1 + dx2))
            )
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

    # The outline endpoints define the full X range — pin those so
    # stations[0] and stations[-1] hit the actual body bounds, not
    # the inner curvature-sample bounds. (Curvature is undefined at
    # endpoints because central differences need both neighbours.)
    all_outline = top or bot
    x_min = min(p[0] for p in (top + bot)) if (top or bot) else 0.0
    x_max = max(p[0] for p in (top + bot)) if (top or bot) else 1.0
    if x_max - x_min < 1e-9:
        return [x_min for _ in range(n_stations)]

    if not samples_x:
        # Pure uniform — no curvature info available.
        return [x_min + (x_max - x_min) * i / (n_stations - 1) for i in range(n_stations)]

    # Normalize curvature weights into a PDF-like density on [x_min, x_max].
    arr_x = np.asarray(samples_x)
    arr_w = np.asarray(samples_w)
    sort_idx = np.argsort(arr_x)
    arr_x = arr_x[sort_idx]
    arr_w = arr_w[sort_idx]
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
        logger.info(
            f"Section slicing complete: {len(slices)} slices from x={xmin:.4f} to x={xmax:.4f}"
        )
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
    vertices: Sequence[tuple[float, float]], exponent: float = 2.5, a: float = 1.0, b: float = 1.0
) -> NDArray[np.float64]:
    vertices = np.array(vertices)
    center = np.mean(vertices, axis=0)
    normalized = vertices - center
    scale = np.max(np.abs(normalized), axis=0)
    normalized /= scale  # normalize to [-1, 1] box

    angles = np.arctan2(normalized[:, 1], normalized[:, 0])
    super_radii = (
        np.abs(np.cos(angles) / a) ** exponent + np.abs(np.sin(angles) / b) ** exponent
    ) ** (-1 / exponent)
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
        dr_dtheta = (
            n
            * r
            * (
                (np.abs(np.sin(theta) / b) ** (n - 1) * np.cos(theta) / b)
                - (np.abs(np.cos(theta) / a) ** (n - 1) * np.sin(theta) / a)
            )
        )
        return np.sqrt(r**2 + dr_dtheta**2)

    return quad(integrand, 0, 2 * np.pi, limit=200)[0]


def approximate_area(a: float, b: float, n: float) -> float:
    # Approximation using Gamma function
    return 4 * a * b * (gamma(1 + 1 / n) ** 2) / gamma(1 + 2 / n)


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
        radius_loss = np.mean((radii - fit_r) ** 2)
        length_loss = (perimeter_fit - perimeter_actual) ** 2
        return radius_loss + 0.01 * length_loss

    result = minimize(
        objective,
        x0=[1.0, 1.0, initial_n],
        bounds=[(1e-3, None), (1e-3, None), (0.5, 8.0)],
        method="L-BFGS-B",
    )

    return {
        "center": center,
        "a": result.x[0],
        "b": result.x[1],
        "n": result.x[2],
        "success": result.success,
        "fun": result.fun,
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
        method="L-BFGS-B",
    )

    return {
        "center": center,
        "a": result.x[0],
        "b": result.x[1],
        "n": result.x[2],
        "success": result.success,
        "fun": result.fun,
    }


def fit_shape_area_superellipse(
    points: np.ndarray,
    initial_n: float = 2.0,
    prev_params: Optional[dict] = None,
    smoothness_weight: float = 0.1,
) -> dict:
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
    # gh-732: axis-anchored super-ellipse fit.
    #
    # The super-ellipse ``|y/a|^n + |z/b|^n = 1`` passes by definition
    # through its four cardinal extremes (±a, 0) and (0, ±b). We
    # exploit that algebraically: rather than letting the optimiser
    # roam in a / b / n space (where unweighted least squares pulls
    # the curve away from the actual extremes when the point cloud is
    # asymmetric — see the cessna xsec-28 deformation), we *anchor*
    #
    #     cy = 0                       (forced y-symmetry of fuselage)
    #     cz = (z_max + z_min) / 2     (bbox mid so N/S are equidistant)
    #     a  = max |y - cy|            (E/W extremes touch the curve)
    #     b  = (z_max - z_min) / 2     (N/S extremes touch the curve)
    #
    # leaving only ``n`` to optimise — the curve fit then becomes a
    # 1-D search for the exponent that best matches the in-between
    # points. Arc-length weights still apply to the residual so that
    # densely-sampled regions (canopy plateau lines) don't dominate
    # the n estimate.
    weights = arc_length_weights(points)

    # gh-732: for main-axis fuselages the cross-section is symmetric
    # about y = 0 and the weighted mean of y is ≈ 0. For off-axis
    # sub-fuselages (cessna MainFairing at y = +1.27 m, NoseFairing at
    # similar offsets) the body lives well clear of the symmetry plane
    # and ``cy`` must follow it — otherwise ``a = max|y - cy|`` jumps
    # to the distance from the world origin and the fit becomes
    # nonsense (a = 1.38 m for a 0.11 m wide fairing). Using the
    # weighted mean as ``cy`` handles both cases without a heuristic.
    cy = float(np.average(points[:, 0], weights=weights))
    z_min = float(points[:, 1].min())
    z_max = float(points[:, 1].max())
    cz = 0.5 * (z_min + z_max)
    center = np.array([cy, cz])
    shifted = points - center

    a_fixed = float(np.max(np.abs(shifted[:, 0])))
    b_fixed = float(np.max(np.abs(shifted[:, 1])))

    angles = np.arctan2(shifted[:, 1], shifted[:, 0])
    radii = np.linalg.norm(shifted, axis=1)

    # Mirror across the local y-axis (no longer the global y=0 line —
    # the centroid moves to follow the body). Weights mirror with them.
    angles = np.concatenate([angles, -angles])
    radii = np.concatenate([radii, radii])
    weights_full = np.concatenate([weights, weights])
    weight_sum = float(weights_full.sum()) or 1.0
    radii_norm_sq = max(float(np.sum(weights_full * radii**2) / weight_sum), 1e-9)

    def objective(params: np.ndarray) -> float:
        n_val = float(params[0])
        fit_r = superellipse_radius(angles, a_fixed, b_fixed, n_val)
        shape_loss = float(np.sum(weights_full * (radii - fit_r) ** 2) / weight_sum)
        loss = shape_loss / radii_norm_sq

        # Optional smoothness term — unused in the current ``slice_step_*``
        # pipeline but kept for backwards-compat with callers that still
        # pass ``prev_params``. Relative / scale-invariant form.
        if prev_params:
            n_p = prev_params.get("n", n_val)
            loss += smoothness_weight * ((n_val - n_p) / max(n_p, 1e-9)) ** 2

        return loss

    # Single-parameter optimisation: only n is free (a, b, cy, cz are
    # anchored to the contour's bounding box).
    result = minimize(
        objective,
        x0=[float(initial_n)],
        bounds=[(0.5, 8.0)],
        method="L-BFGS-B",
    )

    return {
        "center": center,
        "a": a_fixed,
        "b": b_fixed,
        "n": float(result.x[0]),
        "success": bool(result.success),
        "fun": float(result.fun),
    }


def plot_superellipse_fit(points_3d: np.ndarray, fit_result: dict, num_samples: int = 300) -> None:
    center = fit_result["center"]
    a, b, n = fit_result["a"], fit_result["b"], fit_result["n"]

    # Convert 3D to 2D (assuming fixed X)
    points_2d = np.array([(y, z) for _, y, z in points_3d])

    # Generate superellipse points
    theta = np.linspace(0, 2 * np.pi, num_samples)
    r = (np.abs(np.cos(theta) / a) ** n + np.abs(np.sin(theta) / b) ** n) ** (-1 / n)
    x = r * np.cos(theta) + center[0]
    y = r * np.sin(theta) + center[1]

    # Plot
    plt.figure()
    plt.plot(points_2d[:, 0], points_2d[:, 1], "go", label="Original Points")
    plt.plot(x, y, "r-", label="Fitted Superellipse")
    plt.axis("equal")
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
                top,
                bot,
                n_stations=number_of_slices,
                curvature_weight=curvature_weight,
            )
        else:
            bb = cq.Shape(sliceable).BoundingBox()
            # Clamp the slice-station count so a caller-controlled
            # ``number_of_slices`` can't drive an unbounded loop.
            n_stations = max(2, min(int(number_of_slices), 4096))
            x_stations = [
                bb.xmin + (bb.xmax - bb.xmin) * i / (n_stations - 1) for i in range(n_stations)
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
    #
    # gh-732 bug-fix: each slice is fitted **independently** — no
    # ``prev_params`` chaining. The smoothness term in
    # ``fit_shape_area_superellipse`` is a causal forward bias that
    # pins each slice's (a, b, n) toward the previous slice's fit.
    # The nose slice is tiny (a few mm), so subsequent slices stay
    # 50–80 % too small for the next 5-6 stations until the optimizer
    # finally outgrows the degenerate anchor. Independent fitting is
    # both correct in scope (the slicer has enough resolution that
    # smoothness emerges from the data) and trivially parallelisable.
    xsec_dicts = []
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
        fit = fit_shape_area_superellipse(points_2d, prev_params=None)
        xyz = [x, float(fit["center"][0]), float(fit["center"][1])]
        xsec_dicts.append(
            {
                "xyz": xyz,
                "a": float(fit["a"]),
                "b": float(fit["b"]),
                "n": float(np.clip(fit["n"], 0.5, 8.0)),
            }
        )

    # Reconstruct as asb.Fuselage for fidelity comparison
    fuselage_xsecs = []
    for xsec in xsec_dicts:
        fuselage_xsecs.append(
            asb.FuselageXSec(
                xyz_c=xsec["xyz"],
                xyz_normal=np.array([1.0, 0.0, 0.0]),
                radius=None,
                width=2.0 * xsec["a"],
                height=2.0 * xsec["b"],
                shape=xsec["n"],
            )
        )

    asb_fuselage = asb.Fuselage(name=fuselage_name, xsecs=fuselage_xsecs)

    reconstructed_volume = asb_fuselage.volume()
    reconstructed_area = asb_fuselage.area_wetted()

    metrics = {
        "original_volume": original_props["volume"],
        "original_area": original_props["surface_area"],
        "reconstructed_volume": reconstructed_volume,
        "reconstructed_area": reconstructed_area,
        "volume_ratio": reconstructed_volume / original_props["volume"]
        if original_props["volume"] > 0
        else 0,
        "area_ratio": reconstructed_area / original_props["surface_area"]
        if original_props["surface_area"] > 0
        else 0,
    }

    logger.info(
        f"Fuselage '{fuselage_name}': {len(xsec_dicts)} sections, "
        f"volume ratio={metrics['volume_ratio']:.3f}, area ratio={metrics['area_ratio']:.3f}"
    )

    return xsec_dicts, metrics


def vsp_anchored_x_stations(
    handler_xsecs: list[dict],
    total_stations: int,
    *,
    scale_to_mm: bool = True,
) -> list[float]:
    """X-stations driven by VSP handler anchors (gh-732).

    Each handler xsec position is a **mandatory** anchor so the
    slicer's downstream xsec list contains the VSP-defined positions
    exactly. The remaining budget is distributed between consecutive
    anchors weighted by *shape change*: ``|Δa| + |Δb| + |Δy| + |Δz|``
    plus a baseline term so a section with zero shape change still
    gets a few interpolation points.

    Inputs:
      * ``handler_xsecs`` — list of dicts ``{"xyz": [x, y, z], "a", "b", "n"}``,
        coordinates in metres (FuselageSchema convention).
      * ``total_stations`` — global budget. Handler-anchor count is
        subtracted to determine the intermediate budget.
      * ``scale_to_mm`` — convert the returned stations to cadquery's
        internal mm convention (default True, so the result drops
        straight into ``slice_at_x``).

    Returns x stations sorted ascending. Always includes every handler
    anchor; never produces duplicates.
    """
    if len(handler_xsecs) < 2:
        return []

    anchors = sorted(
        (
            (
                float(xs["xyz"][0]),
                float(xs["xyz"][1]),
                float(xs["xyz"][2]),
                float(xs["a"]),
                float(xs["b"]),
            )
            for xs in handler_xsecs
        ),
        key=lambda t: t[0],
    )

    n_sections = len(anchors) - 1
    weights: list[float] = []
    # Find the body-typical scale so the tip-boost has a reference.
    # Use the median (a + b) over all non-degenerate anchors so a
    # single bogus anchor doesn't skew the calibration.
    body_dim_median = float(np.median([a + b for _, _, _, a, b in anchors if a + b > 1e-3])) or 1.0
    tip_threshold = 0.15 * body_dim_median  # below this, anchor is a tip
    for i in range(n_sections):
        x_a, y_a, z_a, a_a, b_a = anchors[i]
        x_b, y_b, z_b, a_b, b_b = anchors[i + 1]
        delta_shape = abs(a_b - a_a) + abs(b_b - b_a)
        delta_position = abs(y_b - y_a) + abs(z_b - z_a)
        # Baseline so empty sections (rare but possible) still get a
        # couple of points. Scaled by section length so big featureless
        # sections (tail boom) still get density-proportional coverage —
        # but the length contribution is **capped** at the body's typical
        # cross-section size (gh-804): a long, featureless mid-body (e.g.
        # Romo's 9 m constant section) otherwise dominates the budget and
        # starves the short, highly-curved nose-body fillet next to it,
        # which then renders as a kink.
        section_len = max(abs(x_b - x_a), 1e-6)
        baseline = 0.3 * min(section_len, body_dim_median)
        weight = delta_shape + delta_position + baseline
        # Tip-cap boost (gh-732): sections that include the nose tip or
        # tail tip (a+b at one anchor below ~15% of the body's typical
        # size) curve rapidly from a point to a finite cross-section.
        # The asb.Fuselage's cone-frustum interpolation between sparse
        # xsecs systematically under-estimates the surface area there.
        # Boost the weight ~4x so the budgeter pours intermediate
        # stations into these sections.
        size_a = a_a + b_a
        size_b = a_b + b_b
        if size_a < tip_threshold or size_b < tip_threshold:
            weight *= 4.0
        # Rapid-shape-change boost (gh-732): when the cross-section
        # grows / shrinks fast within a short section (e.g. xsec[1]→[2]
        # on the cessna nose: a goes from 0.14 m to 0.41 m over only
        # 0.13 m of length), the linear cone-frustum interpolation
        # between super-ellipse anchors under-estimates the actual
        # curved surface. Sections whose shape-change-rate exceeds 50 %
        # of the body's typical dim per metre get an extra ×2 boost.
        shape_change_rate = delta_shape / section_len
        if shape_change_rate > 0.5 * body_dim_median:
            weight *= 2.0
        weights.append(weight)

    total_w = sum(weights) or 1.0
    n_intermediates_total = max(0, int(total_stations) - len(anchors))

    intermediates_per_section: list[int] = []
    fractional_remainder = 0.0
    for w in weights:
        ideal = w / total_w * n_intermediates_total + fractional_remainder
        n = int(round(ideal))
        fractional_remainder = ideal - n
        intermediates_per_section.append(max(0, n))

    stations: list[float] = []
    for i in range(n_sections):
        x_a = anchors[i][0]
        x_b = anchors[i + 1][0]
        stations.append(x_a)
        n_inter = intermediates_per_section[i]
        for k in range(1, n_inter + 1):
            # Cosine clustering toward BOTH anchors (gh-804): VSP lofts a
            # spline through the control xsecs, so curvature is highest
            # next to the anchors (the nose-body fillet, tail cone). A
            # uniform split places the first intermediate too far from the
            # anchor and the fillet renders as a kink; cosine spacing
            # pulls samples toward the section ends where the surface
            # actually curves.
            frac = 0.5 * (1.0 - np.cos(np.pi * k / (n_inter + 1)))
            stations.append(x_a + frac * (x_b - x_a))
    stations.append(anchors[-1][0])

    # Deduplicate consecutive equal stations (defensive — shouldn't
    # happen, but a handler xsec at distance zero from another would
    # do this).
    deduped: list[float] = []
    for s in stations:
        if not deduped or abs(s - deduped[-1]) > 1e-9:
            deduped.append(s)

    if scale_to_mm:
        deduped = [s * 1000.0 for s in deduped]
    return deduped


def _clip_to_y_half_space(shape, keep_positive: bool, pad: float = 100.0):
    """Boolean-intersect a shape with a half-space y > 0 (or y < 0).

    Used when slicing a ``symmetric=True`` fuselage's STEP file, which
    contains BOTH mirrored halves. Each section cut would otherwise
    intersect both copies → two disjoint contours per slice and
    centroid ambiguity. Clipping to one half before slicing yields a
    single clean contour per station.

    Returns the clipped TopoDS_Shape, or the original shape on failure.
    """
    try:
        import cadquery as cq
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt

        bb = cq.Shape(shape).BoundingBox()
        y_lo = 0.0 if keep_positive else bb.ymin - pad
        y_hi = bb.ymax + pad if keep_positive else 0.0
        clip_box = cq.Shape(
            BRepPrimAPI_MakeBox(
                gp_Pnt(bb.xmin - pad, y_lo, bb.zmin - pad),
                gp_Pnt(bb.xmax + pad, y_hi, bb.zmax + pad),
            ).Shape()
        )
        op = BRepAlgoAPI_Common(shape, clip_box.wrapped)
        op.Build()
        if op.IsDone():
            return op.Shape()
    except Exception as exc:  # noqa: BLE001 — defensive, fall through to original
        logger.info("Half-space clip failed (%s) — using full shape.", exc)
    return shape


def slice_step_at_stations(
    step_path: str,
    x_stations_mm: list[float],
    *,
    points_per_slice: int = 30,
    slice_axis: str = "x",
    fuselage_name: str = "Imported Fuselage",
    keep_y_side: Optional[str] = None,
) -> tuple[list[dict], dict]:
    """Like :func:`slice_step_to_fuselage` but with an explicit station
    list (already in cadquery mm). Used by the gh-732 wiring so handler
    xsec positions can drive the slicer instead of cadquery's
    XZ-profile curvature.

    Returns ``(xsec_dicts, metrics)`` in the same shape as
    :func:`slice_step_to_fuselage`. Each fit is independent (no
    ``prev_params`` cascade — see the bug-fix note in
    :func:`slice_step_to_fuselage`).
    """
    if slice_axis != "x":
        # Keep this entry-point minimal — the legacy auto-rotate path
        # belongs in slice_step_to_fuselage. Callers that need it
        # should pre-rotate.
        raise ValueError(
            f"slice_step_at_stations only supports slice_axis='x' (got {slice_axis!r})."
        )

    model = load_step_model(step_path)
    sliceable = _ensure_sliceable_shape(model)

    # gh-732: when slicing a ``symmetric=True`` fuselage, clip the STEP
    # to one half (y > 0 or y < 0) so each Section cut yields a single
    # outline. Without clipping, every slice would intersect BOTH
    # mirrored copies and the fitter would have to pick one.
    if keep_y_side == "positive":
        sliceable = _clip_to_y_half_space(sliceable, keep_positive=True)
    elif keep_y_side == "negative":
        sliceable = _clip_to_y_half_space(sliceable, keep_positive=False)

    # Original geometry properties (Shell-tolerant: Volume is only
    # defined for closed Solids — fall back to surface-area alone when
    # given an Open Shell from VSP).
    solids = model.solids().vals()
    if solids:
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

    xsec_dicts: list[dict] = []
    for x in x_stations_mm:
        polylines = slice_at_x(sliceable, x, points_per_edge=points_per_slice)
        if not polylines:
            continue
        # gh-732: drop inner / disjoint contours (canopy bubbles,
        # cowling sub-features) so the fitter sees only the outer skin.
        # See ``select_outer_contour`` for the clustering heuristic.
        polylines = select_outer_contour(polylines)
        slice_points = [pt for poly in polylines for pt in poly]
        if not slice_points:
            continue
        x_real = float(slice_points[0][0])
        points_2d = np.array([(y, z) for (_, y, z) in slice_points])
        fit = fit_shape_area_superellipse(points_2d, prev_params=None)
        xyz = [x_real, float(fit["center"][0]), float(fit["center"][1])]
        xsec_dicts.append(
            {
                "xyz": xyz,
                "a": float(fit["a"]),
                "b": float(fit["b"]),
                "n": float(np.clip(fit["n"], 0.5, 8.0)),
            }
        )

    # Reconstruct as asb.Fuselage for global fidelity.
    fuselage_xsecs = [
        asb.FuselageXSec(
            xyz_c=d["xyz"],
            xyz_normal=np.array([1.0, 0.0, 0.0]),
            radius=None,
            width=2.0 * d["a"],
            height=2.0 * d["b"],
            shape=d["n"],
        )
        for d in xsec_dicts
    ]
    asb_fuselage = asb.Fuselage(name=fuselage_name, xsecs=fuselage_xsecs)
    rec_vol = asb_fuselage.volume()
    rec_area = asb_fuselage.area_wetted()
    metrics = {
        "original_volume": original_props["volume"],
        "original_area": original_props["surface_area"],
        "reconstructed_volume": rec_vol,
        "reconstructed_area": rec_area,
        "volume_ratio": (
            rec_vol / original_props["volume"] if original_props["volume"] > 0 else 0.0
        ),
        "area_ratio": (
            rec_area / original_props["surface_area"] if original_props["surface_area"] > 0 else 0.0
        ),
    }
    logger.info(
        "Fuselage %r: %d xsecs from %d stations, volume_ratio=%.3f, area_ratio=%.3f",
        fuselage_name,
        len(xsec_dicts),
        len(x_stations_mm),
        metrics["volume_ratio"],
        metrics["area_ratio"],
    )
    return xsec_dicts, metrics


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    step_path = "../../components/aircraft/eHawk/e-Hawk Rumpf v29.step"
    xsecs, metrics = slice_step_to_fuselage(step_path, number_of_slices=50)

    print(f"\n{'=' * 60}")
    print(f"Sections: {len(xsecs)}")
    print(
        f"Volume:   original={metrics['original_volume']:.6f}  reconstructed={metrics['reconstructed_volume']:.6f}  ratio={metrics['volume_ratio']:.3f}"
    )
    print(
        f"Area:     original={metrics['original_area']:.6f}  reconstructed={metrics['reconstructed_area']:.6f}  ratio={metrics['area_ratio']:.3f}"
    )
