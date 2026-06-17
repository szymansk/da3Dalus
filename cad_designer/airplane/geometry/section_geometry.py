"""Section-geometry primitive (gh-1020, gh-1046).

Recover, at a parametric location ``(y/span, x/c)``:

* ``thickness`` — vertical extent of the built section at that chord location
* ``top_z`` / ``bottom_z`` — upper / lower surface heights
* ``center_z`` — section mid-height (spar-placement reference)

Two evaluation modes (gh-1046):

* ``mode="analytic"`` (**default**) — blend the two segment airfoils
  analytically via :meth:`WingConfiguration.get_points_on_surface`. The loft is
  ``loft(ruled=True)`` (straight generators between airfoils), so an intermediate
  section is a *linear blend* of root and tip airfoils — exactly what
  ``get_points_on_surface`` returns from the cached, fully-transformed segment
  planes (twist + dihedral + sweep included). No solid is built, so this is
  ~1000× faster than slicing and is the path the interactive spar-sizing /
  spar-plan / section-geometry endpoints use. It still touches lightweight
  cadquery ``Plane``/``Vector`` math (milliseconds), but never
  :class:`WingLoftCreator`.
* ``mode="solid"`` — build the **real lofted CAD solid** with
  :class:`WingLoftCreator` and slice it. This is the slow (~6–13 s) path, kept
  reachable for true built-geometry fidelity (construction plans / STEP export).
  The loft encodes every relative rotation (dihedral via R_x, incidence/twist
  via R_y, sweep via the plane origin); slicing gives the exact *built* geometry.

The two modes agree to within a fraction of a percent on thickness and a
fraction of a mm on ``center_z`` on representative wings (both are ruled-linear),
which the ``requires_cadquery`` equivalence test asserts.

Frame: wing-local, origin at the wing-root LE, ``z`` vertical (the world frame
the loft is built in). Internally **millimetres** — the service layer converts
to metres for the API (project convention).

Platform guard: ``cadquery`` is excluded on ``linux/aarch64``. Both modes need
it (analytic for ``Plane`` math, solid for the loft); a clear
:class:`SectionGeometryUnavailableError` is raised when it is unavailable, so
callers can return a 503/422 rather than crashing.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

import numpy as np

from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)

# Platform guard — cadquery is excluded on linux/aarch64. Probe without binding
# an unused module-level name (keeps the import section lint-clean).
_HAS_CADQUERY = importlib.util.find_spec("cadquery") is not None


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


@dataclass(frozen=True)
class _SlicedSection:
    """A single section-plane cut, reusable across many ``x_c`` samples.

    ``outline`` is the cut expressed in local ``(chord_u, height_v)`` (mm).
    ``le_anchor`` + ``chord_unit`` recover the world chord line; ``up_z`` is the
    section up-vector's world-z component (carries dihedral tilt into world z).
    """

    outline: list[tuple[float, float]]
    chord_len: float
    le_anchor: np.ndarray
    chord_unit: np.ndarray
    up_z: float


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
    # Unreachable: total > 0 guarantees the last positive segment returns above;
    # an all-zero list is handled by the total <= 0 guard. Defensive only.
    return len(segment_lengths) - 1, 1.0  # pragma: no cover


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
    """Recover section geometry of a wing at parametric ``(y/span, x/c)`` points.

    Two modes (gh-1046):

    * ``mode="analytic"`` (default) — blend the segment airfoils analytically via
      :meth:`WingConfiguration.get_points_on_surface`; no solid is built.
    * ``mode="solid"`` — build the lofted CAD solid once and slice it on demand.
      ``sample`` groups requests by ``y_span`` so each section plane is cut once
      and all ``x_c`` are read off the same outline.

    Both expose the same ``at`` / ``sample`` / ``at_max_thickness`` /
    ``per_segment`` interface, so consumers are mode-agnostic.
    """

    def __init__(
        self,
        wing_config: WingConfiguration,
        points_per_edge: int = 80,
        mode: str = "analytic",
    ):
        if not _HAS_CADQUERY:
            raise SectionGeometryUnavailableError(
                "cadquery is not available on this platform; section geometry cannot be computed."
            )
        if mode not in ("analytic", "solid"):
            raise ValueError(
                f"unknown section-geometry mode {mode!r}; expected 'analytic' or 'solid'"
            )
        self._wing_config = wing_config
        self._mode = mode
        self._points_per_edge = max(8, min(int(points_per_edge), 4096))
        self._segment_lengths = [float(s.length) for s in wing_config.segments]
        # The solid is built lazily only in solid mode — the analytic path
        # (gh-1046) must NOT invoke WingLoftCreator (the ~13 s bottleneck).
        self._solid_shape = self._build_solid() if mode == "solid" else None

    # -- build -------------------------------------------------------------

    def _build_solid(
        self,
    ):  # pragma: no cover - cadquery boundary, covered by requires_cadquery slow tests
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

    def _slice_outline(  # pragma: no cover - cadquery boundary, covered by requires_cadquery slow tests
        self,
        origin: np.ndarray,
        chord_dir: np.ndarray,
        up_dir: np.ndarray,
        span_dir: np.ndarray,
    ) -> _SlicedSection:
        """Cut the solid with the section plane and return the outline expressed
        in local ``(chord_u, height_v)`` coordinates plus the metadata needed to
        rebuild world ``z`` at any chord ordinate.
        """
        from cad_designer.aerosandbox.slicing import _section_outline_edges

        edges = _section_outline_edges(
            self._solid_shape.wrapped,
            tuple(float(c) for c in origin),
            tuple(float(c) for c in span_dir),
        )
        if not edges:
            return _SlicedSection([], 0.0, origin, chord_dir, float(up_dir[2]))

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
        return _SlicedSection(
            outline=outline,
            chord_len=chord_len,
            le_anchor=le_anchor,
            chord_unit=chord_dir,
            up_z=float(up_dir[2]),
        )

    def _section(
        self, y_span: float
    ) -> _SlicedSection:  # pragma: no cover - cadquery boundary (slow tests + mocked in fast)
        """Slice the solid at ``y_span`` and return the reusable section data."""
        origin, chord_dir, span_dir, up_dir = self._station_frame(y_span)
        return self._slice_outline(origin, chord_dir, up_dir, span_dir)

    @staticmethod
    def _point_from_section(section: _SlicedSection, y_span: float, x_c: float) -> SectionPoint:
        """Read a SectionPoint off an already-sliced section at chord ``x_c``.

        The local upper/lower heights ``v`` are projected into world ``z`` about
        the chord-line z at that ordinate (``up_z`` carries the dihedral tilt).
        """
        if section.chord_len <= 0.0:
            return SectionPoint(y_span, x_c, 0.0, 0.0, 0.0, 0.0)
        top_v, bottom_v = _outline_to_top_bottom(section.outline, x_c, section.chord_len)
        chord_point = section.le_anchor + (x_c * section.chord_len) * section.chord_unit
        base_z = float(chord_point[2])
        top_z = base_z + top_v * section.up_z
        bottom_z = base_z + bottom_v * section.up_z
        return SectionPoint(
            y_span=y_span,
            x_c=x_c,
            thickness=abs(top_z - bottom_z),
            top_z=max(top_z, bottom_z),
            bottom_z=min(top_z, bottom_z),
            center_z=(top_z + bottom_z) / 2.0,
        )

    # -- analytic evaluation (gh-1046, default) ----------------------------

    def _analytic_point(self, y_span: float, x_c: float) -> SectionPoint:
        """SectionPoint at ``(y/span, x/c)`` via the analytic airfoil blend.

        Maps ``y_span`` → ``(segment, relative_length)`` with the same
        accumulated-length logic the solid path uses, then reads the upper /
        lower surface points from
        :meth:`WingConfiguration.get_points_on_surface` in the **world** frame
        (origin root-LE, z up — the same frame the solid slice returns). Because
        the loft is ruled, this linear root↔tip blend equals the built section.
        Twist / dihedral / sweep are baked into the segment workplanes, so they
        appear in the placement exactly as for the slice.

        ``thickness`` is the vertical (world-z) extent between the surfaces and
        ``center_z`` their midpoint — matching the solid-slice semantics.
        """
        idx, rel = _y_span_to_segment(y_span, self._segment_lengths)
        top, bottom = self._wing_config.get_points_on_surface(
            segment=idx,
            relative_chord=float(x_c),
            relative_length=float(rel),
            coordinate_system="world",
        )
        top_z = float(top.z)
        bottom_z = float(bottom.z)
        return SectionPoint(
            y_span=y_span,
            x_c=x_c,
            thickness=abs(top_z - bottom_z),
            top_z=max(top_z, bottom_z),
            bottom_z=min(top_z, bottom_z),
            center_z=(top_z + bottom_z) / 2.0,
        )

    # -- public API --------------------------------------------------------

    def at(self, y_span: float, x_c: float) -> SectionPoint:
        """Section geometry at a single ``(y/span, x/c)`` location."""
        if self._mode == "analytic":
            return self._analytic_point(y_span, x_c)
        return self._point_from_section(self._section(y_span), y_span, x_c)

    def sample(self, y_spans: list[float], x_cs: list[float]) -> list[SectionPoint]:
        """Sample a grid.

        Analytic: evaluate every ``(y, x)`` directly. Solid: slice each unique
        ``y_span`` once and read all ``x_c`` off the same outline.
        """
        if self._mode == "analytic":
            return [self._analytic_point(y, x) for y in y_spans for x in x_cs]
        points: list[SectionPoint] = []
        for y in y_spans:
            section = self._section(y)
            points.extend(self._point_from_section(section, y, x) for x in x_cs)
        return points

    def at_max_thickness(self, y_span: float) -> SectionPoint:
        """Section geometry at the *deepest* chord location on that section.

        Scans a chord grid and returns the point with the greatest thickness —
        the natural spar-placement reference.
        """
        candidates = np.linspace(0.05, 0.6, 23)
        if self._mode == "analytic":
            points = (self._analytic_point(y_span, float(x)) for x in candidates)
            return max(points, key=lambda p: p.thickness)
        section = self._section(y_span)
        if section.chord_len <= 0.0:
            return SectionPoint(y_span, 0.0, 0.0, 0.0, 0.0, 0.0)
        points = (self._point_from_section(section, y_span, float(x)) for x in candidates)
        return max(points, key=lambda p: p.thickness)

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
