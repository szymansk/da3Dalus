"""Tests for mapping a SparPlan into cad_designer Spare objects (gh-1032).

Two tiers:

* **fast** — the pure data mapping (SparPiece → Spare, plan → list[Spare],
  warnings for telescoping / bent-pin / reinforcement metadata). These build
  hand-made ``SparPiece``/``SparPlan`` instances directly, so they run on the
  CI fast tier (no cadquery) and protect the new_coverage gate. The Spare class
  itself imports cadquery's ``Vector`` only lazily for origin/vector, which is
  available on the fast tier.
* **slow / requires_cadquery** — solve a real lofted wing, insert the plan into
  its WingConfiguration, and assert the constructed wing carries the spares.
"""

from __future__ import annotations

import pytest

from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.geometry.spar_cad_insertion import (
    SparInsertionResult,
    spar_piece_to_spare,
    spar_plan_to_spares,
)
from cad_designer.airplane.geometry.spar_solver import (
    SparPiece,
    SparPlan,
    SparRole,
)


def _piece(
    *,
    role: SparRole = SparRole.FRONT,
    origin: tuple[float, float, float] = (10.0, 0.0, 5.0),
    vector: tuple[float, float, float] = (0.0, 1.0, 0.0),
    outer_d: float = 12.0,
    inner_d: float = 8.0,
    length: float = 300.0,
    shape: str = "tube",
    joint_to_next: str | None = None,
) -> SparPiece:
    return SparPiece(
        role=role,
        spare_origin=origin,
        spare_vector=vector,
        outer_d=outer_d,
        inner_d=inner_d,
        shape=shape,
        governing_y=origin[1],
        utilisation=0.8,
        length=length,
        joint_to_next=joint_to_next,
    )


# ---------------------------------------------------------------------------
# spar_piece_to_spare — round tube/rod → Spare field mapping (mm + unit vector)
# ---------------------------------------------------------------------------


def test_piece_to_spare_maps_round_tube_to_equal_width_height():
    piece = _piece(outer_d=14.0)
    spare = spar_piece_to_spare(piece)

    assert isinstance(spare, Spare)
    # A round tube has a circular cross-section → width == height == outer_d (mm).
    assert spare.spare_support_dimension_width == pytest.approx(14.0)
    assert spare.spare_support_dimension_height == pytest.approx(14.0)


def test_piece_to_spare_maps_length_origin_and_unit_vector():
    piece = _piece(origin=(10.0, 0.0, 5.0), vector=(0.0, 1.0, 0.0), length=300.0)
    spare = spar_piece_to_spare(piece)

    # Length is carried in mm directly (gh-402: dimensional fields in mm).
    assert spare.spare_length == pytest.approx(300.0)
    # Origin is mm, mapped directly (the plan is already mm).
    assert tuple(spare.spare_origin.toTuple()) == pytest.approx((10.0, 0.0, 5.0))
    # Vector is a dimensionless unit direction — not scaled.
    assert tuple(spare.spare_vector.toTuple()) == pytest.approx((0.0, 1.0, 0.0))


def test_piece_to_spare_uses_normal_mode_to_preserve_explicit_geometry():
    # The plan already fixes origin + vector; we must NOT let WingConfiguration
    # recompute them from a position factor. "normal" is the explicit mode.
    spare = spar_piece_to_spare(_piece())
    assert spare.spare_mode == "normal"
    assert spare.spare_start == pytest.approx(0.0)


def test_piece_to_spare_normalises_non_unit_vector():
    piece = _piece(vector=(0.0, 3.0, 4.0))  # length 5, not unit
    spare = spar_piece_to_spare(piece)
    vx, vy, vz = spare.spare_vector.toTuple()
    assert (vx**2 + vy**2 + vz**2) == pytest.approx(1.0)
    assert (vx, vy, vz) == pytest.approx((0.0, 0.6, 0.8))


def test_piece_to_spare_rejects_zero_length_vector():
    piece = _piece(vector=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        spar_piece_to_spare(piece)


# ---------------------------------------------------------------------------
# spar_plan_to_spares — full plan → list[Spare] + warnings
# ---------------------------------------------------------------------------


def test_plan_to_spares_collects_front_and_rear_pieces():
    plan = SparPlan(
        front_pieces=[_piece(role=SparRole.FRONT), _piece(role=SparRole.FRONT)],
        rear_pieces=[_piece(role=SparRole.REAR)],
    )
    result = spar_plan_to_spares(plan)
    assert isinstance(result, SparInsertionResult)
    assert len(result.spares) == 3
    assert all(isinstance(s, Spare) for s in result.spares)


def test_plan_to_spares_empty_plan_yields_no_spares_no_warnings():
    result = spar_plan_to_spares(SparPlan())
    assert result.spares == []
    assert result.warnings == []


def test_plan_to_spares_skips_zero_od_phantom_piece():
    # gh-1045/#1057: a Ø0 piece is not a physical part — it must never become a
    # Spare on the BOM / CAD build, even if handed in directly.
    plan = SparPlan(
        front_pieces=[
            _piece(role=SparRole.FRONT, outer_d=14.0),
            _piece(role=SparRole.FRONT, outer_d=0.0, inner_d=0.0),
        ]
    )
    result = spar_plan_to_spares(plan)
    assert len(result.spares) == 1
    assert all(s.spare_support_dimension_width > 0.0 for s in result.spares)


def test_plan_to_spares_warns_on_telescoping_joint():
    plan = SparPlan(
        front_pieces=[
            _piece(joint_to_next="telescoping"),
            _piece(),
        ]
    )
    result = spar_plan_to_spares(plan)
    # Two pieces are still emitted (nothing dropped) ...
    assert len(result.spares) == 2
    # ... but the telescoping joint cannot be modelled as a single Spare → warn.
    assert any("telescop" in w.lower() for w in result.warnings)


def test_plan_to_spares_warns_on_reinforcement_joiner_and_emits_reinforcement():
    plan = SparPlan(
        front_pieces=[_piece()],
        front_joint="reinforcement+joiner",
        reinforcement=_piece(role=SparRole.FRONT, length=80.0),
    )
    result = spar_plan_to_spares(plan)
    # front piece + the reinforcement piece are both emitted (nothing dropped).
    assert len(result.spares) == 2
    assert any("reinforcement" in w.lower() for w in result.warnings)


def test_plan_to_spares_warns_when_reinforcement_joint_lacks_piece():
    plan = SparPlan(
        front_pieces=[_piece()],
        front_joint="reinforcement+joiner",
        reinforcement=None,
    )
    result = spar_plan_to_spares(plan)
    # No reinforcement piece to emit → only the front piece is a Spare.
    assert len(result.spares) == 1
    assert any("no reinforcement" in w.lower() for w in result.warnings)


def test_plan_to_spares_warns_on_bent_pin_rear_joint():
    plan = SparPlan(
        rear_pieces=[_piece(role=SparRole.REAR)],
        rear_joint="bent-pin",
    )
    result = spar_plan_to_spares(plan)
    assert len(result.spares) == 1
    assert any("bent-pin" in w.lower() for w in result.warnings)


def test_plan_to_spares_no_spurious_warning_for_continuous_joints():
    plan = SparPlan(
        front_pieces=[_piece()],
        rear_pieces=[_piece(role=SparRole.REAR)],
        front_joint="continuous",
        rear_joint="continuous",
    )
    result = spar_plan_to_spares(plan)
    assert result.warnings == []


# ---------------------------------------------------------------------------
# insert_spar_plan — fast: the pure list-merge into a segment's spare_list
# ---------------------------------------------------------------------------


def test_insert_spar_plan_appends_to_existing_spare_list():
    from cad_designer.airplane.geometry.spar_cad_insertion import insert_spar_plan

    existing = Spare(spare_support_dimension_width=5.0, spare_support_dimension_height=5.0)

    class _StubSegment:
        def __init__(self):
            self.spare_list = [existing]

    class _StubWing:
        def __init__(self):
            self.segments = [_StubSegment()]

    wing = _StubWing()
    plan = SparPlan(front_pieces=[_piece()])
    result = insert_spar_plan(wing, plan, segment_index=0)

    assert len(wing.segments[0].spare_list) == 2
    assert wing.segments[0].spare_list[0] is existing  # existing preserved
    assert result.spares[0] is wing.segments[0].spare_list[1]


def test_insert_spar_plan_initialises_none_spare_list():
    from cad_designer.airplane.geometry.spar_cad_insertion import insert_spar_plan

    class _StubSegment:
        def __init__(self):
            self.spare_list = None

    class _StubWing:
        def __init__(self):
            self.segments = [_StubSegment()]

    wing = _StubWing()
    plan = SparPlan(front_pieces=[_piece()], rear_pieces=[_piece(role=SparRole.REAR)])
    insert_spar_plan(wing, plan, segment_index=0)
    assert len(wing.segments[0].spare_list) == 2


def test_insert_spar_plan_rejects_out_of_range_segment():
    from cad_designer.airplane.geometry.spar_cad_insertion import insert_spar_plan

    class _StubWing:
        segments: list = []

    with pytest.raises(IndexError):
        insert_spar_plan(_StubWing(), SparPlan(front_pieces=[_piece()]), segment_index=0)


# ---------------------------------------------------------------------------
# slow / requires_cadquery — solve a real wing, insert, verify it carries spares
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_round_trip_solve_insert_and_carry_on_real_wing():
    from cad_designer.aerosandbox.wing_roundtrip_cases import single_segment_flat
    from cad_designer.airplane.geometry.section_geometry import SectionGeometry
    from cad_designer.airplane.geometry.spar_cad_insertion import insert_spar_plan
    from cad_designer.airplane.geometry.spar_solver import (
        build_stations_from_geometry,
        solve_spar_plan,
    )

    wing = single_segment_flat()

    geometry = SectionGeometry(wing)
    # Moderate moment so a single straight tube fits the thin section's band
    # → one continuous full-span piece (positive length).
    stations = build_stations_from_geometry(
        geometry,
        moment_fn=lambda y: 20.0 * (1.0 - y),
        sigma_allow_mpa=300.0,
        n_span=5,
    )
    plan = solve_spar_plan(front_left=stations, front_right=stations)
    assert plan.front_pieces, "solver produced no front pieces for the test wing"

    n_before = len(wing.segments[0].spare_list or [])
    result = insert_spar_plan(wing, plan, segment_index=0)

    assert len(wing.segments[0].spare_list) == n_before + len(result.spares)
    for spare in result.spares:
        assert spare in wing.segments[0].spare_list
        assert spare.spare_support_dimension_width > 0
        assert spare.spare_length is not None and spare.spare_length > 0
        # unit vector preserved
        vx, vy, vz = spare.spare_vector.toTuple()
        assert (vx**2 + vy**2 + vz**2) == pytest.approx(1.0, abs=1e-6)
