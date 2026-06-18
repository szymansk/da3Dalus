"""Map a :class:`SparPlan` into cad_designer ``Spare`` objects (gh-1032).

The spar-vector solver (#1030) produces a :class:`SparPlan` — front/rear lists
of straight :class:`SparPiece` tubes plus join metadata (telescoping across
consecutive pieces, reinforcement+joiner / bent-pin across the root). This
module turns that plan into ``Spare`` instances and inserts them into a
``WingConfiguration`` segment's ``spare_list`` via the existing topology path.

**Read-only topology.** We never modify the ``Spare`` / ``WingSegment`` /
``WingConfiguration`` classes — we only *construct* ``Spare`` instances and
append them to the existing ``spare_list``.

**Units (gh-402).** The plan is already in millimetres in the wing-local frame.
``Spare`` dimensional fields (``spare_support_dimension_width/height``,
``spare_length``, ``spare_start``, ``spare_origin``) are stored in **mm**, so
they map across directly with no scaling. ``spare_vector`` is a **dimensionless
unit direction** — we normalise (defensively) and never scale it.

**Tube/rod → Spare cross-section.** A ``SparPiece`` is a *round* tube/rod, so
its single ``outer_d`` maps to both of the ``Spare`` cross-section dimensions:
``spare_support_dimension_width == spare_support_dimension_height == outer_d``
(a square bounding box of a circle of that diameter). The bore (``inner_d``)
is not representable in the ``Spare`` topology, so it is preserved only as plan
metadata — a faithful-representation limitation surfaced as a warning, never a
silent drop. ``spare_mode`` is ``"normal"`` so the explicit, solved origin and
vector are honoured verbatim (WingConfiguration does not recompute them from a
position factor).

Faithfulness: each piece is emitted as one ``Spare``. Join semantics that a
single ``Spare`` cannot encode — telescoping overlaps, reinforcement+joiner,
bent-pin — are surfaced as warnings; pieces are NEVER dropped.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.geometry.spar_solver import SparPiece, SparPlan

_UNIT_TOL = 1e-9


@dataclass
class SparInsertionResult:
    """Spares produced from a plan plus any faithful-representation warnings."""

    spares: list[Spare] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def spar_piece_to_spare(piece: SparPiece) -> Spare:
    """Construct a single ``Spare`` from a round-tube/rod :class:`SparPiece`.

    Maps the piece's millimetre geometry onto the ``Spare`` fields and uses the
    ``"normal"`` spare mode so the solved (origin, vector) are taken verbatim.
    Raises ``ValueError`` for a zero-length direction vector (un-orientable).
    """
    vector = _unit(piece.spare_vector)
    return Spare(
        # Round cross-section → equal width/height (mm).
        spare_support_dimension_width=float(piece.outer_d),
        spare_support_dimension_height=float(piece.outer_d),
        spare_length=float(piece.length),
        spare_start=0.0,
        spare_origin=tuple(float(c) for c in piece.spare_origin),
        spare_vector=vector,
        # "normal" → WingConfiguration keeps our explicit origin/vector as-is.
        spare_mode="normal",
    )


def spar_plan_to_spares(plan: SparPlan) -> SparInsertionResult:
    """Turn a whole :class:`SparPlan` into ``Spare`` objects + warnings.

    Every front piece, rear piece and (if present) the root reinforcement is
    emitted as one ``Spare``. Joints that a single ``Spare`` cannot encode are
    surfaced as warnings; nothing is silently dropped.
    """
    result = SparInsertionResult()

    _emit_pieces(plan.front_pieces, "front", result)
    _emit_pieces(plan.rear_pieces, "rear", result)

    if plan.front_joint == "reinforcement+joiner":
        if plan.reinforcement is not None:
            result.spares.append(spar_piece_to_spare(plan.reinforcement))
            result.warnings.append(
                "Front spar uses a reinforcement+joiner across the root: the "
                "reinforcement is emitted as a separate Spare; the joiner "
                "fit/overlap is plan metadata and is not modelled as a Spare."
            )
        else:
            result.warnings.append(
                "Front spar marked 'reinforcement+joiner' but no reinforcement "
                "piece was provided by the plan."
            )

    if plan.rear_joint == "bent-pin":
        result.warnings.append(
            "Rear spar uses a bent-pin root joint: each straight piece is "
            "emitted as a Spare, but the bent-pin kink across the root is not "
            "representable as a single straight Spare."
        )

    return result


def insert_spar_plan(
    wing_config,
    plan: SparPlan,
    *,
    segment_index: int = 0,
) -> SparInsertionResult:
    """Insert a :class:`SparPlan` into a ``WingConfiguration`` segment.

    Constructs ``Spare`` instances from ``plan`` and appends them to the target
    segment's ``spare_list`` (existing topology path), preserving any spares
    already present. Returns the produced spares and warnings.

    Raises ``IndexError`` if ``segment_index`` is out of range.
    """
    segments = wing_config.segments
    if segment_index < 0 or segment_index >= len(segments):
        raise IndexError(
            f"segment_index {segment_index} out of range (wing has {len(segments)} segment(s))"
        )

    result = spar_plan_to_spares(plan)

    segment = segments[segment_index]
    if segment.spare_list is None:
        segment.spare_list = []
    segment.spare_list.extend(result.spares)

    return result


def _emit_pieces(pieces: list[SparPiece], role_label: str, result: SparInsertionResult) -> None:
    """Append one Spare per piece; warn (once) if the run is telescoping.

    gh-1045/#1057: skip any degenerate Ø0 piece — a zero-diameter tube is not a
    physical structural object, so it must never reach the BOM / CAD build as a
    phantom zero-size Spare. The solver already drops Ø0 pieces; this guard keeps
    the insertion step safe for any caller that hands one in directly.
    """
    telescoping = False
    for piece in pieces:
        if piece.outer_d <= 0.0:
            continue
        result.spares.append(spar_piece_to_spare(piece))
        if piece.joint_to_next == "telescoping":
            telescoping = True
    if telescoping:
        result.warnings.append(
            f"{role_label.capitalize()} spar is telescoping (multi-piece): each "
            "piece is emitted as its own Spare, but the telescoping overlap "
            "(OD_outer <= ID_inner - clearance) is plan metadata and is not "
            "modelled as a Spare."
        )


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    """Normalise a direction vector to unit length; reject the zero vector."""
    x, y, z = (float(vector[0]), float(vector[1]), float(vector[2]))
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < _UNIT_TOL:
        raise ValueError("spar piece has a zero-length direction vector; cannot orient a Spare")
    return (x / norm, y / norm, z / norm)
