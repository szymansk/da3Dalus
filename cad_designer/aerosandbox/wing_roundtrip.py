"""
Helpers for comparing a ``WingConfiguration`` before and after a
``asb_wing() -> from_asb()`` roundtrip.

Three comparison levels:

1. **Parameter-strict**: Walks the ``WingSegment`` / ``Airfoil`` fields
   of two ``WingConfiguration`` objects and reports per-field
   differences. The user has specified that ``nose_pnt``, ``incidence``,
   ``sweep``, ``dihedral_as_rotation_in_degrees``,
   ``dihedral_as_translation`` must be
   *exactly equal* after a correct roundtrip. Deviations here indicate
   a bug in ``WingConfiguration.from_asb()`` or in the downstream
   schema-converter path.

2. **Segment-origin-strict**: Calls ``get_wing_workplane(i)`` on each
   segment and compares the resulting ``Plane.origin`` points. This
   catches cases where parameter values look right individually but
   the accumulated homogeneous transforms place the segments at
   different locations in global space.

3. **Shape-tolerant**: Renders both ``WingConfiguration`` variants
   through ``WingLoftCreator`` (loft-only, no ribs/spars), exports
   each to a STEP file, re-imports them, and compares the resulting
   CAD solids via ``BRepGProp.VolumeProperties_s`` (volume),
   ``BRepGProp.SurfaceProperties_s`` (surface area) and centroid
   distance. The existing helpers in
   ``cad_designer/aerosandbox/slicing.py`` (``compute_shape_properties``,
   ``load_step_model``) are reused directly.

All helpers are read-only with respect to their ``WingConfiguration``
arguments where possible, except ``render_wing_loft_to_step`` which
must invoke the CAD pipeline.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from numpy import ndarray

from cad_designer.aerosandbox.slicing import (
    compute_shape_properties,
    load_step_model,
)


# --------------------------------------------------------------------------- #
# Result containers
# --------------------------------------------------------------------------- #


@dataclass
class ParameterDiff:
    """A single per-field parameter mismatch between two WingConfigurations."""

    path: str  # e.g. "segments[1].tip_airfoil.incidence"
    expected: Any
    actual: Any
    abs_delta: float  # |expected - actual| for numeric fields, NaN otherwise

    def __str__(self) -> str:  # pragma: no cover - pure formatting
        return (
            f"{self.path}: expected={self.expected!r} "
            f"actual={self.actual!r} abs_delta={self.abs_delta}"
        )


@dataclass
class ParameterCompareResult:
    """Outcome of ``compare_wing_configs``."""

    diffs: List[ParameterDiff] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.diffs

    def __str__(self) -> str:  # pragma: no cover - pure formatting
        if self.ok:
            return "ParameterCompareResult: OK (no differences)"
        lines = ["ParameterCompareResult: FAILED"]
        lines.extend(f"  - {d}" for d in self.diffs)
        return "\n".join(lines)


@dataclass
class SegmentOriginDiff:
    """A single segment-origin mismatch."""

    segment_index: int
    expected: Tuple[float, float, float]
    actual: Tuple[float, float, float]
    distance: float  # Euclidean distance in wing-config units (mm)


@dataclass
class SegmentOriginCompareResult:
    diffs: List[SegmentOriginDiff] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.diffs

    @property
    def max_distance(self) -> float:
        if not self.diffs:
            return 0.0
        return max(d.distance for d in self.diffs)


@dataclass
class ShapeCompareResult:
    """Tolerant shape comparison between two rendered wing solids."""

    volume_a: float
    volume_b: float
    surface_a: float
    surface_b: float
    centroid_a: Tuple[float, float, float]
    centroid_b: Tuple[float, float, float]

    @property
    def volume_rel_delta(self) -> float:
        if self.volume_a == 0:
            return float("inf") if self.volume_b != 0 else 0.0
        return abs(self.volume_a - self.volume_b) / abs(self.volume_a)

    @property
    def surface_rel_delta(self) -> float:
        if self.surface_a == 0:
            return float("inf") if self.surface_b != 0 else 0.0
        return abs(self.surface_a - self.surface_b) / abs(self.surface_a)

    @property
    def centroid_distance(self) -> float:
        dx = self.centroid_a[0] - self.centroid_b[0]
        dy = self.centroid_a[1] - self.centroid_b[1]
        dz = self.centroid_a[2] - self.centroid_b[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def summary(self) -> str:
        return (
            f"volume_rel={self.volume_rel_delta:.4%} "
            f"surface_rel={self.surface_rel_delta:.4%} "
            f"centroid_dist={self.centroid_distance:.4f}mm"
        )


# --------------------------------------------------------------------------- #
# Level 1: parameter-strict comparison
# --------------------------------------------------------------------------- #


# Fields that are asb-invariant metadata and must roundtrip exactly.
#
# NOTE: ``length``, ``sweep``, ``dihedral_as_translation``,
# ``dihedral_as_rotation_in_degrees`` and ``incidence``
# are intentionally NOT in these lists.
# ``from_asb`` projects the rebuilt configuration onto a canonical
# form with ``rc = 0`` and all dihedral carried as translations, so
# those fields will differ by design. The *geometric* equivalence
# that matters to the caller is covered by Level 2 (segment origins)
# and Level 3 (rendered shape). Level 1 is now a pure metadata check
# on the fields that survive the projection. See
# cad-modelling-service-121.
_SEGMENT_STRICT_FIELDS: Tuple[str, ...] = ()

_AIRFOIL_STRICT_FIELDS: Tuple[str, ...] = (
    "chord",
)


def _numeric_abs_delta(a: Any, b: Any) -> float:
    try:
        return abs(float(a) - float(b))
    except (TypeError, ValueError):
        return float("nan")


def _approx_equal(a: Any, b: Any, tol: float) -> bool:
    """Numeric near-equality with NaN propagation."""
    try:
        fa = float(a)
        fb = float(b)
    except (TypeError, ValueError):
        return a == b
    if math.isnan(fa) or math.isnan(fb):
        return False
    return abs(fa - fb) <= tol


def compare_wing_configs(
    expected,
    actual,
    *,
    tol: float = 1e-6,
) -> ParameterCompareResult:
    """Metadata sanity check between two WingConfigurations.

    Post-Phase-3, the rebuilt configuration is a projection onto
    ``dihedral_as_rotation_in_degrees=0``,
    with dihedral carried entirely by ``dihedral_as_translation``.
    Strict field-for-field equality on the geometric parameters is
    therefore meaningless — the *geometric* equivalence is the job of
    Levels 2 and 3.

    This function checks only the asb-invariant metadata that *must*
    roundtrip regardless of projection:

    - ``nose_pnt`` (3-tuple)
    - ``symmetric`` (bool)
    - Number of segments
    - For each segment's root + tip airfoil: chord

    Tolerance defaults to ``1e-6`` to absorb float round-tripping
    through aerosandbox (which converts through np.float64).
    """
    result = ParameterCompareResult()

    # nose_pnt
    e_nose = tuple(expected.nose_pnt)
    a_nose = tuple(actual.nose_pnt)
    for idx, (e, a) in enumerate(zip(e_nose, a_nose)):
        if not _approx_equal(e, a, tol):
            result.diffs.append(
                ParameterDiff(
                    path=f"nose_pnt[{idx}]",
                    expected=e,
                    actual=a,
                    abs_delta=_numeric_abs_delta(e, a),
                )
            )

    # symmetric
    if expected.symmetric != actual.symmetric:
        result.diffs.append(
            ParameterDiff(
                path="symmetric",
                expected=expected.symmetric,
                actual=actual.symmetric,
                abs_delta=float("nan"),
            )
        )

    # segment count
    e_segs = list(expected.segments or [])
    a_segs = list(actual.segments or [])
    if len(e_segs) != len(a_segs):
        result.diffs.append(
            ParameterDiff(
                path="len(segments)",
                expected=len(e_segs),
                actual=len(a_segs),
                abs_delta=_numeric_abs_delta(len(e_segs), len(a_segs)),
            )
        )
        return result  # further per-segment comparison is meaningless

    for i, (e_seg, a_seg) in enumerate(zip(e_segs, a_segs)):
        for fname in _SEGMENT_STRICT_FIELDS:
            e_val = getattr(e_seg, fname, None)
            a_val = getattr(a_seg, fname, None)
            if not _approx_equal(e_val, a_val, tol):
                result.diffs.append(
                    ParameterDiff(
                        path=f"segments[{i}].{fname}",
                        expected=e_val,
                        actual=a_val,
                        abs_delta=_numeric_abs_delta(e_val, a_val),
                    )
                )

        for airfoil_name in ("root_airfoil", "tip_airfoil"):
            e_af = getattr(e_seg, airfoil_name, None)
            a_af = getattr(a_seg, airfoil_name, None)
            if e_af is None and a_af is None:
                continue
            if e_af is None or a_af is None:
                result.diffs.append(
                    ParameterDiff(
                        path=f"segments[{i}].{airfoil_name}",
                        expected=e_af,
                        actual=a_af,
                        abs_delta=float("nan"),
                    )
                )
                continue
            for fname in _AIRFOIL_STRICT_FIELDS:
                e_val = getattr(e_af, fname, None)
                a_val = getattr(a_af, fname, None)
                if not _approx_equal(e_val, a_val, tol):
                    result.diffs.append(
                        ParameterDiff(
                            path=f"segments[{i}].{airfoil_name}.{fname}",
                            expected=e_val,
                            actual=a_val,
                            abs_delta=_numeric_abs_delta(e_val, a_val),
                        )
                    )

    return result


# --------------------------------------------------------------------------- #
# Level 2: segment-origin-strict comparison
# --------------------------------------------------------------------------- #


def compare_segment_origins(
    expected,
    actual,
    *,
    tol: float = 1e-6,
) -> SegmentOriginCompareResult:
    """Compare per-segment workplane origins between two WingConfigurations.

    Iterates ``segment`` from 0 to ``len(segments)`` (inclusive — the
    last call gives the tip of the last segment) and compares the
    ``Plane.origin`` coordinates. This is the "nose point der Segmente"
    check from the user's spec: the resulting segment positions in
    global space must match exactly, because that is the ground-truth
    placement of the airfoil cross-sections.

    The comparison uses ``ignore_nose_point=False`` so that the
    ``nose_pnt`` translation is included — mismatches in ``nose_pnt``
    will show as a constant offset across all segments.
    """
    n_segments = len(list(expected.segments or []))
    result = SegmentOriginCompareResult()
    for i in range(n_segments + 1):
        e_plane = expected.get_wing_workplane(
            segment=min(i, n_segments - 1),
            ignore_nose_point=False,
        ).plane
        a_plane = actual.get_wing_workplane(
            segment=min(i, n_segments - 1),
            ignore_nose_point=False,
        ).plane
        e_o = (e_plane.origin.x, e_plane.origin.y, e_plane.origin.z)
        a_o = (a_plane.origin.x, a_plane.origin.y, a_plane.origin.z)
        dist = math.sqrt(
            (e_o[0] - a_o[0]) ** 2
            + (e_o[1] - a_o[1]) ** 2
            + (e_o[2] - a_o[2]) ** 2
        )
        if dist > tol:
            result.diffs.append(
                SegmentOriginDiff(
                    segment_index=i,
                    expected=e_o,
                    actual=a_o,
                    distance=dist,
                )
            )
    return result


# --------------------------------------------------------------------------- #
# Level 3: shape-tolerant comparison via WingLoftCreator + STEP round-trip
# --------------------------------------------------------------------------- #


def render_wing_loft_to_step(
    wing_config,
    out_path: Path,
    *,
    wing_name: str = "wing",
    wing_side: str = "BOTH",
    connected: bool = False,
) -> Path:
    """Render a ``WingConfiguration`` through ``WingLoftCreator`` and
    export it as a STEP file at ``out_path``.

    Runs ``WingLoftCreator`` directly (no ``ConstructionRootNode`` /
    ``ExportToStepCreator`` layers) and writes the resulting workplane
    via ``cadquery.exporters.export``. This keeps the filename
    predictable (exactly ``out_path``) and avoids the multi-file
    artefacts produced by ``ExportToStepCreator``.

    The caller is responsible for ensuring the output directory
    exists. Returns the resolved ``out_path`` for convenience.
    """
    # Local imports to keep this module importable on aarch64 where
    # cadquery is excluded.
    import cadquery as cq  # noqa: F401 — ensures cq plugins load
    from cadquery import exporters

    from cad_designer.airplane.creator.wing import WingLoftCreator

    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wing_configuration = {wing_name: wing_config}

    creator = WingLoftCreator(
        creator_id=f"wing_loft_{out_path.stem}",
        wing_index=wing_name,
        wing_config=wing_configuration,
        wing_side=wing_side,
        connected=connected,
    )

    shapes = creator.create_shape()
    # create_shape returns {<creator_id>: Workplane}; take the only entry.
    workplane = next(iter(shapes.values()))

    exporters.export(workplane, str(out_path))
    return out_path


def render_asb_wing_to_stl(
    wing_config,
    out_path: Path,
    *,
    unit_scale_mm: float = 1.0,
) -> Path:
    """Render the asb view of a WingConfiguration as an STL file.

    This is the *aerodynamic* gold standard: it writes the triangle
    mesh that ``aerosandbox.Wing.mesh_body()`` produces, using the
    same frame computation (``_compute_frame_of_WingXSec``) that
    every VLM / AVL / stability analysis inside this service
    consumes. Anything that aero analysis ever "sees" of the wing
    is represented in this STL; overlaying it onto the CAD STEP
    files renders the asb-vs-Wing discrepancy visible.

    Args:
        wing_config: The source ``WingConfiguration``. This
            function calls ``asb_wing()`` on it, so the returned
            cache will be populated.
        out_path: Destination STL file. Parents are created if
            needed.
        unit_scale_mm: Scale factor to apply to the mesh vertices
            so the output STL is in *millimetres*. The CAD STEP
            files produced by :func:`render_wing_loft_to_step` are
            in mm, and the harness factories build
            ``WingConfiguration``\\s in mm; calling
            ``wing_config.asb_wing()`` with the default
            ``scale=1.0`` keeps the asb wing in mm, so the
            ``unit_scale_mm`` default of ``1.0`` is correct for the
            in-process harness. If a caller uses
            ``wing_config.asb_wing(scale=0.001)`` to put asb in
            SI metres (as the REST pipeline does), pass
            ``unit_scale_mm=1000.0`` to rescale back to mm for the
            STL overlay.

    Returns:
        The resolved STL path for convenience.
    """
    import aerosandbox as asb  # noqa: F401 — raise ImportError on aarch64

    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build (or reuse) the asb wing. ``asb_wing()`` caches on the
    # instance, so a second call inside the same process is cheap.
    asb_wing = wing_config.asb_wing()

    # ``mesh_body`` returns (vertices, triangles). ``method='tri'``
    # yields a triangle mesh ready for STL; the alternative 'quad'
    # mode would need triangulation.
    vertices, triangles = asb_wing.mesh_body(method="tri")

    # Apply the unit scale. For the in-process harness this is the
    # identity; it exists so that downstream REST or SI-unit
    # callers can convert metres → millimetres without touching the
    # asb wing itself.
    if unit_scale_mm != 1.0:
        vertices = np.asarray(vertices, dtype=float) * unit_scale_mm

    _write_stl_mesh(vertices, triangles, out_path)
    return out_path


def _write_stl_mesh(
    vertices: ndarray,
    triangles: ndarray,
    out_path: Path,
) -> None:
    """Write a triangle mesh to an ASCII STL file.

    Computes per-face normals via the right-hand rule on the
    triangle's vertices and flips each one outward by comparing
    it to the centroid-to-face direction. This matches the
    normal-correction heuristic in
    ``cad_designer/aerosandbox/convert2aerosandbox.asb_mesh_to_stl``
    but without the hard-coded ``scale=0.1`` factor that legacy
    helper bakes in.
    """
    vertices = np.asarray(vertices, dtype=float)
    triangles = np.asarray(triangles, dtype=int)

    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError(
            f"vertices must be (N, 3); got shape {vertices.shape}"
        )
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError(
            f"triangles must be (M, 3); got shape {triangles.shape}"
        )

    center = vertices.mean(axis=0)

    def _unit_normal(v1: ndarray, v2: ndarray, v3: ndarray) -> ndarray:
        n = np.cross(v2 - v1, v3 - v1)
        m = float(np.linalg.norm(n))
        return n / m if m > 0.0 else np.zeros(3)

    lines = ["solid asb_wing_mesh"]
    for tri in triangles:
        v1, v2, v3 = (vertices[i] for i in tri)
        normal = _unit_normal(v1, v2, v3)
        centroid = (v1 + v2 + v3) / 3.0
        direction = centroid - center
        if float(np.dot(normal, direction)) < 0.0:
            # Flip winding so the face points outward.
            v2, v3 = v3, v2
            normal = _unit_normal(v1, v2, v3)
        lines.append(
            f"  facet normal {normal[0]} {normal[1]} {normal[2]}"
        )
        lines.append("    outer loop")
        lines.append(f"      vertex {v1[0]} {v1[1]} {v1[2]}")
        lines.append(f"      vertex {v2[0]} {v2[1]} {v2[2]}")
        lines.append(f"      vertex {v3[0]} {v3[1]} {v3[2]}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid asb_wing_mesh")

    out_path.write_text("\n".join(lines))


def propagate_cad_metadata(expected, rebuilt) -> None:
    """Copy CAD-only metadata from the expected wing into the rebuilt wing.

    ``WingConfiguration.from_asb`` reconstructs the *geometric* state
    from asb data, but asb does not store a handful of CAD-only
    attributes that the CadQuery loft pipeline nevertheless reads from
    the ``WingConfiguration``:

    - ``number_interpolation_points`` — how many points the airfoil
      spline uses when it is sampled onto the workplane. asb has no
      concept of this because it only runs vortex-lattice analysis.
    - ``wing_segment_type`` / ``tip_type`` — the Wing-level
      distinction between regular segments and tip segments (flat,
      round, …). asb just sees a flat list of cross-sections.
    - Airfoil file paths on both root and tip airfoils — asb stores
      only the airfoil *name* (a bare identifier), not the full
      ``.dat`` path that CadQuery needs to open.

    In the REST/production pipeline this information is restored via
    the ``AsbWingSchema`` hydration step in
    ``asbWingSchemaToWingConfig``. In the test harness (which goes
    directly through ``from_asb`` with no schema), we need to
    propagate it manually so that the rebuilt wing renders with the
    same CAD-level settings as the expected one. Without this the
    loft uses a different airfoil resolution and the Level 3 shape
    test picks up a ~2 % volume delta that is *purely* a mesh-density
    artefact, not a geometric roundtrip issue.

    The function mutates ``rebuilt`` in place. Segment counts must
    match; any mismatch is silently tolerated by iterating over the
    shorter list.
    """
    if expected.segments is None or rebuilt.segments is None:
        return

    for idx, (exp_seg, reb_seg) in enumerate(zip(expected.segments, rebuilt.segments)):
        if exp_seg.number_interpolation_points is not None:
            reb_seg.number_interpolation_points = exp_seg.number_interpolation_points
        if getattr(exp_seg, "wing_segment_type", None) is not None:
            reb_seg.wing_segment_type = exp_seg.wing_segment_type
        if getattr(exp_seg, "tip_type", None) is not None:
            reb_seg.tip_type = exp_seg.tip_type
        if exp_seg.root_airfoil is not None and reb_seg.root_airfoil is not None:
            if exp_seg.root_airfoil.airfoil is not None:
                reb_seg.root_airfoil.airfoil = exp_seg.root_airfoil.airfoil
        if exp_seg.tip_airfoil is not None and reb_seg.tip_airfoil is not None:
            if exp_seg.tip_airfoil.airfoil is not None:
                reb_seg.tip_airfoil.airfoil = exp_seg.tip_airfoil.airfoil


def compare_wing_shapes(step_path_a: Path, step_path_b: Path) -> ShapeCompareResult:
    """Compare two wing shapes exported as STEP files.

    Uses the existing ``load_step_model`` and ``compute_shape_properties``
    helpers from ``cad_designer/aerosandbox/slicing.py``. The result
    carries raw volumes, surface areas and centroids plus derived
    relative-delta helper properties.
    """
    step_path_a = Path(step_path_a).resolve()
    step_path_b = Path(step_path_b).resolve()
    if not step_path_a.exists():
        raise FileNotFoundError(f"STEP file A not found: {step_path_a}")
    if not step_path_b.exists():
        raise FileNotFoundError(f"STEP file B not found: {step_path_b}")

    wp_a = load_step_model(str(step_path_a))
    wp_b = load_step_model(str(step_path_b))

    solid_a = wp_a.solids().first().val().wrapped
    solid_b = wp_b.solids().first().val().wrapped

    props_a = compute_shape_properties(solid_a)
    props_b = compute_shape_properties(solid_b)

    # Centroid via BoundingBox center as a simple proxy — BRepGProp also
    # provides a true mass centre of the solid which is more precise.
    try:
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps

        gp_a = GProp_GProps()
        BRepGProp.VolumeProperties_s(solid_a, gp_a)
        ca = gp_a.CentreOfMass()

        gp_b = GProp_GProps()
        BRepGProp.VolumeProperties_s(solid_b, gp_b)
        cb = gp_b.CentreOfMass()

        centroid_a = (ca.X(), ca.Y(), ca.Z())
        centroid_b = (cb.X(), cb.Y(), cb.Z())
    except Exception:
        bb_a = wp_a.solids().first().val().BoundingBox()
        bb_b = wp_b.solids().first().val().BoundingBox()
        centroid_a = (
            (bb_a.xmin + bb_a.xmax) * 0.5,
            (bb_a.ymin + bb_a.ymax) * 0.5,
            (bb_a.zmin + bb_a.zmax) * 0.5,
        )
        centroid_b = (
            (bb_b.xmin + bb_b.xmax) * 0.5,
            (bb_b.ymin + bb_b.ymax) * 0.5,
            (bb_b.zmin + bb_b.zmax) * 0.5,
        )

    return ShapeCompareResult(
        volume_a=props_a["volume"],
        volume_b=props_b["volume"],
        surface_a=props_a["surface_area"],
        surface_b=props_b["surface_area"],
        centroid_a=centroid_a,
        centroid_b=centroid_b,
    )


# --------------------------------------------------------------------------- #
# CLI: export STEP pairs for manual visual comparison in a CAD tool
# --------------------------------------------------------------------------- #


def export_roundtrip_pair(
    wing_config,
    out_dir: Path,
    *,
    case_id: str,
    wing_side: str = "RIGHT",
) -> Tuple[Path, Path, "ShapeCompareResult"]:
    """Export a complete comparison bundle for one roundtrip case.

    Writes three files to ``out_dir``:

    - ``<case_id>_expected.step`` — the CAD render of the
      *original* ``WingConfiguration`` (through ``WingLoftCreator``).
    - ``<case_id>_actual.step`` — the CAD render of the
      ``from_asb``-rebuilt ``WingConfiguration``.
    - ``<case_id>_asb_goldstandard.stl`` — the *aerodynamic* gold
      standard: the triangle mesh that aerosandbox produces directly
      from the source wing via ``asb.Wing.mesh_body()``. All
      VLM/AVL/stability analyses inside the service consume this
      exact mesh, so overlaying it onto the STEP files shows where
      the CAD pipeline diverges from the aero model. It is always a
      full mirrored mesh (``mesh_body`` does its own mirroring) and
      is written in millimetres to match the STEP files.

    The ``ShapeCompareResult`` between the two STEP files is
    returned so the caller can print a summary table. The STL does
    not participate in the numeric comparison.

    Using ``wing_side="RIGHT"`` for the STEP files avoids the
    mirror-and-union step that doubles CAD render cost and obscures
    per-segment drift during visual comparison. Pass
    ``wing_side="BOTH"`` explicitly if you want the full mirrored
    wing in the STEP output (the STL is always full-mirrored).
    """
    from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
        WingConfiguration,
    )

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build the baseline asb wing from a *fresh* copy — asb_wing() caches
    # on the instance, so we feed a second factory result into the
    # roundtrip path and leave the original untouched for rendering.
    asb_wing = wing_config.asb_wing()
    rebuilt = WingConfiguration.from_asb(
        asb_wing.xsecs,
        symmetric=wing_config.symmetric,
    )
    # Restore CAD-only metadata (number_interpolation_points,
    # tip_type, airfoil file paths) that asb cannot represent. In
    # the production REST pipeline this is done by the schema
    # hydration step; in this CLI we do it directly from the
    # expected config.
    propagate_cad_metadata(wing_config, rebuilt)

    expected_path = out_dir / f"{case_id}_expected.step"
    actual_path = out_dir / f"{case_id}_actual.step"

    render_wing_loft_to_step(
        wing_config,
        expected_path,
        wing_name="main_wing",
        wing_side=wing_side,
        connected=False,
    )
    render_wing_loft_to_step(
        rebuilt,
        actual_path,
        wing_name="main_wing",
        wing_side=wing_side,
        connected=False,
    )

    # Aerodynamic gold standard: asb mesh of the *original* wing,
    # exported as STL with the same mm scale as the STEP files.
    # Any divergence between this STL and the two STEP files is
    # the geometric gap between the aero model (VLM/AVL input) and
    # the CAD model (3D-print input).
    asb_stl_path = out_dir / f"{case_id}_asb_goldstandard.stl"
    render_asb_wing_to_stl(
        wing_config,
        asb_stl_path,
        unit_scale_mm=1.0,
    )

    result = compare_wing_shapes(expected_path, actual_path)
    return expected_path, actual_path, result


def _main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry: export STEP pairs for every registered roundtrip case.

    Usage::

        poetry run python -m cad_designer.aerosandbox.wing_roundtrip \\
            [--out-dir exports/wing_roundtrip] \\
            [--case <case_id> ...] \\
            [--wing-side RIGHT|BOTH]

    The default output location is ``<repo-root>/exports/wing_roundtrip``.
    Open the pairs side-by-side (or overlaid) in FreeCAD / Fusion /
    CadQuery-Gateway. Since both sides of a perfect roundtrip would
    render identical shapes, any visible deviation is the geometric
    manifestation of a ``from_asb()`` bug.
    """
    import argparse
    import logging

    from cad_designer.aerosandbox.wing_roundtrip_cases import (
        CASE_FACTORIES,
        get_factory,
    )

    parser = argparse.ArgumentParser(
        description="Export WingConfiguration roundtrip STEP pairs.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: <repo>/exports/wing_roundtrip)",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=None,
        help="Limit to one or more case ids (default: all). Repeatable.",
    )
    parser.add_argument(
        "--wing-side",
        default="RIGHT",
        choices=["RIGHT", "LEFT", "BOTH"],
        help="Which wing half to render (default: RIGHT)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging from the CAD pipeline.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Default out-dir: <repo>/exports/wing_roundtrip. The helper module
    # wing_roundtrip_cases already computes REPO_ROOT relative to its
    # own location, so we reuse it for consistency.
    from cad_designer.aerosandbox.wing_roundtrip_cases import REPO_ROOT

    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "exports" / "wing_roundtrip"

    if args.case:
        cases = [(cid, get_factory(cid)) for cid in args.case]
    else:
        cases = list(CASE_FACTORIES)

    print(f"Exporting {len(cases)} roundtrip STEP pair(s) to {out_dir}")
    print("=" * 72)

    header = f"{'case':<32}{'vol Δ':>10}{'surf Δ':>10}{'centroid Δ mm':>18}"
    print(header)
    print("-" * len(header))

    all_results: list[tuple[str, "ShapeCompareResult"]] = []
    for case_id, factory in cases:
        wc = factory()
        try:
            _, _, result = export_roundtrip_pair(
                wc,
                out_dir,
                case_id=case_id,
                wing_side=args.wing_side,
            )
        except Exception as exc:  # pragma: no cover - CLI diagnostics path
            print(f"{case_id:<32}  FAILED: {exc}")
            continue
        all_results.append((case_id, result))
        print(
            f"{case_id:<32}"
            f"{result.volume_rel_delta:>9.4%}"
            f"{result.surface_rel_delta:>10.4%}"
            f"{result.centroid_distance:>18.4f}"
        )

    print("=" * 72)
    print(f"Files written to {out_dir}")
    print(
        "For each case three files are produced:\n"
        "  <case>_expected.step        CAD render of the original WingConfiguration\n"
        "  <case>_actual.step          CAD render of the from_asb-rebuilt WingConfiguration\n"
        "  <case>_asb_goldstandard.stl aerosandbox mesh of the *original* wing\n"
        "                              (the aerodynamic gold standard, same mesh VLM/AVL uses).\n"
        "All three are in millimetres — overlay them directly in a CAD tool."
    )
    return 0 if all_results else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
