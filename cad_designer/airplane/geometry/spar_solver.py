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

# Span fraction used to sample the root station instead of the degenerate
# y_span=0 slice (gh-1037 #4). Small enough to still represent the max-moment
# root, large enough to land on a valid (non-pinched) section.
_ROOT_EPS = 1e-3

# gh-1076: buildable-minimum spar outer diameter (mm). A tip station whose
# design-moment-driven required OD falls below this floor carries negligible
# bending load — no orderable/cuttable carbon spar exists that small, and the
# D-box skin + ribs carry the tip. Such trailing stations are reported as an
# explicit *no-spar region* on the plan (see :func:`solve_spar_plan`) rather
# than emitted as a degenerate Ø≈0 piece whose wall rounds to 0. The threshold
# is applied on ``required_od``, which is already the design moment (M·g·j)
# sizing produced upstream in :func:`build_stations_from_geometry`. Tie to the
# real CF-pin stock floor (#1081) when that lands.
NEGLIGIBLE_OD_FLOOR_MM = 1.0


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
    #: Radial clearance (mm) at a telescoping joint: the tip-side piece OD must
    #: be at least this much smaller than the root-side piece bore so it can
    #: slide in (glue gap / slip fit). gh-1037.
    telescope_clearance_mm: float = 0.5


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
    #: gh-1072: chordwise location (x/c, 0..1) this piece was placed at — the
    #: governing (root-side) station's ``x_c``. Front ≈ section max-thickness;
    #: rear = the requested rear x/c clamped forward of the control surface.
    x_over_chord: float = 0.0
    length: float = 0.0  # mm, root→tip span of this straight piece (#1032)
    joint_to_next: str | None = None  # "telescoping" between consecutive pieces
    feasible: bool = True  # gh-1037: False when no round tube strong enough fits
    infeasibility_reason: str | None = None
    # gh-1080: extended dims for rectangular/capped; None for tube/rod.
    width: float | None = None  # mm, web/flange width for rectangular
    height: float | None = None  # mm, profile height for rectangular (= band depth)
    cap_width: float | None = None  # mm, flange width for capped (I/C-beam)

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
            "x_over_chord": self.x_over_chord,
            "length": self.length,
            "joint_to_next": self.joint_to_next,
            "feasible": self.feasible,
            "infeasibility_reason": self.infeasibility_reason,
            # gh-1080: extended dims (None for tube/rod)
            "width": self.width,
            "height": self.height,
            "cap_width": self.cap_width,
        }


@dataclass
class SparPlan:
    """The full two-spar layout for a wing (front + rear). Serialisable."""

    front_pieces: list[SparPiece] = field(default_factory=list)
    rear_pieces: list[SparPiece] = field(default_factory=list)
    front_joint: str = "continuous"  # continuous | reinforcement+joiner
    rear_joint: str = "continuous"  # continuous | bent-pin
    reinforcement: SparPiece | None = None
    feasible: bool = True  # gh-1037: False when any piece cannot contain a strong tube
    infeasibility_reason: str | None = None
    # gh-1076: spanwise |y| (mm, starboard half) where the tip-most no-spar
    # region begins — the load-bearing span ends here and the D-box skin + ribs
    # carry the rest to the tip. ``None`` means the spar runs to the tip; the
    # root y means the whole span is negligible (no spar at all).
    front_no_spar_from_y: float | None = None
    rear_no_spar_from_y: float | None = None

    def to_dict(self) -> dict:
        return {
            "front_pieces": [p.to_dict() for p in self.front_pieces],
            "rear_pieces": [p.to_dict() for p in self.rear_pieces],
            "front_joint": self.front_joint,
            "rear_joint": self.rear_joint,
            "reinforcement": self.reinforcement.to_dict() if self.reinforcement else None,
            "feasible": self.feasible,
            "infeasibility_reason": self.infeasibility_reason,
            "front_no_spar_from_y": self.front_no_spar_from_y,
            "rear_no_spar_from_y": self.rear_no_spar_from_y,
        }


# Default chordwise margin (fraction of chord) a COMPUTED rear/torsion spar
# keeps in front of a control-surface hinge line so it never overlaps the
# movable surface. gh-1059.
_REAR_CLEARANCE_FRACTION = 0.03

# Smallest chordwise location a clamped rear spar may take (never at/forward of
# the LE). gh-1059.
_MIN_REAR_X_C = 0.05


# ---------------------------------------------------------------------------
# Geometry helpers (pure)
# ---------------------------------------------------------------------------


def rear_spar_x_c_with_clearance(
    requested_x_c: float,
    *,
    control_surface_hinge_x_c: float | None,
    clearance: float = _REAR_CLEARANCE_FRACTION,
) -> float:
    """Constrain a COMPUTED rear/torsion spar to stay forward of a control
    surface (gh-1059).

    A control surface is the movable region *behind* its hinge line
    (``control_surface_hinge_x_c``, x/c). A solver-placed spar must never
    overlap it, so the rear spar's chordwise location is pulled forward to
    ``hinge - clearance`` when the request would sit at or behind the hinge.
    A request already forward of the clearance line is kept unchanged, and a
    wing with no control surface keeps its requested ``x_c``.

    The result is floored at :data:`_MIN_REAR_X_C` so a control surface whose
    hinge sits near the LE cannot push the spar onto/forward of the leading
    edge. This guard applies ONLY to computed spars — a designer may still
    place a reinforcing spar inside a control surface manually.
    """
    if control_surface_hinge_x_c is None:
        return requested_x_c
    limit = control_surface_hinge_x_c - clearance
    safe = min(requested_x_c, limit)
    return max(safe, _MIN_REAR_X_C)


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


@dataclass
class _Run:
    """A straight-piece run during fitting.

    ``stations`` are every station the straight tube physically covers (used for
    containment fit and length). ``governing`` are the stations whose strength
    drives the piece's OD/bore — this *excludes* a station borrowed from an
    inboard neighbour as a telescoping overlap, since the inner piece reinforces
    the spar there.
    """

    stations: list[StationData]
    governing: list[StationData]


def _split_into_runs(stations: list[StationData]) -> list[_Run]:
    """Break the station list into straight-piece runs (root→tip).

    Partition the stations greedily: extend a run while a straight tube of the
    run's governing OD (the most-inboard, highest-moment station it covers)
    stays inside EVERY covered station's band; on failure start the next run at
    the breaking station. This yields a clean partition (no station appears in
    two runs).

    A partition run may collapse to a single station — physically a zero-length
    piece, which is not a structural object (gh-1037 #2). We repair that by
    overlapping such a run **rootward** into the previous run's tip station: the
    telescoping joint *is* an overlap region, so a piece legitimately reaches
    back to its inboard neighbour's boundary. The borrowed root station extends
    the piece's geometry but does not drive its governing OD.
    """
    partitions: list[list[StationData]] = []
    run: list[StationData] = [stations[0]]
    for st in stations[1:]:
        candidate = run + [st]
        if _run_fits(_governing_od(candidate), candidate):
            run = candidate
            continue
        partitions.append(run)
        run = [st]
    partitions.append(run)

    runs: list[_Run] = []
    for idx, part in enumerate(partitions):
        if len(part) == 1 and idx > 0:
            # borrow the inboard neighbour's tip as a rootward overlap
            runs.append(_Run(stations=[partitions[idx - 1][-1], *part], governing=list(part)))
        elif len(part) == 1 and len(partitions) > 1:
            # single root partition: borrow the next neighbour's root tipward
            runs.append(_Run(stations=[*part, partitions[idx + 1][0]], governing=list(part)))
        else:
            runs.append(_Run(stations=list(part), governing=list(part)))
    return runs


def plan_spar(stations: list[StationData], spec: SparSpec) -> list[SparPiece]:
    """Greedy root→tip fit into straight telescoping pieces.

    Split the stations into straight runs (:func:`_split_into_runs`), then size
    each piece. The telescoping relation runs **inboard**: the tip-side (outer)
    piece must slide INTO the root-side (inner) piece's bore, so

        ``OD_outer ≤ ID_inner − clearance``

    and OD is **non-increasing outboard** (root ≥ tip), consistent with the
    bending moment M(y). We size the pieces tip→root: each piece's OD is its own
    strength-required OD, then each inner (root-side) piece's bore is grown to
    admit the adjacent outer piece's OD plus clearance, and the inner OD grows
    to keep a sane wall around that bore (gh-1037 #1). When a piece's required OD
    cannot be contained by its section, it is marked infeasible with a reason
    rather than emitting a fake feasible plan (gh-1037 #3).

    Confirmed priority rule: keep a piece continuous only while its
    strength-required OD fits the local section at every covered station.
    Otherwise split + telescope. **Strength beats part-count.**
    """
    if not stations:
        return []

    runs = _split_into_runs(stations)

    # Base OD per piece = the piece's own strength-required (governing) OD.
    ods = [_governing_od(r.governing) for r in runs]

    # Propagate the bore demand INBOARD (tip→root): each inner piece must admit
    # the outer piece's OD plus clearance through its bore. The inner bore sets a
    # floor on the inner OD (bore + a minimal wall), so the root piece grows to
    # satisfy the whole telescoping stack. This also enforces OD non-increasing
    # outboard.
    #
    # gh-1080: bore-propagation is TUBE-ONLY. Non-tube shapes (rod/rectangular/
    # capped) connect via discrete joiners — they have no hollow bore to
    # telescope into, so clearance-driven bore growth is meaningless and would
    # wrongly over-dimension inner pieces. Rods are solid (inner_d=0) throughout.
    bores: list[float] = [0.0] * len(runs)
    if spec.shape == "tube":
        # tip piece (last): bore is purely strength-driven.
        bores[-1] = _bore_for(runs[-1], spec, ods[-1])
        # inner pieces (root→tip order, processed tip→root): each must admit the
        # adjacent outer piece's OD plus clearance through its bore, AND keep at
        # least the strength-required bore, AND a minimal wall around the bore.
        for i in range(len(runs) - 2, -1, -1):
            telescope_bore = ods[i + 1] + 2.0 * spec.telescope_clearance_mm
            strength_bore = _bore_for(runs[i], spec, ods[i])
            bore = max(telescope_bore, strength_bore)
            min_od_for_bore = bore + 2.0 * spec.telescope_clearance_mm
            if ods[i] < min_od_for_bore:
                ods[i] = min_od_for_bore
            bores[i] = bore
    # For non-tube shapes bores stays all-zero (solid sections).

    built: list[SparPiece] = []
    for idx, run in enumerate(runs):
        piece = _piece_from_run_with_od(run, spec, ods[idx], bores[idx])
        if idx < len(runs) - 1:
            # gh-1075: only round tubes can physically telescope (they have a bore
            # to slide into). Non-tube shapes (rod, rectangular, capped) must use
            # a discrete joiner instead. Fix at the SOURCE per Iron Law #4.
            piece.joint_to_next = "telescoping" if spec.shape == "tube" else "joiner"
        built.append(piece)
    return _drop_zero_od_tip(built)


def _drop_zero_od_tip(pieces: list[SparPiece]) -> list[SparPiece]:
    """Drop degenerate sub-floor trailing tip pieces (gh-1045/#1057, gh-1076).

    Toward the tip the bending moment M(y)->0, so the strength-required OD falls
    below :data:`NEGLIGIBLE_OD_FLOOR_MM` — no orderable/cuttable carbon spar that
    small exists and the D-box skin + ribs carry the tip. Such a trailing piece
    is not a physical structural object (a Ø≈0 tube whose wall rounds to 0 is the
    gh-1076 symptom); drop every trailing piece below the floor.

    gh-1076 Option A: the remaining last real piece KEEPS its natural length — it
    ends where load ceased to be structurally relevant — and its joint becomes
    continuous (``None``). The tip-most no-spar region is reported explicitly on
    the plan (see :func:`solve_spar_plan`) rather than swallowed by extending the
    last piece to the tip (which was gh-1057's behaviour, now superseded).

    Because spar dimensions are non-increasing root->tip, sub-floor stations are
    always tip-most; popping from the tail keeps the kept run contiguous.
    """
    kept = list(pieces)
    while kept and kept[-1].outer_d < NEGLIGIBLE_OD_FLOOR_MM:
        kept.pop()
    if not kept:
        # every station negligible -> no structural spar at all.
        return []
    kept[-1].joint_to_next = None
    return kept


def _no_spar_from_y(stations: list[StationData], pieces: list[SparPiece]) -> float | None:
    """Spanwise |y| (mm) where the tip-most no-spar region begins, else ``None``.

    gh-1076 Option A. When trailing negligible-load stations produced no
    buildable piece, the region from the last real piece's tip to the wing tip
    carries no spar. Returns the ``|y|`` where that region starts (the root ``y``
    when the whole span is negligible), or ``None`` when the spar runs to the
    tip. ``y_mm`` is signed by half (port negative); the plan is symmetric, so we
    report the starboard-half magnitude.
    """
    if not stations:
        return None
    tip_y = max(abs(s.y_mm) for s in stations)
    if not pieces:
        return min(abs(s.y_mm) for s in stations)  # whole span negligible
    last = pieces[-1]
    last_tip_y = abs(last.spare_origin[1] + last.length * last.spare_vector[1])
    if last_tip_y < tip_y - _FIT_TOL_MM:
        return last_tip_y
    return None


def _bore_for(run: _Run, spec: SparSpec, od: float) -> float:
    """Strength-driven bore for a tube of outer diameter ``od``.

    Uses #1008 tube sizing at the governing station so the bore reflects the
    real load; falls back to a fixed wall fraction when sizing can't solve a
    feasible bore (e.g. strength wants a solid).
    """
    governing_od = _governing_od(run.governing)
    # Reconstruct a required section modulus consistent with the governing
    # station's required_od (the strength OD already encodes the moment). The
    # bore is the largest inner diameter that still meets strength at this OD.
    # required_od was sized as a *rod-equivalent*; for a tube of larger OD we
    # can hollow it. Use solve_dimension's tube path with the governing W.
    erf_w = required_section_modulus_from_od(governing_od)
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


def _piece_from_run_with_od(run: _Run, spec: SparSpec, od: float, inner_d: float) -> SparPiece:
    governing = run.governing[0]
    root = run.stations[0]
    tip = run.stations[-1]
    origin = (0.0, root.y_mm, root.center_z)
    tip_point = (0.0, tip.y_mm, tip.center_z)
    vector = _unit_vector(origin, tip_point)
    length = math.dist(origin, tip_point)
    tightest = _max_od_for_run(run.stations)
    # Honest utilisation (gh-1037 #3): the fraction of the tightest containment
    # band the piece OD uses. It may exceed 1 when no round tube strong enough
    # fits — we report that truthfully instead of clamping to a fake 1.0. When
    # the band has literally no room (tightest == 0) we floor the denominator to
    # a tiny value so the ratio is large-but-finite (JSON-serialisable) and
    # still clearly signals infeasibility.
    utilisation = od / max(tightest, _FIT_TOL_MM)
    feasible = od <= tightest + _FIT_TOL_MM and tightest > 0
    reason: str | None = None
    if not feasible:
        depth = max(0.0, governing.band_hi - governing.band_lo)
        reason = (
            f"required OD {od:.1f} mm exceeds section depth {depth:.1f} mm at "
            f"y={governing.y_mm:.0f} mm; increase root depth/chord or reduce "
            "design load — a round tube is the least efficient bending member, "
            "consider a capped/box spar"
        )
    return SparPiece(
        role=spec.role,
        spare_origin=origin,
        spare_vector=vector,
        outer_d=od,
        inner_d=inner_d,
        shape=spec.shape,
        governing_y=governing.y_mm,
        utilisation=utilisation,
        x_over_chord=governing.x_c,
        length=length,
        feasible=feasible,
        infeasibility_reason=reason,
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
    # gh-1080: bore only for tube-shaped spars.  A rod reinforcement is solid
    # (inner_d=0); solving solve_dimension with shape="tube" then assigning the
    # hollow bore to a rod would produce a rod piece with inner_d > 0 — wrong.
    if spec.shape == "tube":
        sol = solve_dimension(shape="tube", erf_w=erf_w, outer_mm=root_od)
        inner_d = (
            float(sol["inner_mm"])
            if sol["feasible"] and sol["inner_mm"]
            else root_od * spec.wall_factor
        )
    else:
        inner_d = 0.0
    return SparPiece(
        role=SparRole.FRONT,
        spare_origin=origin,
        spare_vector=vector,
        outer_d=root_od,
        inner_d=inner_d,
        shape=spec.shape,
        governing_y=0.0,
        utilisation=1.0,
        x_over_chord=left[0].x_c,
        length=2.0 * reach,  # spans symmetrically across the root (y=-reach → +reach)
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
    plan.front_no_spar_from_y = _no_spar_from_y(front_right, plan.front_pieces)
    if _inboard_collinear(front_left, front_right):
        plan.front_joint = "continuous"
    else:
        plan.front_joint = "reinforcement+joiner"
        plan.reinforcement = _reinforcement_piece(front_left, front_right, front_spec)

    # --- rear ---
    if rear_left and rear_right:
        plan.rear_pieces = plan_spar(rear_right, rear_spec)
        plan.rear_no_spar_from_y = _no_spar_from_y(rear_right, plan.rear_pieces)
        if _straight_collinear_in_envelope(rear_left, rear_right):
            plan.rear_joint = "continuous"
        else:
            plan.rear_joint = "bent-pin"

    # --- feasibility roll-up (gh-1037 #3) ---
    all_pieces = [*plan.front_pieces, *plan.rear_pieces]
    if plan.reinforcement is not None:
        all_pieces.append(plan.reinforcement)
    infeasible = [p for p in all_pieces if not p.feasible]
    if infeasible:
        plan.feasible = False
        plan.infeasibility_reason = infeasible[0].infeasibility_reason

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
    control_surface_hinge_x_c: float | None = None,
) -> list[StationData]:
    """Sample a :class:`SectionGeometry` into solver-ready :class:`StationData`.

    For each of ``n_span`` stations root→tip: pick the spar chord location
    (``x_c`` if given, else the section's max-thickness location), read the
    contained band ``[bottom_z + clr, top_z - clr]`` (clr from ``packing_factor``)
    and ``center_z``, and compute the strength-required OD from #1008 sizing
    using the station's design moment ``M_design = |M| · g · j``.

    When ``x_c`` and ``control_surface_hinge_x_c`` are both given (the
    rear/torsion-spar path), the chordwise location is first pulled forward of
    the control surface via :func:`rear_spar_x_c_with_clearance` so a computed
    spar never overlaps the movable surface (gh-1059).
    """
    import numpy as np

    if x_c is not None and control_surface_hinge_x_c is not None:
        x_c = rear_spar_x_c_with_clearance(x_c, control_surface_hinge_x_c=control_surface_hinge_x_c)

    y_spans = np.linspace(0.0, 1.0, max(2, n_span)).tolist()
    # gh-1037 #4: the slice at y_span=0 is degenerate on a real loft (pinched,
    # zero-thickness centreline section) and would poison the governing
    # (max-moment) root station. Sample the root at y_span=eps instead so the
    # root sizing uses a valid section while still representing the highest
    # moment.
    if y_spans and y_spans[0] <= 0.0:
        y_spans[0] = _ROOT_EPS
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
