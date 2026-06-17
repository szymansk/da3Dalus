"""Section-geometry primitive (gh-1020).

Slice the **real lofted CAD solid** of a wing to recover, at a parametric
location ``(y/span, x/c)``:

* ``thickness`` — vertical extent of the built section at that chord location
* ``top_z`` / ``bottom_z`` — upper / lower surface heights
* ``center_z`` — section mid-height (spar-placement reference)

Why slice the solid (rather than blend two airfoils analytically): the loft
built by :class:`WingLoftCreator` already encodes every relative rotation
(dihedral via R_x, incidence/twist via R_y, sweep via the plane origin) and the
ruled loft between sections. Slicing gives the exact *built* geometry.

Frame: wing-local, origin at the wing-root LE, ``z`` vertical (the world frame
the loft is built in). Internally **millimetres** — the service layer converts
to metres for the API (project convention).

Platform guard: ``cadquery`` is excluded on ``linux/aarch64``. The import is
lazy and a clear :class:`SectionGeometryUnavailableError` is raised when it is
unavailable, so callers can return a 503/422 rather than crashing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)

try:  # platform guard — cadquery is excluded on linux/aarch64
    import cadquery as cq  # noqa: F401

    _HAS_CADQUERY = True
except ImportError:  # pragma: no cover - platform dependent
    _HAS_CADQUERY = False


class SectionGeometryUnavailableError(RuntimeError):
    """Raised when section geometry cannot be computed because cadquery is
    unavailable on this platform."""


@dataclass(frozen=True)
class SectionPoint:
    """A sampled point on the built wing section.

    All lengths in **millimetres**, wing-local frame (origin root-LE, z up).
    """

    y_span: float  # 0..1 across the whole surface (semi-span)
    x_c: float  # 0..1 along the local chord
    thickness: float
    top_z: float
    bottom_z: float
    center_z: float


# ---------------------------------------------------------------------------
# Pure helpers (fast tier — no CAD)
# ---------------------------------------------------------------------------


def _y_span_to_segment(y_span: float, segment_lengths: list[float]) -> tuple[int, float]:
    """Map a normalised span fraction to ``(segment_index, relative_length)``.

    ``relative_length`` is the 0..1 position *within* that segment. ``y_span``
    is clamped to ``[0, 1]``. The seam between two segments resolves to the end
    (``relative_length == 1.0``) of the lower segment.
    """
    y = min(max(y_span, 0.0), 1.0)
    total = float(sum(segment_lengths))
    if total <= 0.0:
        return 0, 0.0

    target = y * total
    acc = 0.0
    for idx, seg_len in enumerate(segment_lengths):
        seg_len = float(seg_len)
        if seg_len <= 0.0:
            continue
        if target <= acc + seg_len or idx == len(segment_lengths) - 1:
            rel = (target - acc) / seg_len
            return idx, min(max(rel, 0.0), 1.0)
        acc += seg_len
    # fall through (all-zero lengths handled above)
    return len(segment_lengths) - 1, 1.0


def _outline_to_top_bottom(
    outline: list[tuple[float, float]], x_c: float, chord_len: float
) -> tuple[float, float]:
    """Given a closed section outline in (chord_u, height_v) coordinates, return
    ``(top_v, bottom_v)`` at chord position ``x_c * chord_len``.

    The outline is a polyline (consecutive points around the loop). At the
    target chord ordinate we collect every edge crossing and take the max
    (top) and min (bottom). Pure geometry — no CAD dependency, so this runs on
    the fast tier.
    """
    u_target = x_c * chord_len
    crossings: list[float] = []
    n = len(outline)
    for i in range(n):
        u0, v0 = outline[i]
        u1, v1 = outline[(i + 1) % n]
        umin, umax = (u0, u1) if u0 <= u1 else (u1, u0)
        if u_target < umin - 1e-9 or u_target > umax + 1e-9:
            continue
        if abs(u1 - u0) < 1e-12:
            crossings.extend((v0, v1))
        else:
            t = (u_target - u0) / (u1 - u0)
            crossings.append(v0 + t * (v1 - v0))
    if not crossings:
        return 0.0, 0.0
    return max(crossings), min(crossings)


# ---------------------------------------------------------------------------
# SectionGeometry — build once, slice many
# ---------------------------------------------------------------------------


class SectionGeometry:
    """Build a wing's lofted solid once and slice it on demand.

    ``sample`` groups requests by ``y_span`` so each section plane is cut once
    and all ``x_c`` are read off the same outline.
    """

    def __init__(self, wing_config: WingConfiguration, points_per_edge: int = 80):
        if not _HAS_CADQUERY:
            raise SectionGeometryUnavailableError(
                "cadquery is not available on this platform; section geometry cannot be computed."
            )
        self._wing_config = wing_config
        self._points_per_edge = max(8, min(int(points_per_edge), 4096))
        self._segment_lengths = [float(s.length) for s in wing_config.segments]
        self._solid_shape = self._build_solid()

    # -- build -------------------------------------------------------------

    def _build_solid(self):
        """Build the starboard (RIGHT) half loft once and return its shape.

        RIGHT half keeps ``y >= 0`` so the span maps monotonically to ``y/span``.
        """
        from cad_designer.airplane.creator.wing.WingLoftCreator import (
            WingLoftCreator,
        )

        result = WingLoftCreator(
            "section_geometry.loft",
            wing_index=0,
            wing_config={0: self._wing_config},
            wing_side="RIGHT",
        ).create_shape()
        workplane = next(iter(result.values()))
        solids = workplane.solids().vals()
        if not solids:
            raise SectionGeometryUnavailableError("wing loft produced no solid to slice.")
        return solids[0]

    # -- station frame -----------------------------------------------------

    def _station_frame(
        self, y_span: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return ``(origin, chord_dir, span_dir, up_dir)`` for the section plane
        at ``y_span``.

        The frame is interpolated along the segment between its root and tip
        workplanes. ``span_dir`` is the section-plane normal; ``chord_dir`` and
        ``up_dir`` parameterise the cut outline.
        """
        idx, rel = _y_span_to_segment(y_span, self._segment_lengths)
        root_plane = self._wing_config.get_wing_workplane(idx).plane
        tip_plane = self._wing_config.get_wing_workplane(idx + 1).plane

        o_root = np.array(root_plane.origin.toTuple())
        o_tip = np.array(tip_plane.origin.toTuple())
        origin = o_root + rel * (o_tip - o_root)

        # Direction along the segment span = vector between its station LEs.
        span_dir = o_tip - o_root
        norm = np.linalg.norm(span_dir)
        if norm < 1e-9:
            span_dir = np.array(root_plane.yDir.toTuple())
        else:
            span_dir = span_dir / norm

        chord_dir = np.array(root_plane.xDir.toTuple())
        up_dir = np.array(root_plane.zDir.toTuple())
        return origin, chord_dir, span_dir, up_dir

    # -- slicing -----------------------------------------------------------

    def _slice_outline(
        self,
        origin: np.ndarray,
        chord_dir: np.ndarray,
        up_dir: np.ndarray,
        span_dir: np.ndarray,
    ) -> tuple[list[tuple[float, float]], float, np.ndarray, np.ndarray]:
        """Cut the solid with the section plane and return the outline expressed
        in local ``(chord_u, height_v)`` coordinates, the chord length, and the
        LE point + chord unit vector (world) needed to rebuild world ``z``.
        """
        from cad_designer.aerosandbox.slicing import _section_outline_edges

        edges = _section_outline_edges(
            self._solid_shape.wrapped,
            tuple(float(c) for c in origin),
            tuple(float(c) for c in span_dir),
        )
        if not edges:
            return [], 0.0, origin, chord_dir

        pts_world: list[np.ndarray] = []
        for e in edges:
            for k in range(self._points_per_edge):
                t = k / float(self._points_per_edge - 1)
                p = e.positionAt(t)
                pts_world.append(np.array([p.x, p.y, p.z]))

        # Project to local (u along chord_dir, v along up_dir) about a LE anchor.
        # Anchor at the minimum chord projection so u starts at 0 at the LE.
        u_all = np.array([float(np.dot(p - origin, chord_dir)) for p in pts_world])
        v_all = np.array([float(np.dot(p - origin, up_dir)) for p in pts_world])
        u_min = float(u_all.min())
        u_all = u_all - u_min
        chord_len = float(u_all.max())
        le_anchor = origin + u_min * chord_dir

        outline = list(zip(u_all.tolist(), v_all.tolist(), strict=True))
        return outline, chord_len, le_anchor, chord_dir

    def _point_at(self, y_span: float, x_c: float) -> SectionPoint:
        origin, chord_dir, span_dir, up_dir = self._station_frame(y_span)
        outline, chord_len, le_anchor, chord_unit = self._slice_outline(
            origin, chord_dir, up_dir, span_dir
        )
        if chord_len <= 0.0:
            return SectionPoint(y_span, x_c, 0.0, 0.0, 0.0, 0.0)

        top_v, bottom_v = _outline_to_top_bottom(outline, x_c, chord_len)
        # Convert local v back to world z at the sampled chord ordinate.
        chord_point = le_anchor + (x_c * chord_len) * chord_unit
        base_z = float(chord_point[2])
        # up_dir z-component scales the local v into world z.
        up_z = float(up_dir[2])
        top_z = base_z + top_v * up_z
        bottom_z = base_z + bottom_v * up_z
        thickness = abs(top_z - bottom_z)
        center_z = (top_z + bottom_z) / 2.0
        return SectionPoint(
            y_span=y_span,
            x_c=x_c,
            thickness=thickness,
            top_z=max(top_z, bottom_z),
            bottom_z=min(top_z, bottom_z),
            center_z=center_z,
        )

    # -- public API --------------------------------------------------------

    def at(self, y_span: float, x_c: float) -> SectionPoint:
        """Section geometry at a single ``(y/span, x/c)`` location."""
        return self._point_at(y_span, x_c)

    def sample(self, y_spans: list[float], x_cs: list[float]) -> list[SectionPoint]:
        """Sample a grid: slice each unique ``y_span`` once, read all ``x_c``."""
        points: list[SectionPoint] = []
        for y in y_spans:
            origin, chord_dir, span_dir, up_dir = self._station_frame(y)
            outline, chord_len, le_anchor, chord_unit = self._slice_outline(
                origin, chord_dir, up_dir, span_dir
            )
            up_z = float(up_dir[2])
            for x in x_cs:
                if chord_len <= 0.0:
                    points.append(SectionPoint(y, x, 0.0, 0.0, 0.0, 0.0))
                    continue
                top_v, bottom_v = _outline_to_top_bottom(outline, x, chord_len)
                chord_point = le_anchor + (x * chord_len) * chord_unit
                base_z = float(chord_point[2])
                top_z = base_z + top_v * up_z
                bottom_z = base_z + bottom_v * up_z
                points.append(
                    SectionPoint(
                        y_span=y,
                        x_c=x,
                        thickness=abs(top_z - bottom_z),
                        top_z=max(top_z, bottom_z),
                        bottom_z=min(top_z, bottom_z),
                        center_z=(top_z + bottom_z) / 2.0,
                    )
                )
        return points

    def at_max_thickness(self, y_span: float) -> SectionPoint:
        """Section geometry at the *deepest* chord location on that section.

        Scans a chord grid and returns the point with the greatest thickness —
        the natural spar-placement reference.
        """
        candidates = np.linspace(0.05, 0.6, 23)
        best: SectionPoint | None = None
        origin, chord_dir, span_dir, up_dir = self._station_frame(y_span)
        outline, chord_len, le_anchor, chord_unit = self._slice_outline(
            origin, chord_dir, up_dir, span_dir
        )
        up_z = float(up_dir[2])
        if chord_len <= 0.0:
            return SectionPoint(y_span, 0.0, 0.0, 0.0, 0.0, 0.0)
        for x in candidates:
            top_v, bottom_v = _outline_to_top_bottom(outline, float(x), chord_len)
            chord_point = le_anchor + (float(x) * chord_len) * chord_unit
            base_z = float(chord_point[2])
            top_z = base_z + top_v * up_z
            bottom_z = base_z + bottom_v * up_z
            thickness = abs(top_z - bottom_z)
            if best is None or thickness > best.thickness:
                best = SectionPoint(
                    y_span=y_span,
                    x_c=float(x),
                    thickness=thickness,
                    top_z=max(top_z, bottom_z),
                    bottom_z=min(top_z, bottom_z),
                    center_z=(top_z + bottom_z) / 2.0,
                )
        return best if best is not None else SectionPoint(y_span, 0.0, 0.0, 0.0, 0.0, 0.0)

    def per_segment(self, n_span: int, n_chord: int) -> dict[int, list[SectionPoint]]:
        """Grid of section points per segment.

        For each segment, sample ``n_span`` stations across that segment's own
        span and ``n_chord`` chord positions. ``y_span`` on each point is the
        global (whole-surface) span fraction.
        """
        n_span = max(1, int(n_span))
        n_chord = max(1, int(n_chord))
        x_cs = np.linspace(0.05, 0.95, n_chord).tolist()
        total = float(sum(self._segment_lengths))
        grid: dict[int, list[SectionPoint]] = {}
        acc = 0.0
        for idx, seg_len in enumerate(self._segment_lengths):
            local_fracs = np.linspace(0.0, 1.0, n_span)
            y_globals = [(acc + f * seg_len) / total if total > 0 else 0.0 for f in local_fracs]
            grid[idx] = self.sample(y_globals, x_cs)
            acc += seg_len
        return grid
