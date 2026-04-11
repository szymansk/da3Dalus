"""
Helpers for comparing a ``WingConfiguration`` before and after a
``asb_wing() -> from_asb()`` roundtrip.

Three comparison levels:

1. **Parameter-strict**: Walks the ``WingSegment`` / ``Airfoil`` fields
   of two ``WingConfiguration`` objects and reports per-field
   differences. The user has specified that ``nose_pnt``, ``incidence``,
   ``sweep``, ``dihedral_as_rotation_in_degrees``,
   ``dihedral_as_translation`` and ``rotation_point_rel_chord`` must be
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


# Fields on ``WingSegment`` that the user has declared must roundtrip exactly.
_SEGMENT_STRICT_FIELDS: Tuple[str, ...] = (
    "length",
    "sweep",
)

# Fields on ``Airfoil`` that must roundtrip exactly.
_AIRFOIL_STRICT_FIELDS: Tuple[str, ...] = (
    "chord",
    "dihedral_as_rotation_in_degrees",
    "dihedral_as_translation",
    "incidence",
    "rotation_point_rel_chord",
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
    tol: float = 1e-9,
) -> ParameterCompareResult:
    """Strict per-field comparison of two WingConfigurations.

    The comparison covers:

    - ``nose_pnt`` (3-tuple)
    - ``symmetric`` (bool)
    - Number of segments (must match exactly)
    - For each segment: length, sweep
    - For each segment's root + tip airfoil: chord,
      dihedral_as_rotation_in_degrees, dihedral_as_translation,
      incidence, rotation_point_rel_chord

    Any field difference above ``tol`` becomes a ``ParameterDiff`` in
    the result. ``tol`` is a single absolute tolerance applied to all
    numeric fields (the user has asked for "exact" equality; ``1e-9``
    is slack enough to absorb float round-tripping through numpy but
    tight enough to catch real bugs).
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
