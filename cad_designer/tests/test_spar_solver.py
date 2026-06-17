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
) -> StationData:
    """A single station with explicit containment band + required strength OD."""
    return StationData(
        y_span=y_span,
        y_mm=y_mm,
        x_c=0.4,
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
        # telescoping: outer piece OD == inner piece ID
        inner, outer = pieces[0], pieces[1]
        assert inner.joint_to_next == "telescoping"
        assert outer.outer_d == pytest.approx(inner.inner_d, abs=1e-6)
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
