"""Tests for the main-spar segment-split helper (gh-1059).

A telescoping main (front) spar has a varying diameter, so it cannot live as
multiple ``spar_index == 0`` pieces in a single wing segment (VaseMode treats
*any* index-0 spar as THE main spar). The fix is to split the host segment at
each telescoping joint y into N contiguous sub-segments, each carrying exactly
one main piece at index 0.

The split MUST be geometrically transparent — the built loft is unchanged
across the split. This is guaranteed because the loft is ruled (linear blend
root↔tip), so an intermediate section is fully determined by the linearly
interpolated chord / twist / dihedral / sweep / length plus the (same or
Kulfan-morphed) airfoil shape at the split fraction.

Two tiers:

* **fast** — pure split math + child transfer (no CAD, morph mocked).
* **slow / requires_cadquery** — build the loft BEFORE and AFTER the split and
  assert the section geometry is unchanged at sample stations.
"""

from __future__ import annotations

import math

import pytest

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import (
    TrailingEdgeDevice,
)
from cad_designer.airplane.aircraft_topology.wing.Turbulator import Turbulator
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)
from cad_designer.airplane.geometry.segment_split import (
    split_segment,
    split_segment_at_lengths,
)

AIRFOIL = "components/airfoils/naca0010.dat"
AIRFOIL_B = "components/airfoils/naca2412.dat"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _single_segment(
    *,
    root_chord: float = 200.0,
    tip_chord: float = 150.0,
    length: float = 500.0,
    sweep: float = 20.0,
    tip_dihedral: float = 8.0,
    tip_incidence: float = -4.0,
    root_af: str = AIRFOIL,
    tip_af: str | None = None,
    spare_list: list[Spare] | None = None,
    ted: TrailingEdgeDevice | None = None,
    turbulator: Turbulator | None = None,
) -> WingConfiguration:
    return WingConfiguration(
        nose_pnt=(0.0, 0.0, 0.0),
        root_airfoil=Airfoil(
            airfoil=root_af,
            chord=root_chord,
            dihedral_as_rotation_in_degrees=2.0,
            incidence=1.0,
        ),
        length=length,
        sweep=sweep,
        sweep_is_angle=False,
        tip_airfoil=Airfoil(
            airfoil=tip_af,
            chord=tip_chord,
            dihedral_as_rotation_in_degrees=tip_dihedral,
            incidence=tip_incidence,
        ),
        spare_list=spare_list,
        trailing_edge_device=ted,
        turbulator=turbulator,
        symmetric=True,
        parameters="relative",
    )


def _main_spare() -> Spare:
    return Spare(
        spare_support_dimension_width=10.0,
        spare_support_dimension_height=10.0,
        spare_length=500.0,
        spare_start=0.0,
        spare_origin=(0.0, 0.0, 0.0),
        spare_vector=(0.0, 1.0, 0.0),
        spare_mode="normal",
    )


# ---------------------------------------------------------------------------
# Fast: split math
# ---------------------------------------------------------------------------


class TestSplitMath:
    def test_single_split_produces_two_subsegments(self):
        wc = _single_segment(length=500.0)
        out = split_segment(wc, 0, [0.4])
        assert len(out.segments) == 2

    def test_lengths_sum_to_original(self):
        wc = _single_segment(length=500.0)
        out = split_segment(wc, 0, [0.4])
        total = sum(s.length for s in out.segments)
        assert total == pytest.approx(500.0)
        assert out.segments[0].length == pytest.approx(200.0)
        assert out.segments[1].length == pytest.approx(300.0)

    def test_multiple_splits_contiguous(self):
        wc = _single_segment(length=600.0)
        out = split_segment(wc, 0, [1.0 / 3.0, 2.0 / 3.0])
        assert len(out.segments) == 3
        lengths = [s.length for s in out.segments]
        assert sum(lengths) == pytest.approx(600.0)
        assert lengths[0] == pytest.approx(200.0)
        assert lengths[1] == pytest.approx(200.0)
        assert lengths[2] == pytest.approx(200.0)

    def test_split_at_lengths_helper(self):
        wc = _single_segment(length=500.0)
        out = split_segment_at_lengths(wc, 0, [150.0, 350.0])
        lengths = [s.length for s in out.segments]
        assert lengths == pytest.approx([150.0, 200.0, 150.0])

    def test_boundary_chord_linear_blend(self):
        wc = _single_segment(root_chord=200.0, tip_chord=100.0, length=500.0)
        out = split_segment(wc, 0, [0.5])
        # boundary chord at t=0.5 -> midway 150
        assert out.segments[0].tip_airfoil.chord == pytest.approx(150.0)
        # the second sub-segment's root chord equals the boundary chord
        assert out.segments[1].root_airfoil.chord == pytest.approx(150.0)
        # endpoints unchanged
        assert out.segments[0].root_airfoil.chord == pytest.approx(200.0)
        assert out.segments[1].tip_airfoil.chord == pytest.approx(100.0)

    def test_sweep_delta_split_sums(self):
        wc = _single_segment(sweep=40.0, length=500.0)
        out = split_segment(wc, 0, [0.25])
        assert out.segments[0].sweep + out.segments[1].sweep == pytest.approx(40.0)
        assert out.segments[0].sweep == pytest.approx(10.0)

    def test_incidence_delta_split_sums(self):
        # The cumulative twist root->tip is always preserved across the split.
        # original tip incidence delta = -4 (relative to root).
        wc = _single_segment(tip_incidence=-4.0, length=500.0)
        out = split_segment(wc, 0, [0.25])
        boundary_i = out.segments[0].tip_airfoil.incidence
        second_tip_i = out.segments[1].tip_airfoil.incidence
        assert boundary_i + second_tip_i == pytest.approx(-4.0)

    def test_incidence_split_near_linear_when_untapered(self):
        # gh-1068: without taper the chord-weighted twist split is ~the plain
        # linear split (boundary at fraction 0.25 of -4 ~= -1.0). It is the
        # blended-up-vector value rather than the linear angle, so it differs by
        # a sub-0.01deg sin-arc term — geometrically correct, not a regression.
        wc = _single_segment(root_chord=180.0, tip_chord=180.0, tip_incidence=-4.0, length=500.0)
        out = split_segment(wc, 0, [0.25])
        assert out.segments[0].tip_airfoil.incidence == pytest.approx(-1.0, abs=0.01)

    def test_incidence_split_is_chord_weighted_when_tapered(self):
        # gh-1068: with taper the per-sub-segment twist is NOT the linear split
        # (-1.0) but the chord-weighted value that keeps the built ruled loft's
        # center_z unchanged (the section's world-z carries a chord*sin(twist)
        # term that is nonlinear for a tapered host). Sum is still preserved.
        wc = _single_segment(root_chord=200.0, tip_chord=150.0, tip_incidence=-4.0, length=500.0)
        out = split_segment(wc, 0, [0.25])
        boundary_i = out.segments[0].tip_airfoil.incidence
        second_tip_i = out.segments[1].tip_airfoil.incidence
        assert boundary_i + second_tip_i == pytest.approx(-4.0)
        assert boundary_i != pytest.approx(-1.0)  # not the buggy linear split
        assert boundary_i == pytest.approx(-0.79977, abs=1e-4)

    def test_boundary_twist_cumulative_degenerate_zero_chord(self):
        # gh-1068: the chord-weighting falls back to a plain linear twist blend
        # when the (degenerate) ruled chord at a boundary is zero, so the helper
        # never divides by zero.
        from cad_designer.airplane.geometry.segment_split import _boundary_twist_cumulative

        out = _boundary_twist_cumulative([0.0, 0.5, 1.0], 0.0, -4.0, 0.0, 0.0)
        assert out == pytest.approx([0.0, -2.0, -4.0])

    def test_dihedral_delta_carried_on_last_subsegment(self):
        # Dihedral rotates the spanwise translation; splitting the delta
        # linearly would bend the intermediate origins off the original straight
        # ruled line. The geometrically-exact rule (proven by the slow
        # loft-unchanged test) is: ZERO dihedral delta on intermediate
        # boundaries, the FULL delta on the last sub-segment's tip.
        wc = _single_segment(tip_dihedral=8.0, length=500.0)
        out = split_segment(wc, 0, [0.25])
        boundary_d = out.segments[0].tip_airfoil.dihedral_as_rotation_in_degrees
        last_tip_d = out.segments[1].tip_airfoil.dihedral_as_rotation_in_degrees
        assert boundary_d == pytest.approx(0.0)
        assert last_tip_d == pytest.approx(8.0)
        # the total dihedral from root to original tip is preserved.
        assert boundary_d + last_tip_d == pytest.approx(8.0)

    def test_three_way_dihedral_only_on_last(self):
        wc = _single_segment(tip_dihedral=6.0, length=600.0)
        out = split_segment(wc, 0, [1.0 / 3.0, 2.0 / 3.0])
        dihedrals = [s.tip_airfoil.dihedral_as_rotation_in_degrees for s in out.segments]
        assert dihedrals[0] == pytest.approx(0.0)
        assert dihedrals[1] == pytest.approx(0.0)
        assert dihedrals[2] == pytest.approx(6.0)

    def test_same_airfoil_keeps_file(self):
        wc = _single_segment(root_af=AIRFOIL, tip_af=AIRFOIL)
        out = split_segment(wc, 0, [0.5])
        assert out.segments[0].tip_airfoil.airfoil == AIRFOIL
        assert out.segments[1].root_airfoil.airfoil == AIRFOIL

    def test_invalid_split_fraction_rejected(self):
        wc = _single_segment()
        with pytest.raises(ValueError):
            split_segment(wc, 0, [0.0])
        with pytest.raises(ValueError):
            split_segment(wc, 0, [1.0])
        with pytest.raises(ValueError):
            split_segment(wc, 0, [1.5])

    def test_unsorted_split_fractions_rejected(self):
        wc = _single_segment()
        with pytest.raises(ValueError):
            split_segment(wc, 0, [0.6, 0.3])

    def test_empty_split_returns_equivalent(self):
        wc = _single_segment(length=500.0)
        out = split_segment(wc, 0, [])
        assert len(out.segments) == 1
        assert out.segments[0].length == pytest.approx(500.0)

    def test_out_of_range_segment_rejected(self):
        wc = _single_segment()
        with pytest.raises(IndexError):
            split_segment(wc, 5, [0.5])

    def test_other_segments_untouched(self):
        wc = _single_segment(length=500.0)
        wc.add_segment(length=300.0, sweep=10.0, tip_airfoil=Airfoil(chord=80.0))
        out = split_segment(wc, 0, [0.5])
        # 2 (split seg 0) + 1 (seg 1) = 3
        assert len(out.segments) == 3
        # the untouched outer segment keeps its length
        assert out.segments[-1].length == pytest.approx(300.0)

    def test_split_non_root_segment_passes_root_through(self):
        wc = _single_segment(length=500.0)
        wc.add_segment(length=300.0, sweep=10.0, tip_airfoil=Airfoil(chord=80.0))
        out = split_segment(wc, 1, [0.5])  # split the OUTER segment
        # seg 0 passes through unchanged + 2 sub-segments of seg 1 = 3
        assert len(out.segments) == 3
        assert out.segments[0].length == pytest.approx(500.0)
        assert out.segments[1].length + out.segments[2].length == pytest.approx(300.0)

    def test_split_with_tip_segment_present(self):
        wc = _single_segment(length=500.0)
        wc.add_tip_segment(tip_type="round", length=100.0, tip_airfoil=Airfoil(chord=60.0))
        out = split_segment(wc, 0, [0.5])
        # 2 sub-segments + the carried-through tip segment = 3
        assert len(out.segments) == 3
        assert out.segments[-1].wing_segment_type == "tip"
        assert out.segments[-1].length == pytest.approx(100.0)

    def test_main_pieces_count_mismatch_rejected(self):
        wc = _single_segment(length=500.0)
        with pytest.raises(ValueError):
            split_segment(wc, 0, [0.5], main_pieces_per_subsegment=[[]])  # need 2 entries

    def test_at_lengths_zero_length_segment_rejected(self):
        wc = _single_segment(length=500.0)
        wc.segments[0].length = 0.0
        with pytest.raises(ValueError):
            split_segment_at_lengths(wc, 0, [100.0])


# ---------------------------------------------------------------------------
# Fast: main-spar index-0 per sub-segment
# ---------------------------------------------------------------------------


class TestMainSparIndexZero:
    def test_main_piece_index_zero_in_each_subsegment(self):
        wc = _single_segment(spare_list=[_main_spare()])
        main_pieces = [
            Spare(
                spare_support_dimension_width=10.0,
                spare_support_dimension_height=10.0,
                spare_length=200.0,
                spare_origin=(0.0, 0.0, 0.0),
                spare_vector=(0.0, 1.0, 0.0),
                spare_mode="normal",
            ),
            Spare(
                spare_support_dimension_width=8.0,
                spare_support_dimension_height=8.0,
                spare_length=300.0,
                spare_origin=(0.0, 200.0, 0.0),
                spare_vector=(0.0, 1.0, 0.0),
                spare_mode="normal",
            ),
        ]
        out = split_segment(
            wc, 0, [0.4], main_pieces_per_subsegment=[[main_pieces[0]], [main_pieces[1]]]
        )
        assert len(out.segments) == 2
        # each sub-segment carries its main piece at index 0
        assert out.segments[0].spare_list[0] is main_pieces[0]
        assert out.segments[1].spare_list[0] is main_pieces[1]


# ---------------------------------------------------------------------------
# Fast: control-surface duplication + naming
# ---------------------------------------------------------------------------


class TestControlSurfaceDuplication:
    def test_ted_duplicated_onto_each_subsegment(self):
        ted = TrailingEdgeDevice(name="aileron", rel_chord_root=0.75, rel_chord_tip=0.75)
        wc = _single_segment(ted=ted)
        out = split_segment(wc, 0, [0.5])
        assert out.segments[0].trailing_edge_device is not None
        assert out.segments[1].trailing_edge_device is not None

    def test_ted_names_disambiguated(self):
        ted = TrailingEdgeDevice(name="aileron", rel_chord_root=0.75)
        wc = _single_segment(ted=ted)
        out = split_segment(wc, 0, [0.5])
        names = [s.trailing_edge_device.name for s in out.segments]
        assert len(set(names)) == 2  # globally unique
        # first sub-segment keeps the original name
        assert names[0] == "aileron"

    def test_ted_role_tag_preserved(self):
        ted = TrailingEdgeDevice(name="[aileron]right", rel_chord_root=0.75)
        wc = _single_segment(ted=ted)
        out = split_segment(wc, 0, [0.5])
        for s in out.segments:
            assert s.trailing_edge_device.name.startswith("[aileron]")

    def test_ted_chord_taper_interpolated(self):
        # taper the hinge line 0.70 (root) -> 0.80 (tip) over the whole segment.
        ted = TrailingEdgeDevice(name="flap", rel_chord_root=0.70, rel_chord_tip=0.80)
        wc = _single_segment(ted=ted)
        out = split_segment(wc, 0, [0.5])
        # boundary hinge at t=0.5 -> 0.75
        assert out.segments[0].trailing_edge_device.rel_chord_tip == pytest.approx(0.75)
        assert out.segments[1].trailing_edge_device.rel_chord_root == pytest.approx(0.75)
        # endpoints preserved
        assert out.segments[0].trailing_edge_device.rel_chord_root == pytest.approx(0.70)
        assert out.segments[1].trailing_edge_device.rel_chord_tip == pytest.approx(0.80)

    def test_ted_side_spacing_interpolated(self):
        ted = TrailingEdgeDevice(
            name="flap", rel_chord_root=0.75, side_spacing_root=4.0, side_spacing_tip=8.0
        )
        wc = _single_segment(ted=ted)
        out = split_segment(wc, 0, [0.5])
        assert out.segments[0].trailing_edge_device.side_spacing_tip == pytest.approx(6.0)
        assert out.segments[1].trailing_edge_device.side_spacing_root == pytest.approx(6.0)

    def test_no_ted_leaves_none(self):
        wc = _single_segment(ted=None)
        out = split_segment(wc, 0, [0.5])
        assert out.segments[0].trailing_edge_device is None
        assert out.segments[1].trailing_edge_device is None

    def test_servo_rides_only_containing_subsegment(self):
        # servo at rel_length 0.8 -> only the OUTER sub-segment carries it.
        ted = TrailingEdgeDevice(
            name="aileron",
            rel_chord_root=0.75,
            servo=7,
            rel_chord_servo_position=0.85,
            rel_length_servo_position=0.8,
        )
        wc = _single_segment(ted=ted)
        out = split_segment(wc, 0, [0.5])
        assert out.segments[0].trailing_edge_device._servo is None
        assert out.segments[1].trailing_edge_device._servo == 7
        # re-expressed within the outer sub-span: (0.8 - 0.5) / 0.5 = 0.6
        assert out.segments[1].trailing_edge_device.rel_length_servo_position == pytest.approx(0.6)


class TestMorphSeamFallbackNoFn:
    def test_differing_airfoil_without_morph_fn_keeps_inboard(self):
        # No morph seam supplied for differing anchors -> boundary keeps the
        # inboard anchor's airfoil so the section is still buildable.
        wc = _single_segment(root_af=AIRFOIL, tip_af=AIRFOIL_B)
        out = split_segment(wc, 0, [0.5])  # no airfoil_morph_fn
        assert out.segments[0].tip_airfoil.airfoil == AIRFOIL
        assert out.segments[1].root_airfoil.airfoil == AIRFOIL


# ---------------------------------------------------------------------------
# Fast: turbulator carry-along
# ---------------------------------------------------------------------------


class TestTurbulatorCarry:
    def test_turbulator_carried_onto_each_subsegment(self):
        turb = Turbulator(position_root=0.10, position_tip=0.20, form="zigzag")
        wc = _single_segment(turbulator=turb)
        out = split_segment(wc, 0, [0.5])
        assert out.segments[0].turbulator is not None
        assert out.segments[1].turbulator is not None

    def test_turbulator_position_interpolated(self):
        turb = Turbulator(position_root=0.10, position_tip=0.20)
        wc = _single_segment(turbulator=turb)
        out = split_segment(wc, 0, [0.5])
        # boundary at t=0.5 -> 0.15
        assert out.segments[0].turbulator.position_tip == pytest.approx(0.15)
        assert out.segments[1].turbulator.position_root == pytest.approx(0.15)
        assert out.segments[0].turbulator.position_root == pytest.approx(0.10)
        assert out.segments[1].turbulator.position_tip == pytest.approx(0.20)

    def test_turbulator_form_preserved(self):
        turb = Turbulator(position_root=0.10, form="dots", height_mm=0.5)
        wc = _single_segment(turbulator=turb)
        out = split_segment(wc, 0, [0.5])
        for s in out.segments:
            assert s.turbulator.form == "dots"
            assert s.turbulator.height_mm == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Fast: existing-spare re-home
# ---------------------------------------------------------------------------


class TestSpareRehome:
    def _spare_at_y(self, y: float) -> Spare:
        return Spare(
            spare_support_dimension_width=5.0,
            spare_support_dimension_height=5.0,
            spare_length=50.0,
            spare_origin=(0.0, y, 0.0),
            spare_vector=(0.0, 1.0, 0.0),
            spare_mode="normal",
        )

    def test_inboard_spare_homes_to_first_subsegment(self):
        s = self._spare_at_y(50.0)  # y=50 < boundary 200
        wc = _single_segment(length=500.0, spare_list=[s])
        out = split_segment(wc, 0, [0.4])  # boundary at 200mm
        assert s in (out.segments[0].spare_list or [])
        assert s not in (out.segments[1].spare_list or [])

    def test_outboard_spare_homes_to_second_subsegment(self):
        s = self._spare_at_y(300.0)  # y=300 > boundary 200
        wc = _single_segment(length=500.0, spare_list=[s])
        out = split_segment(wc, 0, [0.4])
        assert s in (out.segments[1].spare_list or [])
        assert s not in (out.segments[0].spare_list or [])

    def test_spare_origin_uses_local_offset(self):
        # spare origin y is segment-local; re-home keys off local y vs sub-span.
        s_in = self._spare_at_y(100.0)
        s_out = self._spare_at_y(400.0)
        wc = _single_segment(length=500.0, spare_list=[s_in, s_out])
        out = split_segment(wc, 0, [0.5])  # boundary at 250mm
        assert s_in in out.segments[0].spare_list
        assert s_out in out.segments[1].spare_list

    def test_spare_on_outer_tip_boundary_homes_to_last(self):
        # a spare sitting exactly at the segment tip y belongs to the last sub-span.
        s_tip = self._spare_at_y(500.0)
        wc = _single_segment(length=500.0, spare_list=[s_tip])
        out = split_segment(wc, 0, [0.5])
        assert s_tip in out.segments[1].spare_list

    def test_via_at_lengths_rehome(self):
        s_in = self._spare_at_y(80.0)
        s_out = self._spare_at_y(300.0)
        wc = _single_segment(length=500.0, spare_list=[s_in, s_out])
        out = split_segment_at_lengths(wc, 0, [200.0])
        assert s_in in out.segments[0].spare_list
        assert s_out in out.segments[1].spare_list

    def test_exactly_root_y_spare_survives_on_first_subsegment(self):
        # gh-1067: a spare at exactly y=0 (segment root) must not be dropped.
        s_root = self._spare_at_y(0.0)
        wc = _single_segment(length=500.0, spare_list=[s_root])
        out = split_segment(wc, 0, [0.4])
        assert s_root in (out.segments[0].spare_list or [])
        assert s_root not in (out.segments[1].spare_list or [])

    def test_negative_root_y_spare_survives_on_first_subsegment(self):
        # gh-1067 (DATA LOSS): the DB round-trip reconstructs a manual root spare
        # with a slightly negative local y (e.g. -0.6mm from dihedral geometry).
        # That spare is the most load-critical (main joiner tube at the root) and
        # must clamp to the root sub-segment, never be silently dropped.
        s_neg = self._spare_at_y(-0.6266)
        wc = _single_segment(length=500.0, spare_list=[s_neg])
        out = split_segment(wc, 0, [0.4])
        assert s_neg in (out.segments[0].spare_list or [])
        assert s_neg not in (out.segments[1].spare_list or [])

    def test_no_spare_is_lost_across_split(self):
        # gh-1067: total spare count must be conserved across a split (no silent
        # drop), including a negative-y root spare alongside ordinary ones.
        s_neg = self._spare_at_y(-0.6266)
        s_mid = self._spare_at_y(150.0)
        s_out = self._spare_at_y(400.0)
        wc = _single_segment(length=500.0, spare_list=[s_neg, s_mid, s_out])
        out = split_segment(wc, 0, [0.4])
        rehomed = [sp for seg in out.segments for sp in (seg.spare_list or [])]
        for s in (s_neg, s_mid, s_out):
            assert s in rehomed

    def test_rehome_helper_keeps_negative_root_y(self):
        # gh-1067 minimal repro from the ticket: _rehome_spares must not drop a
        # spare whose local origin y is slightly negative for the first sub-span.
        from cad_designer.airplane.geometry.segment_split import _rehome_spares

        s = self._spare_at_y(-0.6266)
        assert len(_rehome_spares([s], 0.0, 200.0)) == 1


# ---------------------------------------------------------------------------
# Fast: differing-airfoil split uses the injected morph seam (gh-796 reuse)
# ---------------------------------------------------------------------------


class TestMorphSeam:
    def test_differing_airfoil_calls_morph_fn(self):
        calls: list[tuple[str, str, float]] = []

        def fake_morph(a: str, b: str, t: float) -> str:
            calls.append((a, b, t))
            return "components/airfoils/__morphed__.dat"

        wc = _single_segment(root_af=AIRFOIL, tip_af=AIRFOIL_B)
        out = split_segment(wc, 0, [0.5], airfoil_morph_fn=fake_morph)
        assert calls == [(AIRFOIL, AIRFOIL_B, 0.5)]
        assert out.segments[0].tip_airfoil.airfoil == "components/airfoils/__morphed__.dat"
        assert out.segments[1].root_airfoil.airfoil == "components/airfoils/__morphed__.dat"

    def test_morph_fn_none_falls_back_to_root_airfoil(self):
        # When the morph function returns None (fit failed), the boundary keeps
        # the inboard anchor's airfoil so a buildable form is still captured.
        def fake_morph(a: str, b: str, t: float) -> None:
            return None

        wc = _single_segment(root_af=AIRFOIL, tip_af=AIRFOIL_B)
        out = split_segment(wc, 0, [0.5], airfoil_morph_fn=fake_morph)
        assert out.segments[0].tip_airfoil.airfoil == AIRFOIL

    def test_same_airfoil_does_not_call_morph(self):
        def boom(a: str, b: str, t: float) -> str:  # pragma: no cover - must not run
            raise AssertionError("morph must not be called for same-airfoil segments")

        wc = _single_segment(root_af=AIRFOIL, tip_af=AIRFOIL)
        split_segment(wc, 0, [0.5], airfoil_morph_fn=boom)


# ---------------------------------------------------------------------------
# Slow / requires_cadquery: the split is geometrically transparent.
# Build the loft BEFORE and AFTER the split and assert the section geometry
# (thickness / top_z / bottom_z / center_z) is unchanged at sample stations.
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.requires_cadquery
class TestLoftUnchangedAcrossSplit:
    """The split must be geometrically transparent: the built loft is unchanged.

    The proof uses the **analytic** SectionGeometry mode — the ground-truth
    ruled (linear) blend the loft is built from — and asserts the section
    geometry at sample stations matches before vs after the split. The
    **solid** mode (real CAD slice) is also checked, at a looser tolerance that
    absorbs the slicer's own discretisation noise (the analytic↔solid
    equivalence test in test_section_geometry already bounds that to a fraction
    of a mm / percent).

    Transparency is *exact* for taper + sweep + dihedral (dihedral carried on
    the last sub-segment keeps every intermediate origin on the original
    straight ruled line). It is *near-exact* for twist combined with taper: a
    rotated-and-scaled intermediate wire differs from the linear blend of the
    two endpoint wires by a small twist×taper nonlinearity (sub-mm on
    representative wings) — the same approximation class as any
    intermediate-airfoil insertion. We bound that residual explicitly.
    """

    _SAMPLE_Y = [0.1, 0.3, 0.5, 0.7, 0.9]
    _SAMPLE_X = [0.15, 0.3, 0.5, 0.7]

    def _max_section_diff(self, before, after, *, mode: str) -> float:
        from cad_designer.airplane.geometry.section_geometry import SectionGeometry

        sg_before = SectionGeometry(before, mode=mode)
        sg_after = SectionGeometry(after, mode=mode)
        worst = 0.0
        for y in self._SAMPLE_Y:
            for x in self._SAMPLE_X:
                pb = sg_before.at(y, x)
                pa = sg_after.at(y, x)
                worst = max(
                    worst,
                    abs(pa.thickness - pb.thickness),
                    abs(pa.top_z - pb.top_z),
                    abs(pa.bottom_z - pb.bottom_z),
                    abs(pa.center_z - pb.center_z),
                )
        return worst

    def test_taper_sweep_dihedral_split_is_exact(self):
        """No twist → the split is geometrically exact (sub-0.1mm)."""
        before = _single_segment(
            root_chord=200.0,
            tip_chord=120.0,
            length=600.0,
            sweep=40.0,
            tip_dihedral=6.0,
            tip_incidence=0.0,
            root_af=AIRFOIL,
            tip_af=AIRFOIL,
        )
        after = split_segment(before, 0, [1.0 / 3.0, 2.0 / 3.0])
        assert len(after.segments) == 3
        assert self._max_section_diff(before, after, mode="analytic") < 0.1

    def test_untapered_twist_split_is_exact(self):
        """Twist without taper → exact (twist×taper nonlinearity absent)."""
        before = _single_segment(
            root_chord=180.0,
            tip_chord=180.0,
            length=500.0,
            sweep=30.0,
            tip_dihedral=5.0,
            tip_incidence=-6.0,
            root_af=AIRFOIL,
            tip_af=AIRFOIL,
        )
        after = split_segment(before, 0, [0.5])
        assert self._max_section_diff(before, after, mode="analytic") < 0.1

    def test_full_taper_twist_dihedral_split_residual_bounded(self):
        """Taper + twist combined → small bounded twist×taper residual (<1.5mm)."""
        before = _single_segment(
            root_chord=200.0,
            tip_chord=120.0,
            length=600.0,
            sweep=40.0,
            tip_dihedral=6.0,
            tip_incidence=-4.0,
            root_af=AIRFOIL,
            tip_af=AIRFOIL,
        )
        after = split_segment(before, 0, [1.0 / 3.0, 2.0 / 3.0])
        # Analytic ground truth: a sub-1.5mm twist×taper residual on a 600mm
        # wing (~0.25% of span). Documented, not silently widened.
        assert self._max_section_diff(before, after, mode="analytic") < 1.5

    def test_twist_taper_washout_split_center_z_unchanged(self):
        """gh-1068: a twist+taper (washout) host split must keep intermediate
        section center_z on the original ruled loft.

        The bug: incidence was split *linearly*, but a section's world-z carries
        a ``chord·sin(twist)`` term that is nonlinear for a tapered host, so the
        inserted intermediate wire drifted the center_z by up to ~0.7-0.9mm. The
        chord-weighted twist split keeps it within µm-class tolerance.
        """
        before = _single_segment(
            root_chord=200.0,
            tip_chord=120.0,  # taper — the bug needs taper AND twist
            length=1200.0,
            sweep=0.0,
            tip_dihedral=5.0,
            tip_incidence=-4.0,  # 4 deg washout root->tip
            root_af=AIRFOIL,
            tip_af=AIRFOIL,
        )
        after = split_segment(before, 0, [533.0 / 1200.0])
        assert len(after.segments) == 2
        # center_z must match pre-split within a tight tolerance (was ~0.7mm).
        assert self._max_section_diff(before, after, mode="analytic") <= 0.1

    def test_twist_taper_washout_split_center_z_unchanged_solid(self):
        """gh-1068: confirmed in the REAL solid ruled loft, not just analytic."""
        before = _single_segment(
            root_chord=200.0,
            tip_chord=120.0,
            length=1200.0,
            sweep=0.0,
            tip_dihedral=5.0,
            tip_incidence=-4.0,
            root_af=AIRFOIL,
            tip_af=AIRFOIL,
        )
        after = split_segment(before, 0, [533.0 / 1200.0])
        assert self._max_section_diff(before, after, mode="solid") <= 0.1

    def test_solid_loft_unchanged_within_slicer_noise(self):
        """The real CAD solid lofts the same across the split (slicer-noise tol)."""
        before = _single_segment(
            root_chord=200.0,
            tip_chord=120.0,
            length=600.0,
            sweep=40.0,
            tip_dihedral=6.0,
            tip_incidence=0.0,
            root_af=AIRFOIL,
            tip_af=AIRFOIL,
        )
        after = split_segment(before, 0, [1.0 / 3.0, 2.0 / 3.0])
        # Exact-geometry (no-twist) case; the residual here is the solid
        # slicer's own discretisation, bounded to ~1mm on this section.
        assert self._max_section_diff(before, after, mode="solid") < 1.0

    def test_split_preserves_total_span(self):
        before = _single_segment(length=600.0, root_af=AIRFOIL, tip_af=AIRFOIL)
        after = split_segment(before, 0, [0.5])
        span_before = before.segments[0].length
        span_after = sum(s.length for s in after.segments)
        assert span_after == pytest.approx(span_before)

    def test_differing_airfoil_split_is_transparent_via_kulfan(self):
        from app.converters.openvsp_airfoil import morph_airfoils

        before = _single_segment(
            root_chord=200.0,
            tip_chord=150.0,
            length=500.0,
            sweep=20.0,
            tip_dihedral=4.0,
            tip_incidence=0.0,
            root_af=AIRFOIL,
            tip_af=AIRFOIL_B,
        )
        after = split_segment(before, 0, [0.5], airfoil_morph_fn=morph_airfoils)
        # Kulfan morphing approximates the ruled blend of two different shapes;
        # bound the residual on the real solid loft.
        assert self._max_section_diff(before, after, mode="solid") < 3.0


def test_helper_module_importable():
    # the module must expose both the fraction- and length-based entry points.
    assert callable(split_segment)
    assert callable(split_segment_at_lengths)
    assert math.isclose(1.0, 1.0)
