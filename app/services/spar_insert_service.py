"""Service for the spar-plan → wing insert endpoint (gh-1049).

Compute a buildable :class:`~cad_designer.airplane.geometry.spar_solver.SparPlan`
(reusing :func:`app.services.spar_plan_service.compute_spar_plan_object`), map
each piece to a persisted ``Spare`` (reusing
:func:`cad_designer.airplane.geometry.spar_cad_insertion.spar_piece_to_spare`),
resolve each piece's target wing segment from its spanwise span, assign the
per-segment ``sort_index`` per the **HARD INVARIANT**, and either preview
(``dry_run=true``) or persist (``dry_run=false``) the result.

HARD INVARIANT (cad_designer construction relies on it — verified against
:class:`cad_designer.airplane.creator.wing.VaseModeWingCreator.VaseModeWingCreator`):
``spare_list[0]`` is the **main spar**; it is the only spar that receives the
vase-mode print slot and is built first. Therefore the **front (bending) spar
MUST be ``spar_index = 0`` in every segment it occupies**, the **rear spar = 1**,
and the **reinforcement = the next index (2)**. The same logical spar carries the
same ``spar_index`` in every segment it passes through; telescoping pieces keep
that spar's index within their segment.

**Already-has-index-0 behaviour (REPLACE).** Inserting a fresh spar plan
*replaces* every spare in each segment the plan writes to: each target segment is
cleared first, then the plan's spares are appended in invariant order. This makes
the front spar deterministically land at ``sort_index = 0`` and never silently
corrupts an existing index-0 spar by shifting it to a non-zero slot.

Units: the plan is solved in mm; the dry-run response exposes piece dimensions in
**metres** (project convention). On commit, the metre values are handed to
``wing_service.create_spare`` which converts back to mm for DB storage (gh-402).
``spare_vector`` is a dimensionless unit direction and is never scaled.
"""

from __future__ import annotations

import logging

from app import schemas
from app.core.exceptions import ValidationError
from app.schemas.spar_insert import (
    PlannedSpareOut,
    SparInsertRequest,
    SparInsertResponse,
)
from app.services import aeroplane_version_service
from app.services.spar_plan_service import _resolve_wing, compute_spar_plan_object
from app.services.wing_service import create_spare, get_aeroplane_or_raise
from cad_designer.airplane.geometry.spar_cad_insertion import (
    spar_piece_to_spare,
    spar_plan_to_spares,
)

logger = logging.getLogger(__name__)

_MM_TO_M = 0.001
_FRACTION_TOL = 1e-6

#: Version-label for the auto-snapshot taken before a destructive spar insert
#: commit (gh-1058). The commit REPLACEs existing spares in each touched
#: segment, so the head is frozen first to enable a one-click revert.
_AUTOSNAPSHOT_LABEL = "Before spar insert"

#: Per-invariant spar_index assignment by structural role / piece kind.
_FRONT_INDEX = 0
_REAR_INDEX = 1
_REINFORCEMENT_INDEX = 2


class _PlannedPiece:
    """A solved SparPiece paired with its assigned (segment_index, spar_index)."""

    __slots__ = ("piece", "spare", "segment_index", "spar_index")

    def __init__(self, piece, spare, segment_index: int, spar_index: int):
        self.piece = piece
        self.spare = spare
        self.segment_index = segment_index
        self.spar_index = spar_index


def _segment_lengths_mm(wing) -> list[float]:
    """Return the wing's per-segment spanwise lengths (mm).

    Builds the millimetre ``WingConfiguration`` and reads each segment's
    ``length``. Kept as a seam so fast tests can stub the cadquery/converter
    boundary.
    """
    from app.converters.model_schema_converters import wing_model_to_wing_config

    wing_config = wing_model_to_wing_config(wing, scale=1000.0)
    return [float(seg.length) for seg in (wing_config.segments or [])]


def _segment_for_y(y_mm: float, segment_lengths_mm: list[float]) -> int:
    """Resolve a spanwise position (mm, may be the piece root or governing_y) to
    a segment index via accumulated segment lengths.

    Segment ``i`` spans ``[sum(lengths[:i]), sum(lengths[:i+1]))``. A position at
    or beyond the last boundary clamps to the last segment; a negative (mirror)
    position clamps to the root segment 0.
    """
    if not segment_lengths_mm:
        return 0
    y = abs(float(y_mm))
    upper = 0.0
    for idx, length in enumerate(segment_lengths_mm):
        upper += length
        if y < upper:
            return idx
    return len(segment_lengths_mm) - 1


def _spar_index_for(piece, *, is_reinforcement: bool) -> int:
    """Assign the per-segment sort_index per the HARD INVARIANT."""
    from cad_designer.airplane.geometry.spar_solver import SparRole

    if is_reinforcement:
        return _REINFORCEMENT_INDEX
    if piece.role == SparRole.REAR:
        return _REAR_INDEX
    return _FRONT_INDEX


def _piece_locate_y(piece) -> float:
    """The spanwise position used to place a piece into a segment.

    Prefer the piece root origin's y (where the straight piece starts); fall back
    to ``governing_y``. Both are mm in the wing-local frame.
    """
    origin = getattr(piece, "spare_origin", None)
    if origin is not None and len(origin) >= 2:
        return float(origin[1])
    return float(piece.governing_y)


def _spare_to_metre_schema(piece, spare) -> schemas.SpareDetailSchema:
    """Build a metre ``SpareDetailSchema`` from a mm SparPiece + its mapped Spare.

    The mapped ``Spare`` is in mm; convert dimensional fields to metres so the
    value matches the API convention consumed by ``create_spare`` (which then
    converts back to mm for the DB).
    """
    return schemas.SpareDetailSchema(
        spare_support_dimension_width=spare.spare_support_dimension_width * _MM_TO_M,
        spare_support_dimension_height=spare.spare_support_dimension_height * _MM_TO_M,
        spare_length=(spare.spare_length * _MM_TO_M if spare.spare_length is not None else None),
        spare_start=spare.spare_start * _MM_TO_M,
        spare_mode=spare.spare_mode,
        spare_vector=list(spare.spare_vector) if spare.spare_vector is not None else None,
        spare_origin=(
            [c * _MM_TO_M for c in spare.spare_origin] if spare.spare_origin is not None else None
        ),
        spare_position_factor=None,
    )


def _planned_to_out(planned: _PlannedPiece) -> PlannedSpareOut:
    """Build the metre dry-run/commit response item from a planned piece."""
    piece = planned.piece
    spare = planned.spare
    return PlannedSpareOut(
        segment_index=planned.segment_index,
        spar_index=planned.spar_index,
        role=piece.role.value,
        spare_support_dimension_width=spare.spare_support_dimension_width * _MM_TO_M,
        spare_support_dimension_height=spare.spare_support_dimension_height * _MM_TO_M,
        spare_length=(spare.spare_length or 0.0) * _MM_TO_M,
        outer_d=piece.outer_d * _MM_TO_M,
        inner_d=piece.inner_d * _MM_TO_M,
        spare_origin=[c * _MM_TO_M for c in spare.spare_origin],
        spare_vector=list(spare.spare_vector),
        joint_note=piece.joint_to_next,
        feasible=piece.feasible,
    )


def _plan_pieces_in_invariant_order(plan):
    """Yield ``(piece, is_reinforcement)`` in the order spares get appended.

    Order matters: within each segment the FRONT spar must be appended FIRST so
    it lands at ``sort_index = 0`` (the main spar slot). We emit all front
    pieces, then all rear pieces, then the reinforcement.
    """
    for piece in plan.front_pieces:
        yield piece, False
    for piece in plan.rear_pieces:
        yield piece, False
    if plan.reinforcement is not None:
        yield plan.reinforcement, True


def _build_planned_pieces(plan, segment_lengths_mm: list[float]) -> list[_PlannedPiece]:
    """Map every plan piece to a ``Spare``, resolve its segment, assign its index.

    The mapping reuses :func:`spar_plan_to_spares` so warnings (telescoping,
    bent-pin, reinforcement+joiner, dropped bore) stay faithful. We rebuild the
    Spare list in invariant order and pair each Spare with its source piece.
    """
    # NOTE (gh-1053 adjacent / owned by gh-1045): the solver can emit a Ø0
    # terminal tip piece (outer_d == 0) at the zero-moment tip. That phantom
    # zero-size Spare is tracked and fixed in gh-1045 ("spar solver emits a Ø0
    # terminal tip piece"); it is deliberately NOT suppressed here to avoid two
    # competing fixes for the same defect.
    mapping = spar_plan_to_spares(plan)
    spares = list(mapping.spares)
    ordered = list(_plan_pieces_in_invariant_order(plan))
    if len(spares) != len(ordered):  # pragma: no cover - defensive: mapping mirrors order
        raise ValidationError(
            message="Spar plan mapping produced an unexpected number of spares.",
        )

    planned: list[_PlannedPiece] = []
    for (piece, is_reinforcement), spare in zip(ordered, spares, strict=True):
        segment_index = _segment_for_y(_piece_locate_y(piece), segment_lengths_mm)
        spar_index = _spar_index_for(piece, is_reinforcement=is_reinforcement)
        planned.append(_PlannedPiece(piece, spare, segment_index, spar_index))
    return planned


def _clear_plan_spares(db, wing, segment_index: int) -> None:
    """Remove all existing spares from a segment's cross-section detail (REPLACE).

    Inserting a fresh plan replaces existing spares in each target segment so the
    front spar deterministically lands at sort_index 0 and existing indices are
    never silently corrupted.
    """
    x_secs = wing.x_secs
    if segment_index < 0 or segment_index >= len(x_secs):  # pragma: no cover - guarded upstream
        return
    detail = x_secs[segment_index].detail
    if detail is None:
        return
    for spare in list(detail.spares):
        db.delete(spare)
    detail.spares.clear()
    db.flush()


def _persist_spares(db, aeroplane_uuid, wing, planned: list[_PlannedPiece]) -> None:
    """Persist the planned spares, honouring the spar_index as sort_index.

    Clears each target segment once (REPLACE), then appends the planned spares in
    invariant order so ``create_spare``'s ``sort_index = len(spares)`` yields the
    intended index (front first → 0, rear → 1, reinforcement → 2).
    """
    for segment_index in sorted({p.segment_index for p in planned}):
        _clear_plan_spares(db, wing, segment_index)

    for planned_piece in sorted(planned, key=lambda p: (p.segment_index, p.spar_index)):
        spare_data = _spare_to_metre_schema(planned_piece.piece, planned_piece.spare)
        create_spare(
            db,
            aeroplane_uuid,
            wing.name,
            planned_piece.segment_index,
            spare_data,
        )


# ---------------------------------------------------------------------------
# gh-1063: main-spar segment split persistence (front spar telescopes).
#
# When the solved FRONT (main) spar is multi-piece (telescopes), each diameter
# needs its own segment with the main piece at spar_index 0 (the VaseMode
# invariant). We split the host segment at each joint y, place each main piece in
# its sub-segment, carry the children (control surface duplicated, turbulator
# carried, existing spares re-homed) via the gh-1064 split helper, and persist by
# rebuilding the wing's cross-section rows from the post-split WingConfiguration.
# Secondary spars (rear/reinforcement) stay in the host segment as Option-B
# partial-span spares (no split) and are written by the existing spare path.
# ---------------------------------------------------------------------------


def _real_front_pieces(plan) -> list:
    """Front pieces that actually become a Spare (drop sub-buildable tips).

    The solver already drops sub-floor terminal tip pieces (gh-1045/#1076); a
    tube below the buildable floor is not a physical structural object and never
    reaches the build, so it must not count toward telescoping detection or
    create a phantom split. This guard mirrors the solver's floor so a plan that
    reaches this path without going through ``plan_spar`` (e.g. deserialized)
    stays coherent with it.
    """
    from cad_designer.airplane.geometry.spar_solver import NEGLIGIBLE_OD_FLOOR_MM

    return [p for p in plan.front_pieces if p.outer_d >= NEGLIGIBLE_OD_FLOOR_MM]


def _front_telescopes(plan) -> bool:
    """True when the front (main) spar is multi-piece → a segment split is needed."""
    return len(_real_front_pieces(plan)) > 1


def _front_split_plan(plan, segment_lengths_mm: list[float]) -> tuple[int, list[float]]:
    """Resolve the host segment + the segment-local joint lengths (mm) for the
    telescoping front spar.

    All front pieces of one telescoping spar run continuously root→tip inside a
    single host segment; the host is resolved from the first front piece's root
    y. Each subsequent piece's root y is a joint — converted to a segment-local
    length (joint_y - host_root_y), clamped strictly inside the segment.
    """
    pieces = _real_front_pieces(plan)
    host_index = _segment_for_y(_piece_locate_y(pieces[0]), segment_lengths_mm)
    host_root_y = float(sum(segment_lengths_mm[:host_index]))
    host_len = float(segment_lengths_mm[host_index]) if segment_lengths_mm else 0.0

    split_lengths: list[float] = []
    for piece in pieces[1:]:
        local = float(_piece_locate_y(piece)) - host_root_y
        # Keep strictly inside the host segment so the split helper accepts it.
        if _FRACTION_TOL * host_len < local < host_len - _FRACTION_TOL * host_len:
            split_lengths.append(local)
    return host_index, split_lengths


def _main_pieces_per_subsegment(plan) -> list[list]:
    """One front-spar Spare per sub-segment, in root→tip order (index-0 invariant).

    The split produces ``len(real_front_pieces)`` sub-segments; the i-th
    sub-segment gets the i-th front piece as its sole main spar at ``spar_list[0]``.
    """
    return [[spar_piece_to_spare(piece)] for piece in _real_front_pieces(plan)]


def _apply_front_split_to_config(wing_config, host_index: int, split_lengths: list[float], plan):
    """Return a new WingConfiguration with the host segment split (gh-1064 helper).

    Reuses ``split_segment_at_lengths`` so the loft is geometrically unchanged;
    injects ``morph_airfoils`` so differing-airfoil hosts get a real morphed
    boundary, and places each front piece at ``spar_list[0]`` of its sub-segment.
    """
    from app.converters.openvsp_airfoil import morph_airfoils
    from cad_designer.airplane.geometry.segment_split import split_segment_at_lengths

    return split_segment_at_lengths(
        wing_config,
        host_index,
        split_lengths,
        airfoil_morph_fn=morph_airfoils,
        main_pieces_per_subsegment=_main_pieces_per_subsegment(plan),
    )


def _wing_to_config_mm(wing):
    """Build the wing's millimetre WingConfiguration (seam for fast tests)."""
    from app.converters.model_schema_converters import wing_model_to_wing_config

    return wing_model_to_wing_config(wing, scale=1000.0)


def _persist_wing_config(db, aeroplane_uuid, wing, new_wing_config) -> None:
    """Materialise the post-split WingConfiguration into the wing's DB rows.

    Rebuilds the wing's cross-section rows from ``new_wing_config`` via the
    round-trip converter: this inserts the new ``WingXSecModel`` rows at the
    split boundaries, re-indexes ``sort_index`` contiguously, and transfers each
    sub-segment's detail (duplicated control surface, carried turbulator,
    re-homed + main-piece spares). Replaces the wing's ``x_secs`` in place so the
    wing identity (and component-tree group) is preserved. All within the caller's
    transaction (get_db commits/rolls back).
    """
    from app.converters.model_schema_converters import wing_config_to_wing_model
    from app.services.wing_service import _recompute_spare_vectors

    rebuilt = wing_config_to_wing_model(
        wing_config=new_wing_config,
        wing_name=wing.name,
        scale=_MM_TO_M,
    )
    # Detach the rebuilt cross-sections from their transient parent so they have
    # exactly one owner. Reassigning ``wing.x_secs`` wholesale lets the
    # ``all, delete-orphan`` cascade delete the wing's previous ribs and adopt
    # the rebuilt ones in a single step — inserting the new split boundary rows,
    # keeping contiguous sort_index (0..N), and carrying each sub-segment's
    # transferred detail (duplicated control surface, carried turbulator,
    # re-homed + main-piece spares). The wing identity (and its component-tree
    # group) is preserved.
    new_xsecs = list(rebuilt.x_secs)
    rebuilt.x_secs = []
    wing.x_secs = new_xsecs
    db.flush()
    _recompute_spare_vectors(wing)


def _persist_front_split(db, aeroplane_uuid, wing, plan, segment_lengths_mm: list[float]):
    """Persist a telescoping front spar as a materialised segment split.

    Returns the planned per-sub-segment lengths (m) for the split host segment.
    Secondary (rear/reinforcement) spares are appended to the FIRST sub-segment
    as Option-B partial-span spares after the split.
    """
    host_index, split_lengths = _front_split_plan(plan, segment_lengths_mm)
    if not split_lengths:
        # Defensive: telescoping detected but every joint clamped out of range —
        # fall back to the spare-only path rather than emit a no-op split.
        _persist_spares(db, aeroplane_uuid, wing, _build_planned_pieces(plan, segment_lengths_mm))
        return None

    wing_config = _wing_to_config_mm(wing)
    new_wing_config = _apply_front_split_to_config(wing_config, host_index, split_lengths, plan)
    _add_secondary_spares_to_first_subsegment(new_wing_config, host_index, plan)
    _persist_wing_config(db, aeroplane_uuid, wing, new_wing_config)

    sub_lengths_mm = [
        float(new_wing_config.segments[host_index + i].length)
        for i in range(len(split_lengths) + 1)
    ]
    return [length * _MM_TO_M for length in sub_lengths_mm]


def _add_secondary_spares_to_first_subsegment(new_wing_config, host_index: int, plan) -> None:
    """Append rear/reinforcement spares as Option-B partial-span spares (no split).

    Secondary spars stay in the host segment (now the FIRST sub-segment) with
    ``spare_start``/``spare_length`` set so they span the joint(s) without
    forcing another split. They follow the index-0 main piece (rear root = 1,
    reinforcement = next).
    """
    from cad_designer.airplane.geometry.spar_cad_insertion import secondary_spare_option_b

    first_sub = new_wing_config.segments[host_index]
    segment_root_y = float(_subsegment_root_y(new_wing_config, host_index))
    secondaries = list(plan.rear_pieces)
    if plan.reinforcement is not None:
        secondaries.append(plan.reinforcement)
    if not secondaries:
        return
    if first_sub.spare_list is None:
        first_sub.spare_list = []
    for piece in secondaries:
        if piece.outer_d <= 0.0:
            continue
        first_sub.spare_list.append(secondary_spare_option_b(piece, segment_root_y=segment_root_y))


def _subsegment_root_y(wing_config, segment_index: int) -> float:
    """Spanwise root y (mm) of a segment = sum of preceding segment lengths."""
    return sum(float(seg.length) for seg in wing_config.segments[:segment_index])


def insert_spar_plan(
    db,
    aeroplane_uuid,
    request: SparInsertRequest,
) -> SparInsertResponse:
    """Compute a spar plan and insert it into the wing (dry-run or commit).

    On commit (``dry_run=false``) the wing is mutated destructively — existing
    spares in every touched segment are REPLACEd. Before any mutation the head is
    frozen as an immutable snapshot (gh-1058) so the user can one-click revert;
    the snapshot id is returned in the response. A dry-run takes no snapshot.

    Raises:
        NotFoundError: aeroplane or wing does not exist (-> 404).
        ValidationError: section geometry unavailable, material/strength inputs
            invalid, or the plan is infeasible (-> 422).
    """
    aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
    wing = _resolve_wing(aeroplane, request)

    plan = compute_spar_plan_object(db, aeroplane_uuid, request, wing=wing)

    if not plan.feasible:
        raise ValidationError(
            message=(
                "Spar plan is infeasible and cannot be inserted: "
                f"{plan.infeasibility_reason or 'no buildable round tube fits the section.'}"
            ),
            details={"infeasibility_reason": plan.infeasibility_reason},
        )

    segment_lengths_mm = _segment_lengths_mm(wing)
    planned = _build_planned_pieces(plan, segment_lengths_mm)

    # gh-1063: a telescoping front spar materialises a SEGMENT SPLIT (new
    # cross-section rows) rather than writing multiple index-0 spares into one
    # segment; a single-piece front spar takes the existing spare-only path.
    splits = _front_telescopes(plan)
    planned_segment_lengths: list[float] | None = None
    if splits:
        host_index, split_lengths = _front_split_plan(plan, segment_lengths_mm)
        planned_segment_lengths = _preview_subsegment_lengths_m(
            segment_lengths_mm, host_index, split_lengths
        )

    committed = False
    snapshot_id: int | None = None
    if not request.dry_run:
        # gh-1058: a commit mutates structure destructively (segment split, or a
        # REPLACE of existing spares). Freeze the current head as an immutable
        # snapshot BEFORE mutating anything so the user can one-click revert. If
        # snapshotting fails we abort the whole commit (never mutate without a
        # recovery point); the exception propagates and get_db() rolls back.
        snapshot_node = aeroplane_version_service.snapshot(
            db,
            aeroplane.id,
            _AUTOSNAPSHOT_LABEL,
        )
        snapshot_id = snapshot_node.id
        if splits:
            persisted_lengths = _persist_front_split(
                db, aeroplane_uuid, wing, plan, segment_lengths_mm
            )
            if persisted_lengths is not None:
                planned_segment_lengths = persisted_lengths
        else:
            _persist_spares(db, aeroplane_uuid, wing, planned)
        committed = True

    mapping = spar_plan_to_spares(plan)
    return SparInsertResponse(
        dry_run=request.dry_run,
        committed=committed,
        wing_name=wing.name,
        planned_spares=[_planned_to_out(p) for p in planned],
        warnings=mapping.warnings,
        feasible=plan.feasible,
        infeasibility_reason=plan.infeasibility_reason,
        snapshot_id=snapshot_id,
        planned_segment_lengths=planned_segment_lengths,
    )


def _preview_subsegment_lengths_m(
    segment_lengths_mm: list[float], host_index: int, split_lengths: list[float]
) -> list[float] | None:
    """Planned per-sub-segment lengths (m) for a previewed split (no DB write)."""
    if not split_lengths:
        return None
    host_len = float(segment_lengths_mm[host_index])
    boundaries = [0.0, *split_lengths, host_len]
    return [(boundaries[i + 1] - boundaries[i]) * _MM_TO_M for i in range(len(boundaries) - 1)]
