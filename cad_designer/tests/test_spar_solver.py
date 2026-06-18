"""Tests for the spar-vector solver core (gh-1030).

Two tiers:

* **fast** — the pure decision logic (greedy straight-piece fit, telescoping
  split on strength/containment failure, the strength-beats-part-count priority
  rule, root-collinearity yes/no, bent-pin trigger via geometry). These drive
  every branch by feeding hand-built ``StationData`` directly, so they run on
  the CI fast tier (no cadquery) and protect the new_coverage gate.
* **slow / requires_cadquery** — run the solver end-to-end on a real lofted wing
  (taper + twist + dihedral) and assert plausible plans.
"""

from __future__ import annotations

import pytest

from cad_designer.airplane.geometry.spar_solver import (
    SparPiece,
    SparPlan,
    SparRole,
    SparSpec,
    StationData,
    _inboard_collinear,
    _straight_collinear_in_envelope,
    plan_spar,
    solve_spar_plan,
)


# ---------------------------------------------------------------------------
# Helpers — build StationData without any CAD
# ---------------------------------------------------------------------------


def _station(
    y_span: float,
    *,
    y_mm: float,
    center_z: float = 0.0,
    band: tuple[float, float] = (-50.0, 50.0),
    required_od: float = 10.0,
    x_c: float = 0.4,
) -> StationData:
    """A single station with explicit containment band + required strength OD."""
    return StationData(
        y_span=y_span,
        y_mm=y_mm,
        x_c=x_c,
        center_z=center_z,
        band_lo=band[0],
        band_hi=band[1],
        required_od=required_od,
    )


def _uniform_stations(n: int = 5, *, required_od: float = 10.0) -> list[StationData]:
    """A straight, generously-thick wing: every station easily contains the OD."""
    return [
        _station(i / (n - 1), y_mm=i * 100.0, band=(-50.0, 50.0), required_od=required_od)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Fast: greedy straight-piece fit
# ---------------------------------------------------------------------------


class TestContinuousFit:
    def test_uniform_wing_is_one_continuous_piece(self):
        spec = SparSpec(role=SparRole.FRONT)
        pieces = plan_spar(_uniform_stations(), spec)
        assert len(pieces) == 1
        assert pieces[0].governing_y == pytest.approx(0.0)
        # round tube by default
        assert pieces[0].shape == "tube"
        assert pieces[0].outer_d == pytest.approx(10.0)

    def test_governing_od_is_the_most_inboard_station(self):
        # required OD decreases outboard (root carries the highest moment)
        stations = [
            _station(0.0, y_mm=0.0, required_od=20.0),
            _station(0.5, y_mm=250.0, required_od=12.0),
            _station(1.0, y_mm=500.0, required_od=8.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) == 1
        assert pieces[0].outer_d == pytest.approx(20.0)

    def test_origin_and_vector_follow_first_to_last_center(self):
        stations = [
            _station(0.0, y_mm=0.0, center_z=0.0),
            _station(1.0, y_mm=400.0, center_z=0.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        p = pieces[0]
        assert p.spare_origin[1] == pytest.approx(0.0)
        # unit span vector along +y
        assert p.spare_vector[1] == pytest.approx(1.0)
        assert sum(c * c for c in p.spare_vector) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Fast: telescoping split (strength beats part-count)
# ---------------------------------------------------------------------------


class TestTelescopingSplit:
    def test_thin_tip_forces_split_on_containment(self):
        # root band is deep, tip band collapses below the required OD -> a single
        # straight tube of the root OD would poke through the tip skin.
        stations = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=30.0),
            _station(0.5, y_mm=250.0, band=(-25.0, 25.0), required_od=20.0),
            _station(1.0, y_mm=500.0, band=(-6.0, 6.0), required_od=8.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) >= 2
        # telescoping: the tip-side (outer) piece must slide INTO the root-side
        # (inner) piece's bore — OD_outer <= ID_inner (gh-1037: the old
        # equal-OD/ID convention let a fat tip into a narrow bore).
        inner, outer = pieces[0], pieces[1]
        assert inner.joint_to_next == "telescoping"
        assert outer.outer_d <= inner.inner_d + 1e-9
        # strength beats part-count: each piece's OD still meets its governing station
        assert inner.outer_d >= 30.0 - 1e-9

    def test_strength_required_od_exceeds_band_triggers_split(self):
        # strength wants a fat OD at the root that the outboard thin section can't
        # contain even though the band alone (for a thinner tube) would be fine.
        stations = [
            _station(0.0, y_mm=0.0, band=(-40.0, 40.0), required_od=40.0),
            _station(1.0, y_mm=500.0, band=(-15.0, 15.0), required_od=12.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) >= 2
        assert pieces[0].joint_to_next == "telescoping"

    def test_utilisation_recorded_per_piece(self):
        pieces = plan_spar(_uniform_stations(), SparSpec(role=SparRole.FRONT))
        for p in pieces:
            assert 0.0 < p.utilisation <= 1.0


# ---------------------------------------------------------------------------
# Fast: root collinearity / reinforcement (front)
# ---------------------------------------------------------------------------


class TestRootCollinearity:
    def test_flat_root_is_single_carry_through(self):
        left = _uniform_stations()
        right = _uniform_stations()
        plan = solve_spar_plan(front_left=left, front_right=right)
        assert plan.front_joint == "continuous"
        assert plan.reinforcement is None

    def test_offset_root_centres_force_reinforcement(self):
        # left and right inboard centres at very different z -> not collinear
        left = [
            _station(0.0, y_mm=0.0, center_z=0.0),
            _station(1.0, y_mm=500.0, center_z=0.0),
        ]
        right = [
            _station(0.0, y_mm=0.0, center_z=40.0),
            _station(1.0, y_mm=500.0, center_z=80.0),
        ]
        plan = solve_spar_plan(front_left=left, front_right=right)
        assert plan.front_joint == "reinforcement+joiner"
        assert plan.reinforcement is not None
        # reinforcement sits at the max-moment (root) station, collinear through y=0
        assert plan.reinforcement.governing_y == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Fast: rear spar bent-pin trigger (geometry-derived, not a fixed angle)
# ---------------------------------------------------------------------------


class TestRearBentPin:
    def test_straight_collinear_rear_stays_in_envelope(self):
        right = [
            _station(0.0, y_mm=0.0, center_z=0.0, band=(-30.0, 30.0)),
            _station(1.0, y_mm=500.0, center_z=0.0, band=(-30.0, 30.0)),
        ]
        left = [
            _station(0.0, y_mm=0.0, center_z=0.0, band=(-30.0, 30.0)),
            _station(1.0, y_mm=-500.0, center_z=0.0, band=(-30.0, 30.0)),
        ]
        plan = solve_spar_plan(
            front_left=right, front_right=right, rear_left=left, rear_right=right
        )
        assert plan.rear_joint == "continuous"

    def test_strong_dihedral_rear_triggers_bent_pin(self):
        # both halves rise steeply -> a straight collinear rod through y=0 would
        # leave the [bottom_z, top_z] band at the wing-root stations.
        right = [
            _station(0.0, y_mm=0.0, center_z=0.0, band=(-10.0, 10.0)),
            _station(1.0, y_mm=500.0, center_z=200.0, band=(190.0, 210.0)),
        ]
        left = [
            _station(0.0, y_mm=0.0, center_z=0.0, band=(-10.0, 10.0)),
            _station(1.0, y_mm=-500.0, center_z=200.0, band=(190.0, 210.0)),
        ]
        plan = solve_spar_plan(
            front_left=right, front_right=right, rear_left=left, rear_right=right
        )
        assert plan.rear_joint == "bent-pin"
        assert plan.rear_pieces  # still emits the per-half pieces


# ---------------------------------------------------------------------------
# Fast: serialisability
# ---------------------------------------------------------------------------


class TestSerialisation:
    def test_plan_is_serialisable_dict(self):
        plan = solve_spar_plan(front_left=_uniform_stations(), front_right=_uniform_stations())
        assert isinstance(plan, SparPlan)
        assert all(isinstance(p, SparPiece) for p in plan.front_pieces)
        d = plan.to_dict()
        assert isinstance(d, dict)
        assert "front_pieces" in d
        assert "front_joint" in d
        piece = d["front_pieces"][0]
        assert set(piece) >= {
            "spare_origin",
            "spare_vector",
            "outer_d",
            "inner_d",
            "shape",
            "governing_y",
            "utilisation",
            "role",
        }


# ---------------------------------------------------------------------------
# Fast: degenerate / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_stations_yields_no_pieces(self):
        assert plan_spar([], SparSpec(role=SparRole.FRONT)) == []

    def test_single_station_yields_one_piece(self):
        pieces = plan_spar([_station(0.0, y_mm=0.0)], SparSpec(role=SparRole.FRONT))
        assert len(pieces) == 1

    def test_collinear_helpers_reject_empty_half(self):
        assert _inboard_collinear([], [_station(0.0, y_mm=0.0)]) is False
        assert _inboard_collinear([_station(0.0, y_mm=0.0)], []) is False
        assert _straight_collinear_in_envelope([], [_station(0.0, y_mm=0.0)]) is False
        assert _straight_collinear_in_envelope([_station(0.0, y_mm=0.0)], []) is False

    def test_plan_without_rear_stations_skips_rear(self):
        plan = solve_spar_plan(front_left=_uniform_stations(), front_right=_uniform_stations())
        assert plan.rear_pieces == []
        assert plan.rear_joint == "continuous"

    def test_thick_band_uses_strength_bore_not_wall_fallback(self):
        # generous bands so a hollow tube is feasible -> bore comes from #1008
        # tube sizing, exercising the feasible branch in _bore_for.
        stations = [
            _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=20.0),
            _station(1.0, y_mm=500.0, band=(-60.0, 60.0), required_od=10.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) == 1
        # a hollow tube: bore strictly between 0 and OD
        assert 0.0 < pieces[0].inner_d < pieces[0].outer_d


# ---------------------------------------------------------------------------
# Fast: gh-1037 — assemblable telescoping, no zero-length, honest infeasibility
# ---------------------------------------------------------------------------


def _telescoping_joints(pieces):
    """Yield (inner, outer) consecutive piece pairs joined telescoping."""
    for inner, outer in zip(pieces, pieces[1:], strict=False):
        if inner.joint_to_next == "telescoping":
            yield inner, outer


class TestTelescopingAssemblable:
    """gh-1037 #1: a telescoping joint needs OD_outer <= ID_inner - clearance.

    The tip-side piece must physically slide INTO the root-side bore. The old
    ``max(prev_inner, strength_od)`` rule produced the inverse (fat tip into a
    narrow bore), which cannot be assembled.
    """

    def test_outer_od_fits_inside_inner_bore_with_clearance(self):
        # A monotonic taper that forces multiple telescoping splits. Both
        # adjacent pieces have strong required OD (> 0.6 * OD_prev).
        stations = [
            _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=80.0),
            _station(0.33, y_mm=300.0, band=(-30.0, 30.0), required_od=55.0),
            _station(0.66, y_mm=600.0, band=(-15.0, 15.0), required_od=28.0),
            _station(1.0, y_mm=900.0, band=(-8.0, 8.0), required_od=14.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        joints = list(_telescoping_joints(pieces))
        assert joints, "expected at least one telescoping joint"
        for inner, outer in joints:
            # the UAT falsification criterion
            assert outer.outer_d <= inner.inner_d + 1e-9, (
                f"telescoping joint inverted: outer OD {outer.outer_d:.2f} > "
                f"inner ID {inner.inner_d:.2f}"
            )

    def test_od_non_increasing_outboard(self):
        # Root piece OD >= tip piece OD: no load-path inversion (M(y) decreases).
        stations = [
            _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=80.0),
            _station(0.33, y_mm=300.0, band=(-30.0, 30.0), required_od=55.0),
            _station(0.66, y_mm=600.0, band=(-15.0, 15.0), required_od=28.0),
            _station(1.0, y_mm=900.0, band=(-8.0, 8.0), required_od=14.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        ods = [p.outer_d for p in pieces]
        assert ods == sorted(ods, reverse=True), f"OD not non-increasing outboard: {ods}"

    def test_single_root_partition_borrows_tipward_no_zero_length(self):
        # The root interval alone cannot hold the root OD (tip band collapses
        # immediately), so the root partition is a single station. It must
        # borrow the next station tipward rather than emit a zero-length piece.
        stations = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=60.0),
            _station(0.5, y_mm=250.0, band=(-8.0, 8.0), required_od=14.0),
            _station(1.0, y_mm=500.0, band=(-7.0, 7.0), required_od=12.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert pieces
        for p in pieces:
            assert p.length > 0.0
        # root piece governed by the root station's required OD
        assert pieces[0].outer_d >= 60.0 - 1e-9

    def test_no_zero_length_piece_emitted(self):
        # gh-1037 #2: per-station over-splitting must never emit length==0 pieces.
        stations = [
            _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=80.0),
            _station(0.25, y_mm=200.0, band=(-40.0, 40.0), required_od=60.0),
            _station(0.5, y_mm=400.0, band=(-22.0, 22.0), required_od=40.0),
            _station(0.75, y_mm=600.0, band=(-12.0, 12.0), required_od=22.0),
            _station(1.0, y_mm=800.0, band=(-6.0, 6.0), required_od=11.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert pieces
        for p in pieces:
            assert p.length > 0.0, f"zero-length piece emitted: {p}"


class TestInfeasibilityReporting:
    """gh-1037 #3: when no round tube strong enough fits, report infeasible."""

    def test_section_too_shallow_for_required_od_is_infeasible(self):
        # required OD ~96 mm into a ~37 mm depth band: physically impossible.
        stations = [
            _station(0.0, y_mm=0.0, band=(-18.5, 18.5), required_od=96.5),
            _station(1.0, y_mm=500.0, band=(-12.0, 12.0), required_od=40.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert pieces
        root = pieces[0]
        assert root.feasible is False
        assert root.infeasibility_reason is not None
        assert "exceeds" in root.infeasibility_reason.lower()
        # honest reporting: utilisation may exceed 1 on an impossible section,
        # never a fake 1.0.
        assert root.utilisation > 1.0

    def test_plan_marks_infeasible_when_any_piece_infeasible(self):
        left = [
            _station(0.0, y_mm=0.0, band=(-18.5, 18.5), required_od=96.5),
            _station(1.0, y_mm=-500.0, band=(-12.0, 12.0), required_od=40.0),
        ]
        right = [
            _station(0.0, y_mm=0.0, band=(-18.5, 18.5), required_od=96.5),
            _station(1.0, y_mm=500.0, band=(-12.0, 12.0), required_od=40.0),
        ]
        plan = solve_spar_plan(front_left=left, front_right=right)
        assert plan.feasible is False
        assert plan.infeasibility_reason is not None

    def test_feasible_plan_reports_feasible(self):
        plan = solve_spar_plan(front_left=_uniform_stations(), front_right=_uniform_stations())
        assert plan.feasible is True
        assert plan.infeasibility_reason is None
        for p in plan.front_pieces:
            assert p.feasible is True
            assert p.utilisation <= 1.0 + 1e-9


class TestRearTorsionDistinctFromFront:
    """gh-1038: when the rear stations are sized from a (smaller) torsion-derived
    OD, the rear spar must come out DIFFERENT from the bending-driven front — not
    a near-twin. The service builds the rear stations from T(y)/spacing; here we
    feed the solver the resulting (smaller) required_od directly."""

    def test_torsion_sized_rear_is_smaller_than_bending_front(self):
        # Front: bending-driven fat root OD.
        front = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=40.0),
            _station(1.0, y_mm=500.0, band=(-50.0, 50.0), required_od=10.0),
        ]
        # Rear: torsion couple is a fraction of bending -> markedly smaller OD.
        rear = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=12.0),
            _station(1.0, y_mm=500.0, band=(-50.0, 50.0), required_od=4.0),
        ]
        plan = solve_spar_plan(
            front_left=[_mirror(s) for s in front],
            front_right=front,
            rear_left=[_mirror(s) for s in rear],
            rear_right=rear,
        )
        front_root_od = plan.front_pieces[0].outer_d
        rear_root_od = plan.rear_pieces[0].outer_d
        assert rear_root_od < front_root_od
        # The rear OD tracks the torsion-derived station, not the bending one.
        assert rear_root_od == pytest.approx(12.0)

    def test_zero_torsion_rear_emits_no_pieces(self):
        """Zero torsion (+ no secondary bending) -> no physical rear member.

        gh-1045/#1057: a Ø0 rear spar is not a structural object. Rather than
        emit a phantom Ø0 piece (the old behaviour), the solver emits no rear
        pieces at all, and the plan stays feasible.
        """
        rear = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=0.0),
            _station(1.0, y_mm=500.0, band=(-50.0, 50.0), required_od=0.0),
        ]
        plan = solve_spar_plan(
            front_left=_uniform_stations(),
            front_right=_uniform_stations(),
            rear_left=[_mirror(s) for s in rear],
            rear_right=rear,
        )
        assert plan.rear_pieces == []
        assert plan.feasible is True


class TestZeroOdTipPieceSuppressed:
    """gh-1045/#1057: the solver must NOT emit a Ø0 terminal tip piece.

    At the tip the bending moment M(y)->0, so the strength-required OD rounds to
    0. The old solver emitted that as a feasible Ø0 piece — a phantom part you
    cannot cut, order, or glue. The fix drops the degenerate trailing piece and
    runs the previous (last real) piece to the tip with a continuous joint.
    """

    def _tapered_to_zero_tip(self) -> list[StationData]:
        # required OD decays to 0 at the very tip (the normal physical case).
        return [
            _station(0.0, y_mm=0.0, band=(-60.0, 60.0), required_od=80.0),
            _station(0.33, y_mm=300.0, band=(-30.0, 30.0), required_od=55.0),
            _station(0.66, y_mm=600.0, band=(-15.0, 15.0), required_od=28.0),
            _station(1.0, y_mm=900.0, band=(-8.0, 8.0), required_od=0.0),
        ]

    def test_no_zero_od_piece_emitted(self):
        pieces = plan_spar(self._tapered_to_zero_tip(), SparSpec(role=SparRole.FRONT))
        assert pieces
        for p in pieces:
            assert p.outer_d > 0.0, f"Ø0 piece emitted: {p}"

    def test_pieces_cover_root_to_tip_without_gap(self):
        # The remaining pieces must still cover the whole span root->tip with no
        # gap. Telescoping pieces overlap rootward (a joint IS an overlap region),
        # so the invariant is coverage, not abutment: the next piece must start at
        # or before the previous piece's tip, and the union reaches the tip.
        pieces = plan_spar(self._tapered_to_zero_tip(), SparSpec(role=SparRole.FRONT))
        covered_to = pieces[0].spare_origin[1] + pieces[0].length * pieces[0].spare_vector[1]
        for outer in pieces[1:]:
            assert outer.spare_origin[1] <= covered_to + 1e-9, (
                f"gap before piece starting at {outer.spare_origin[1]} "
                f"(covered only to {covered_to})"
            )
            covered_to = max(
                covered_to,
                outer.spare_origin[1] + outer.length * outer.spare_vector[1],
            )
        assert pieces[0].spare_origin[1] == pytest.approx(0.0)  # starts at root
        assert covered_to == pytest.approx(900.0)  # union reaches the tip

    def test_last_piece_runs_to_the_tip(self):
        # After dropping the Ø0 tip piece, the new last real piece must reach the
        # wing tip (y=900), not stop short where the Ø0 run began.
        pieces = plan_spar(self._tapered_to_zero_tip(), SparSpec(role=SparRole.FRONT))
        last = pieces[-1]
        last_tip_y = last.spare_origin[1] + last.length * last.spare_vector[1]
        assert last_tip_y == pytest.approx(900.0)

    def test_last_piece_joint_is_continuous(self):
        # The previous piece no longer telescopes into a non-existent piece.
        pieces = plan_spar(self._tapered_to_zero_tip(), SparSpec(role=SparRole.FRONT))
        assert pieces[-1].joint_to_next is None

    def test_all_zero_od_yields_no_pieces(self):
        # A spar whose every station needs Ø0 (e.g. zero torsion rear) is not a
        # structural object at all — emit nothing rather than a phantom part.
        stations = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=0.0),
            _station(1.0, y_mm=500.0, band=(-50.0, 50.0), required_od=0.0),
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert pieces == []

    def test_plan_has_no_zero_od_rear_pieces(self):
        rear = [
            _station(0.0, y_mm=0.0, band=(-50.0, 50.0), required_od=12.0),
            _station(0.5, y_mm=250.0, band=(-50.0, 50.0), required_od=4.0),
            _station(1.0, y_mm=500.0, band=(-50.0, 50.0), required_od=0.0),
        ]
        plan = solve_spar_plan(
            front_left=_uniform_stations(),
            front_right=_uniform_stations(),
            rear_left=[_mirror(s) for s in rear],
            rear_right=rear,
        )
        for p in plan.rear_pieces:
            assert p.outer_d > 0.0


def _mirror(s: StationData) -> StationData:
    return StationData(
        y_span=s.y_span,
        y_mm=-s.y_mm,
        x_c=s.x_c,
        center_z=s.center_z,
        band_lo=s.band_lo,
        band_hi=s.band_hi,
        required_od=s.required_od,
    )


class TestDegenerateRootSliceGuard:
    """gh-1037 #4: a zero-thickness slice at y_span=0 must not poison the
    governing (root) station. Sample at y_span=eps instead."""

    def test_epsilon_guard_skips_degenerate_root_slice(self):
        from cad_designer.airplane.geometry import spar_solver

        class _Pt:
            def __init__(self, y_span, thickness, center_z=0.0):
                self.y_span = y_span
                self.x_c = 0.4
                self.thickness = thickness
                self.center_z = center_z
                self.bottom_z = center_z - thickness / 2.0
                self.top_z = center_z + thickness / 2.0

        class _FakeGeometry:
            # half-span used by _half_span_mm
            _segment_lengths = [500.0]

            def at_max_thickness(self, y_span):
                # y=0 is a pinched, zero-thickness slice; everything outboard
                # is a healthy linearly-tapering section.
                if y_span <= 0.0:
                    return _Pt(0.0, 0.0)
                return _Pt(y_span, thickness=40.0 * (1.0 - 0.5 * y_span))

        stations = spar_solver.build_stations_from_geometry(
            _FakeGeometry(),
            moment_fn=lambda y: 100.0 * (1.0 - y),
            sigma_allow_mpa=300.0,
            n_span=5,
        )
        assert stations, "expected sampled stations"
        # the governing (most-inboard) station must come from a valid,
        # non-degenerate slice — its band must have positive depth.
        root = stations[0]
        assert root.band_hi - root.band_lo > 0.0
        assert root.required_od > 0.0
        # The governing station stays at the ROOT (the max-moment station): the
        # solver must sample at y_span≈eps rather than discard the root slice and
        # let an outboard station become governing. eps is small (<0.05).
        assert root.y_span < 0.05, (
            f"root station drifted outboard to y_span={root.y_span}; degenerate "
            "root slice was dropped instead of eps-sampled"
        )
        # the eps-sampled root must carry the highest moment-driven OD
        assert root.required_od == max(s.required_od for s in stations)


# ---------------------------------------------------------------------------
# Slow / requires_cadquery: real lofted wing
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.requires_cadquery
class TestSparSolverRealBuild:
    def _moment_fn(self, root_moment: float):
        # linear M(y_span): max at root, 0 at tip
        return lambda y_span: root_moment * (1.0 - y_span)

    def test_thick_straight_wing_is_continuous(self):
        from cad_designer.aerosandbox.wing_roundtrip_cases import single_segment_flat
        from cad_designer.airplane.geometry.spar_solver import (
            build_stations_from_geometry,
        )
        from cad_designer.airplane.geometry.section_geometry import SectionGeometry

        sg = SectionGeometry(single_segment_flat())
        # Modest moment so the strength OD fits inside the (~20 mm thick, t/c=0.10)
        # section's clearance band at every station -> one continuous piece.
        stations = build_stations_from_geometry(
            sg, moment_fn=self._moment_fn(8.0), sigma_allow_mpa=300.0, n_span=6
        )
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) == 1  # generous section, modest moment -> continuous

    def test_thin_tip_with_high_moment_telescopes(self):
        from cad_designer.aerosandbox.wing_roundtrip_cases import (
            single_segment_with_twist_and_dihedral,
        )
        from cad_designer.airplane.geometry.spar_solver import (
            build_stations_from_geometry,
        )
        from cad_designer.airplane.geometry.section_geometry import SectionGeometry

        sg = SectionGeometry(single_segment_with_twist_and_dihedral())
        # large root moment forces a fat root OD the tapered tip can't contain
        stations = build_stations_from_geometry(
            sg, moment_fn=self._moment_fn(8000.0), sigma_allow_mpa=200.0, n_span=8
        )
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) >= 2
        assert pieces[0].joint_to_next == "telescoping"

    def test_strong_dihedral_rear_bent_pin(self):
        from cad_designer.aerosandbox.wing_roundtrip_cases import (
            single_segment_with_dihedral,
        )
        from cad_designer.airplane.geometry.spar_solver import (
            build_stations_from_geometry,
        )
        from cad_designer.airplane.geometry.section_geometry import SectionGeometry

        sg = SectionGeometry(single_segment_with_dihedral())
        right = build_stations_from_geometry(
            sg, moment_fn=self._moment_fn(40.0), sigma_allow_mpa=300.0, n_span=6, x_c=0.65
        )
        left = [
            StationData(
                y_span=s.y_span,
                y_mm=-s.y_mm,
                x_c=s.x_c,
                center_z=s.center_z,
                band_lo=s.band_lo,
                band_hi=s.band_hi,
                required_od=s.required_od,
            )
            for s in right
        ]
        plan = solve_spar_plan(front_left=left, front_right=right, rear_left=left, rear_right=right)
        assert plan.rear_joint == "bent-pin"


# ---------------------------------------------------------------------------
# Fast: x_over_chord carried onto each piece (gh-1072)
# ---------------------------------------------------------------------------


class TestPieceCarriesXOverChord:
    """Each built piece records the chordwise x/c of its governing station."""

    def test_continuous_piece_takes_governing_station_x_c(self):
        stations = [
            _station(i / 4, y_mm=i * 100.0, band=(-50.0, 50.0), required_od=10.0, x_c=0.30)
            for i in range(5)
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.FRONT))
        assert len(pieces) == 1
        # front spar sits at the section max-thickness location (~0.30c here).
        assert pieces[0].x_over_chord == pytest.approx(0.30)

    def test_rear_piece_takes_clamped_x_c(self):
        # rear/torsion spar pulled forward of a hinge → clamped x/c (e.g. 0.62)
        stations = [
            _station(i / 4, y_mm=i * 100.0, band=(-50.0, 50.0), required_od=10.0, x_c=0.62)
            for i in range(5)
        ]
        pieces = plan_spar(stations, SparSpec(role=SparRole.REAR))
        assert len(pieces) == 1
        assert pieces[0].x_over_chord == pytest.approx(0.62)

    def test_x_over_chord_in_to_dict(self):
        stations = _uniform_stations(5)
        piece = plan_spar(stations, SparSpec(role=SparRole.FRONT))[0]
        d = piece.to_dict()
        assert d["x_over_chord"] == pytest.approx(piece.x_over_chord)

    def test_reinforcement_piece_carries_root_x_c(self):
        left = [
            _station(0.0, y_mm=0.0, center_z=0.0, band=(-50.0, 50.0), x_c=0.31),
            _station(0.5, y_mm=-200.0, center_z=0.0, band=(-50.0, 50.0), x_c=0.31),
        ]
        right = [
            _station(0.0, y_mm=0.0, center_z=40.0, band=(-50.0, 50.0), x_c=0.31),
            _station(0.5, y_mm=200.0, center_z=40.0, band=(-50.0, 50.0), x_c=0.31),
        ]
        plan = solve_spar_plan(front_left=left, front_right=right)
        assert plan.reinforcement is not None
        assert plan.reinforcement.x_over_chord == pytest.approx(0.31)
