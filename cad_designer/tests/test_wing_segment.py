"""Tests for cad_designer.airplane.aircraft_topology.wing.WingSegment."""

import math

import pytest

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def root_airfoil():
    return Airfoil(airfoil="naca2415", chord=200.0, dihedral_as_rotation_in_degrees=3.0, incidence=1.0)


@pytest.fixture()
def tip_airfoil():
    return Airfoil(airfoil="naca2415", chord=150.0, dihedral_as_rotation_in_degrees=0.0, incidence=0.5)


@pytest.fixture()
def sample_spare():
    return Spare(spare_support_dimension_width=10.0, spare_support_dimension_height=5.0, spare_position_factor=0.3)


@pytest.fixture()
def sample_ted():
    return TrailingEdgeDevice(name="aileron", rel_chord_root=0.75, rel_chord_tip=0.8)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestWingSegmentInit:
    """Test WingSegment constructor and sweep calculations."""

    def test_minimal_construction(self, root_airfoil):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0)
        assert ws.root_airfoil is root_airfoil
        assert ws.length == 500.0
        assert ws.sweep == 0.0
        assert ws.sweep_angle == 0.0
        assert ws.tip_airfoil is None
        assert ws.spare_list is None
        assert ws.trailing_edge_device is None
        assert ws.number_interpolation_points is None
        assert ws.tip_type is None
        assert ws.wing_segment_type == "segment"

    def test_with_all_params(self, root_airfoil, tip_airfoil, sample_spare, sample_ted):
        ws = WingSegment(
            root_airfoil=root_airfoil,
            length=500.0,
            sweep=50.0,
            tip_airfoil=tip_airfoil,
            spare_list=[sample_spare],
            trailing_edge_device=sample_ted,
            number_interpolation_points=100,
            tip_type="round",
            wing_segment_type="root",
        )
        assert ws.tip_airfoil is tip_airfoil
        assert len(ws.spare_list) == 1
        assert ws.trailing_edge_device is sample_ted
        assert ws.number_interpolation_points == 100
        assert ws.tip_type == "round"
        assert ws.wing_segment_type == "root"

    def test_wing_segment_types(self, root_airfoil):
        for seg_type in ("root", "segment", "tip"):
            ws = WingSegment(root_airfoil=root_airfoil, length=100.0, wing_segment_type=seg_type)
            assert ws.wing_segment_type == seg_type


# ---------------------------------------------------------------------------
# Sweep calculations
# ---------------------------------------------------------------------------

class TestSweepCalculation:
    """Test sweep distance vs. sweep angle conversion."""

    def test_sweep_as_distance(self, root_airfoil):
        """When sweep_is_angle=False (default), sweep is a distance and angle is derived."""
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, sweep=100.0)
        expected_angle = math.degrees(math.atan(100.0 / 500.0))
        assert ws.sweep == 100.0
        assert ws.sweep_angle == pytest.approx(expected_angle)

    def test_sweep_as_angle(self, root_airfoil):
        """When sweep_is_angle=True, sweep distance is computed from angle and length."""
        angle_deg = 30.0
        length = 500.0
        ws = WingSegment(root_airfoil=root_airfoil, length=length, sweep=angle_deg, sweep_is_angle=True)
        expected_distance = length * math.tan(math.radians(angle_deg))
        assert ws.sweep_angle == angle_deg
        assert ws.sweep == pytest.approx(expected_distance)

    def test_zero_sweep_distance(self, root_airfoil):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, sweep=0.0)
        assert ws.sweep == 0.0
        assert ws.sweep_angle == 0.0

    def test_zero_sweep_angle(self, root_airfoil):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, sweep=0.0, sweep_is_angle=True)
        assert ws.sweep == pytest.approx(0.0)
        assert ws.sweep_angle == 0.0

    def test_45_degree_sweep_equals_length(self, root_airfoil):
        """tan(45) = 1, so sweep distance should equal length."""
        length = 300.0
        ws = WingSegment(root_airfoil=root_airfoil, length=length, sweep=45.0, sweep_is_angle=True)
        assert ws.sweep == pytest.approx(length, rel=1e-9)

    def test_sweep_angle_from_distance_small(self, root_airfoil):
        """Small sweep distance should give small angle."""
        ws = WingSegment(root_airfoil=root_airfoil, length=1000.0, sweep=1.0)
        assert ws.sweep_angle == pytest.approx(math.degrees(math.atan(0.001)), rel=1e-6)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestWingSegmentSerialization:
    """Test __getstate__ and from_json_dict."""

    def test_getstate_minimal(self, root_airfoil):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0)
        state = ws.__getstate__()
        assert state["length"] == 500.0
        assert state["sweep"] == 0.0
        assert state["wing_segment_type"] == "segment"
        # root_airfoil should be serialized as a dict (via Airfoil.__getstate__)
        assert isinstance(state["root_airfoil"], dict)
        assert state["root_airfoil"]["airfoil"] == "naca2415"
        assert state["tip_airfoil"] is None
        assert state["spare_list"] is None
        assert state["trailing_edge_device"] is None

    def test_getstate_with_spares(self, root_airfoil, sample_spare):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, spare_list=[sample_spare])
        state = ws.__getstate__()
        assert isinstance(state["spare_list"], list)
        assert len(state["spare_list"]) == 1
        assert isinstance(state["spare_list"][0], dict)

    def test_getstate_with_ted(self, root_airfoil, sample_ted):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, trailing_edge_device=sample_ted)
        state = ws.__getstate__()
        assert isinstance(state["trailing_edge_device"], dict)

    def test_from_json_dict_minimal(self):
        data = {
            "root_airfoil": {"airfoil": "rg15", "chord": 180.0},
            "length": 400.0,
        }
        ws = WingSegment.from_json_dict(data)
        assert ws.root_airfoil.airfoil == "rg15"
        assert ws.root_airfoil.chord == 180.0
        assert ws.length == 400.0
        assert ws.wing_segment_type == "segment"

    def test_from_json_dict_with_spares(self):
        data = {
            "root_airfoil": {"airfoil": "naca2415", "chord": 200.0},
            "length": 500.0,
            "spare_list": [
                {"spare_support_dimension_width": 10.0, "spare_support_dimension_height": 5.0},
                {"spare_support_dimension_width": 8.0, "spare_support_dimension_height": 4.0, "spare_mode": "follow"},
            ],
        }
        ws = WingSegment.from_json_dict(data)
        assert len(ws.spare_list) == 2
        assert ws.spare_list[1].spare_mode == "follow"

    def test_from_json_dict_with_tip_airfoil(self):
        data = {
            "root_airfoil": {"airfoil": "naca2415", "chord": 200.0},
            "tip_airfoil": {"airfoil": "naca2415", "chord": 120.0, "incidence": -1.0},
            "length": 600.0,
        }
        ws = WingSegment.from_json_dict(data)
        assert ws.tip_airfoil is not None
        assert ws.tip_airfoil.chord == 120.0
        assert ws.tip_airfoil.incidence == -1.0

    def test_roundtrip(self, root_airfoil, tip_airfoil, sample_spare, sample_ted):
        original = WingSegment(
            root_airfoil=root_airfoil,
            length=500.0,
            sweep=50.0,
            tip_airfoil=tip_airfoil,
            spare_list=[sample_spare],
            trailing_edge_device=sample_ted,
            wing_segment_type="root",
        )
        state = original.__getstate__()
        restored = WingSegment.from_json_dict(state)

        assert restored.length == original.length
        assert restored.sweep == pytest.approx(original.sweep)
        assert restored.wing_segment_type == original.wing_segment_type
        assert restored.root_airfoil.airfoil == original.root_airfoil.airfoil
        assert restored.root_airfoil.chord == original.root_airfoil.chord
        assert restored.tip_airfoil.airfoil == original.tip_airfoil.airfoil
        assert restored.tip_airfoil.chord == original.tip_airfoil.chord
        assert len(restored.spare_list) == 1
        assert restored.trailing_edge_device is not None

    def test_roundtrip_preserves_sweep_angle(self, root_airfoil):
        """Roundtrip should preserve sweep distance (angle is re-derived)."""
        original = WingSegment(root_airfoil=root_airfoil, length=500.0, sweep=75.0)
        state = original.__getstate__()
        restored = WingSegment.from_json_dict(state)
        assert restored.sweep == pytest.approx(original.sweep)
        assert restored.sweep_angle == pytest.approx(original.sweep_angle)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestWingSegmentEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_spare_list(self, root_airfoil):
        """Regression test for gh-290: empty spare_list must serialize as [], not None."""
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, spare_list=[])
        state = ws.__getstate__()
        # Empty list should serialize as empty list, not None
        assert state["spare_list"] == []

    def test_from_json_dict_missing_optional_fields(self):
        data = {
            "root_airfoil": {"airfoil": "naca0010"},
            "length": 300.0,
        }
        ws = WingSegment.from_json_dict(data)
        assert ws.tip_airfoil is None
        assert ws.spare_list is None
        assert ws.trailing_edge_device is None
        assert ws.number_interpolation_points is None
        assert ws.tip_type is None

    def test_from_json_dict_tip_type(self):
        data = {
            "root_airfoil": {"airfoil": "naca0010"},
            "length": 100.0,
            "tip_type": "round",
            "wing_segment_type": "tip",
        }
        ws = WingSegment.from_json_dict(data)
        assert ws.tip_type == "round"
        assert ws.wing_segment_type == "tip"


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

class TestWingSegmentRepr:
    def test_repr_does_not_raise(self, root_airfoil):
        ws = WingSegment(root_airfoil=root_airfoil, length=500.0, sweep=30.0)
        result = repr(ws)
        assert "500.0" in result
