"""Spar-vector solver core (gh-1030).

Turn loads (#1002), spar-section sizing (#1008) and the real section envelope
(#1019, :class:`SectionGeometry`) into a **buildable spar layout** — a
:class:`SparPlan`. The plan says, for the front (bending) and rear (torsion)
spars, where each straight piece sits, which direction it runs, its
outer/inner diameter, how consecutive pieces and the two wing halves join,
and the governing station + utilisation.

This module is **pure decision logic**. All CAD/sizing access is pushed behind
a thin seam: :func:`build_stations_from_geometry` reads a
:class:`SectionGeometry` once and produces a flat list of :class:`StationData`
(containment band + strength-required OD per station). The solver
(:func:`plan_spar`, :func:`solve_spar_plan`) consumes only ``StationData``, so
every branch — greedy fit, telescoping split, root collinearity, bent-pin — is
exercised on the CI fast tier with hand-built stations (no cadquery).

Topology is **read-only**: nothing here constructs into ``Airfoil`` /
``WingSegment`` / ``WingConfiguration``; we only read them via ``SectionGeometry``.
The endpoint (#1031) and CAD-insertion step (#1032) wrap this output.

Units: **millimetres** throughout, wing-local frame (origin root-LE, z up) —
the same frame ``SectionGeometry`` returns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from app.services.spar_sizing import required_section_modulus, solve_dimension

# A tube whose required strength OD exceeds the local containment band by more
# than this absolute slack (mm) forces a split. Small float tolerance.
_FIT_TOL_MM = 1e-6


class SparRole(str, Enum):
    """Which structural spar a plan/piece belongs to."""

    FRONT = "front"
    REAR = "rear"


@dataclass(frozen=True)
class StationData:
    """One sampled spar station — the solver's only geometric input.

    All lengths in **mm**, wing-local frame. ``band_lo``/``band_hi`` are the
    *contained* z-band at this station's spar chord location, i.e. already
    inset by the skin/packing clearance: a tube of outer diameter ``D``
    centred on ``center_z`` fits iff ``[center_z - D/2, center_z + D/2]`` lies
    inside ``[band_lo, band_hi]``. ``required_od`` is the strength-required
    outer diameter from #1008 sizing at this station.
    """

    y_span: float
    y_mm: float
    x_c: float
    center_z: float
    band_lo: float
    band_hi: float
    required_od: float


@dataclass(frozen=True)
class SparSpec:
    """Knobs for a single spar fit."""

    role: SparRole
    shape: str = "tube"  # round tube (telescoping- and bent-pin-friendly)
    wall_factor: float = 0.6  # piece ID = wall_factor * OD when no strength ID given


@dataclass
class SparPiece:
    """One straight spar piece (a Spare-to-be), in mm."""

    role: SparRole
    spare_origin: tuple[float, float, float]
    spare_vector: tuple[float, float, float]
    outer_d: float
    inner_d: float
    shape: str
    governing_y: float
    utilisation: float
    joint_to_next: str | None = None  # "telescoping" between consecutive pieces

    @property
    def wall(self) -> float:
        return max(0.0, (self.outer_d - self.inner_d) / 2.0)

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "spare_origin": list(self.spare_origin),
            "spare_vector": list(self.spare_vector),
            "outer_d": self.outer_d,
            "inner_d": self.inner_d,
            "wall": self.wall,
            "shape": self.shape,
            "governing_y": self.governing_y,
            "utilisation": self.utilisation,
            "joint_to_next": self.joint_to_next,
        }


@dataclass
class SparPlan:
    """The full two-spar layout for a wing (front + rear). Serialisable."""

    front_pieces: list[SparPiece] = field(default_factory=list)
    rear_pieces: list[SparPiece] = field(default_factory=list)
    front_joint: str = "continuous"  # continuous | reinforcement+joiner
    rear_joint: str = "continuous"  # continuous | bent-pin
    reinforcement: SparPiece | None = None

    def to_dict(self) -> dict:
        return {
            "front_pieces": [p.to_dict() for p in self.front_pieces],
            "rear_pieces": [p.to_dict() for p in self.rear_pieces],
            "front_joint": self.front_joint,
            "rear_joint": self.rear_joint,
            "reinforcement": self.reinforcement.to_dict() if self.reinforcement else None,
        }


# ---------------------------------------------------------------------------
# Geometry helpers (pure)
# ---------------------------------------------------------------------------


def _axis_z_at(run: list[StationData], station: StationData) -> float:
    """Z of a *straight* piece's axis at ``station``.

    A piece is a single straight line from its root station's ``center_z`` to
    its tip station's ``center_z`` (by ``y_mm``). The axis z at an interior
    station is the linear interpolation along that line — NOT the station's own
    ``center_z`` (the piece cannot follow per-station jitter; it is straight).
    """
    root, tip = run[0], run[-1]
    span = tip.y_mm - root.y_mm
    if abs(span) < 1e-9:
        return root.center_z
    t = (station.y_mm - root.y_mm) / span
    return root.center_z + t * (tip.center_z - root.center_z)


def _run_fits(od: float, run: list[StationData]) -> bool:
    """True if a straight tube of outer diameter ``od`` running along the run's
    root→tip axis stays inside EVERY covered station's contained band."""
    half = od / 2.0
    for s in run:
        axis_z = _axis_z_at(run, s)
        if axis_z - half < s.band_lo - _FIT_TOL_MM:
            return False
        if axis_z + half > s.band_hi + _FIT_TOL_MM:
            return False
    return True


def _max_od_for_run(run: list[StationData]) -> float:
    """Largest straight-tube OD that fits every covered station's band when the
    axis follows the run's root→tip line."""
    best = float("inf")
    for s in run:
        axis_z = _axis_z_at(run, s)
        best = min(best, 2.0 * (axis_z - s.band_lo), 2.0 * (s.band_hi - axis_z))
    return max(0.0, best)


def _governing_od(stations: list[StationData]) -> float:
    """Governing OD of a piece = the most-inboard / highest required OD it covers.

    By the spec the inboard (root-side) station carries the highest moment, so
    its strength-required OD governs the whole straight piece.
    """
    return max(s.required_od for s in stations)


def _unit_vector(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    if n < 1e-12:
        return (0.0, 1.0, 0.0)
    return (dx / n, dy / n, dz / n)


# ---------------------------------------------------------------------------
# Greedy straight-piece fit (root -> tip)
# ---------------------------------------------------------------------------


def plan_spar(stations: list[StationData], spec: SparSpec) -> list[SparPiece]:
    """Greedy root→tip fit into straight telescoping pieces.

    Extend a piece while a straight tube of the piece's governing OD (the
    most-inboard, highest-moment station it covers) stays inside EVERY covered
    station's band. On failure → close the piece, start the next; the joint is
    **telescoping** (next piece OD = this piece ID).

    Confirmed priority rule: keep a piece going only while its strength-required
    OD fits the local section at every covered station. Otherwise split +
    telescope. **Strength beats part-count.**
    """
    if not stations:
        return []

    pieces: list[SparPiece] = []
    run: list[StationData] = [stations[0]]

    for st in stations[1:]:
        candidate = run + [st]
        governing_od = _governing_od(candidate)
        # A straight tube of the governing OD must stay inside every covered
        # station's band along the candidate's own straight root→tip axis.
        if _run_fits(governing_od, candidate):
            run = candidate
            continue
        # Close the current run, telescope into the next.
        pieces.append(run)  # placeholder, filled below
        run = [st]

    pieces.append(run)

    # Convert station-runs to SparPieces, wiring telescoping IDs.
    built: list[SparPiece] = []
    prev_inner: float | None = None
    for idx, run_stations in enumerate(pieces):
        od = _governing_od(run_stations)
        if prev_inner is not None:
            # telescoping: this (outer/tip-side) piece OD = previous piece ID.
            # If strength needs more than the previous bore, the previous piece
            # was sized too small — but strength beats part-count, so this OD is
            # max(prev_inner, strength OD). Keep the bore relation by widening.
            od = max(prev_inner, od)
        inner_d = _bore_for(run_stations, spec, od)
        piece = _piece_from_run_with_od(run_stations, spec, od, inner_d)
        built.append(piece)
        if idx < len(pieces) - 1:
            piece.joint_to_next = "telescoping"
        prev_inner = inner_d
    return built


def _bore_for(run: list[StationData], spec: SparSpec, od: float) -> float:
    """Strength-driven bore for a tube of outer diameter ``od``.

    Uses #1008 tube sizing at the governing station so the bore reflects the
    real load; falls back to a fixed wall fraction when sizing can't solve a
    feasible bore (e.g. strength wants a solid).
    """
    governing = run[0]
    # Reconstruct a required section modulus consistent with the station's
    # required_od (the strength OD already encodes the moment). The bore is the
    # largest inner diameter that still meets strength at this OD.
    # required_od was sized as a *rod-equivalent*; for a tube of larger OD we
    # can hollow it. Use solve_dimension's tube path with the governing W.
    erf_w = required_section_modulus_from_od(governing.required_od)
    sol = solve_dimension(shape="tube", erf_w=erf_w, outer_mm=od)
    if sol["feasible"] and sol["inner_mm"] is not None:
        return float(sol["inner_mm"])
    return max(0.0, od * spec.wall_factor)


def required_section_modulus_from_od(od: float) -> float:
    """Section modulus a solid rod of diameter ``od`` provides (mm³).

    #1008 sizes the strength OD as the minimum solid-rod diameter, so its
    section modulus W = d³/10 is exactly the required W. Inverting keeps the
    solver decoupled from the original moment while staying load-consistent.
    """
    return od**3 / 10.0


def _piece_from_run_with_od(
    run: list[StationData], spec: SparSpec, od: float, inner_d: float
) -> SparPiece:
    governing = run[0]
    root = run[0]
    tip = run[-1]
    origin = (0.0, root.y_mm, root.center_z)
    vector = _unit_vector(origin, (0.0, tip.y_mm, tip.center_z))
    tightest = _max_od_for_run(run)
    utilisation = min(1.0, od / tightest) if tightest > 0 else 1.0
    return SparPiece(
        role=spec.role,
        spare_origin=origin,
        spare_vector=vector,
        outer_d=od,
        inner_d=inner_d,
        shape=spec.shape,
        governing_y=governing.y_mm,
        utilisation=utilisation,
    )


# ---------------------------------------------------------------------------
# Root collinearity / reinforcement (front) and bent-pin (rear)
# ---------------------------------------------------------------------------


def _inboard_collinear(
    left: list[StationData], right: list[StationData], tol_mm: float = 5.0
) -> bool:
    """Can the inboard pieces of the two halves be one straight collinear line
    through y=0?

    A straight beam through y=0 collinear across the root requires the two
    inboard stations to share the centreline z (within ``tol_mm``) and the
    pieces to extend symmetrically. We test the root-station center_z match —
    if the halves' roots sit at different heights, a single straight beam can't
    pass through both, so a reinforcement is needed.
    """
    if not left or not right:
        return False
    z_left = left[0].center_z
    z_right = right[0].center_z
    return abs(z_left - z_right) <= tol_mm


def _straight_collinear_in_envelope(left: list[StationData], right: list[StationData]) -> bool:
    """Does a straight collinear rod through y=0 stay inside the band along its
    whole length on both halves?

    Geometry-derived bent-pin trigger (spec §"Defaults"): the straight rod runs
    along the root centreline z; at every station the rod's z is that constant
    root z, and it must lie inside ``[band_lo, band_hi]``. Under strong dihedral
    the outboard band rises away from the root z → the rod exits → bent-pin.
    """
    if not left or not right:
        return False
    root_z = (left[0].center_z + right[0].center_z) / 2.0
    for s in list(left) + list(right):
        if root_z < s.band_lo - _FIT_TOL_MM or root_z > s.band_hi + _FIT_TOL_MM:
            return False
    return True


def _reinforcement_piece(
    left: list[StationData], right: list[StationData], spec: SparSpec
) -> SparPiece:
    """A short, truly-collinear reinforcement at the max-moment (root) station.

    Sized to the root moment (largest required OD across both root stations),
    placed through y=0 along the centreline, spanning a short symmetric overlap
    into each half.
    """
    root_od = max(left[0].required_od, right[0].required_od)
    root_z = (left[0].center_z + right[0].center_z) / 2.0
    # short symmetric span: reach to the first outboard station of each half
    reach = min(
        abs(left[1].y_mm) if len(left) > 1 else abs(left[0].y_mm) + root_od,
        abs(right[1].y_mm) if len(right) > 1 else abs(right[0].y_mm) + root_od,
    )
    origin = (0.0, -reach, root_z)
    vector = (0.0, 1.0, 0.0)  # collinear through y=0
    erf_w = required_section_modulus_from_od(root_od)
    sol = solve_dimension(shape="tube", erf_w=erf_w, outer_mm=root_od)
    inner_d = (
        float(sol["inner_mm"])
        if sol["feasible"] and sol["inner_mm"]
        else root_od * spec.wall_factor
    )
    return SparPiece(
        role=SparRole.FRONT,
        spare_origin=origin,
        spare_vector=vector,
        outer_d=root_od,
        inner_d=inner_d,
        shape=spec.shape,
        governing_y=0.0,
        utilisation=1.0,
    )


def solve_spar_plan(
    front_left: list[StationData],
    front_right: list[StationData],
    rear_left: list[StationData] | None = None,
    rear_right: list[StationData] | None = None,
    front_spec: SparSpec | None = None,
    rear_spec: SparSpec | None = None,
) -> SparPlan:
    """Solve the full two-spar plan for a wing.

    Front spar: greedy fit per half + root-collinearity test (single
    carry-through vs reinforcement). Rear spar: greedy fit + geometry-derived
    bent-pin test under dihedral. ``*_left`` station ``y_mm`` are negative
    (port), ``*_right`` positive (starboard); each list is ordered root→tip.
    """
    front_spec = front_spec or SparSpec(role=SparRole.FRONT)
    rear_spec = rear_spec or SparSpec(role=SparRole.REAR)

    plan = SparPlan()

    # --- front ---
    plan.front_pieces = plan_spar(front_right, front_spec)
    if _inboard_collinear(front_left, front_right):
        plan.front_joint = "continuous"
    else:
        plan.front_joint = "reinforcement+joiner"
        plan.reinforcement = _reinforcement_piece(front_left, front_right, front_spec)

    # --- rear ---
    if rear_left and rear_right:
        plan.rear_pieces = plan_spar(rear_right, rear_spec)
        if _straight_collinear_in_envelope(rear_left, rear_right):
            plan.rear_joint = "continuous"
        else:
            plan.rear_joint = "bent-pin"

    return plan


# ---------------------------------------------------------------------------
# Geometry seam — reads SectionGeometry + #1008 sizing into StationData.
# Mocked in fast tests; exercised by the requires_cadquery slow tests.
# ---------------------------------------------------------------------------


def build_stations_from_geometry(
    geometry,
    *,
    moment_fn: Callable[[float], float],
    sigma_allow_mpa: float,
    n_span: int = 6,
    x_c: float | None = None,
    packing_factor: float = 0.8,
    safety_factor_j: float = 1.5,
    g_limit: float = 3.0,
) -> list[StationData]:
    """Sample a :class:`SectionGeometry` into solver-ready :class:`StationData`.

    For each of ``n_span`` stations root→tip: pick the spar chord location
    (``x_c`` if given, else the section's max-thickness location), read the
    contained band ``[bottom_z + clr, top_z - clr]`` (clr from ``packing_factor``)
    and ``center_z``, and compute the strength-required OD from #1008 sizing
    using the station's design moment ``M_design = |M| · g · j``.
    """
    import numpy as np

    y_spans = np.linspace(0.0, 1.0, max(2, n_span)).tolist()
    stations: list[StationData] = []
    for y_span in y_spans:
        if x_c is None:
            pt = geometry.at_max_thickness(y_span)
        else:
            pt = geometry.at(y_span, x_c)
        if pt.thickness <= 0.0:  # pragma: no cover - cadquery boundary degenerate section
            continue
        clr = (1.0 - packing_factor) / 2.0 * pt.thickness
        band_lo = pt.bottom_z + clr
        band_hi = pt.top_z - clr
        m_design = abs(moment_fn(y_span)) * g_limit * safety_factor_j
        erf_w = required_section_modulus(m_design, sigma_allow_mpa)
        # strength OD as the minimum solid-rod diameter meeting required W.
        sol = solve_dimension(shape="rod", erf_w=erf_w, outer_mm=max(band_hi - band_lo, 1.0))
        required_od = float(sol["solved_mm"]) if sol["solved_mm"] else 0.0
        stations.append(
            StationData(
                y_span=y_span,
                y_mm=pt.y_span * _half_span_mm(geometry),
                x_c=pt.x_c,
                center_z=pt.center_z,
                band_lo=band_lo,
                band_hi=band_hi,
                required_od=required_od,
            )
        )
    return stations


def _half_span_mm(geometry) -> float:
    lengths = getattr(geometry, "_segment_lengths", None)
    if not lengths:
        return 0.0  # pragma: no cover - cadquery boundary
    return float(sum(lengths))
