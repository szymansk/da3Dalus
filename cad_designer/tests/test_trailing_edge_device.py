"""Tests for TrailingEdgeDevice topology model."""

import pytest

from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import (
    TrailingEdgeDevice,
    HingeType,
    ServoPlacement,
)

try:
    from cad_designer.airplane.aircraft_topology.components.Servo import Servo

    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False

requires_cadquery = pytest.mark.skipif(
    not HAS_CADQUERY, reason="CadQuery / OCP not available"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_servo(**overrides):
    """Helper to create a Servo with sensible defaults."""
    defaults = dict(
        length=23.0,
        width=12.5,
        height=25.0,
        leading_length=8.0,
        latch_z=3.0,
        latch_x=2.0,
        latch_thickness=1.5,
        latch_length=4.0,
        cable_z=10.0,
        screw_hole_lx=1.0,
        screw_hole_d=2.0,
    )
    defaults.update(overrides)
    return Servo(**defaults)


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


class TestTrailingEdgeDeviceDefaults:
    """Verify default values assigned by the constructor."""

    def test_minimal_construction(self):
        ted = TrailingEdgeDevice(name="flap")
        assert ted.name == "flap"
        assert ted.rel_chord_root == 0.8
        assert ted.rel_chord_tip == 0.8  # falls back to root when tip is None
        assert ted.hinge_spacing is None
        assert ted.side_spacing_root is None
        assert ted.side_spacing_tip is None
        assert ted._servo is None
        assert ted.servo_placement == "top"
        assert ted.rel_chord_servo_position is None
        assert ted.rel_length_servo_position is None
        assert ted.positive_deflection_deg == 25
        assert ted.negative_deflection_deg == 25
        assert ted.trailing_edge_offset_factor == 1.0
        assert ted.hinge_type == "top"
        assert ted.symmetric is True


class TestTrailingEdgeDeviceConstructor:
    """Verify all constructor parameters are stored correctly."""

    def test_all_parameters(self):
        ted = TrailingEdgeDevice(
            name="aileron",
            rel_chord_root=0.7,
            rel_chord_tip=0.6,
            hinge_spacing=5.0,
            side_spacing_root=2.0,
            side_spacing_tip=3.0,
            servo=42,
            servo_placement="bottom",
            rel_chord_servo_position=0.5,
            rel_length_servo_position=0.3,
            positive_deflection_deg=30,
            negative_deflection_deg=15,
            trailing_edge_offset_factor=0.9,
            hinge_type="middle",
            symmetric=False,
        )
        assert ted.name == "aileron"
        assert ted.rel_chord_root == 0.7
        assert ted.rel_chord_tip == 0.6
        assert ted.hinge_spacing == 5.0
        assert ted.side_spacing_root == 2.0
        assert ted.side_spacing_tip == 3.0
        assert ted._servo == 42
        assert ted.servo_placement == "bottom"
        assert ted.rel_chord_servo_position == 0.5
        assert ted.rel_length_servo_position == 0.3
        assert ted.positive_deflection_deg == 30
        assert ted.negative_deflection_deg == 15
        assert ted.trailing_edge_offset_factor == 0.9
        assert ted.hinge_type == "middle"
        assert ted.symmetric is False

    def test_tip_defaults_to_root_when_none(self):
        ted = TrailingEdgeDevice(name="flap", rel_chord_root=0.65)
        assert ted.rel_chord_tip == 0.65

    def test_tip_independent_of_root(self):
        ted = TrailingEdgeDevice(name="flap", rel_chord_root=0.7, rel_chord_tip=0.5)
        assert ted.rel_chord_root == 0.7
        assert ted.rel_chord_tip == 0.5

    @requires_cadquery
    def test_servo_object_stored(self):
        servo = _make_servo()
        ted = TrailingEdgeDevice(name="flap", servo=servo)
        assert ted._servo is servo

    def test_servo_int_id_stored(self):
        ted = TrailingEdgeDevice(name="flap", servo=99)
        assert ted._servo == 99


# ---------------------------------------------------------------------------
# Hinge types
# ---------------------------------------------------------------------------

class TestHingeTypes:
    """Verify all documented hinge type literals."""

    @pytest.mark.parametrize(
        "hinge_type",
        ["middle", "top", "top_simple", "round_inside", "round_outside"],
    )
    def test_valid_hinge_types(self, hinge_type):
        ted = TrailingEdgeDevice(name="flap", hinge_type=hinge_type)
        assert ted.hinge_type == hinge_type


# ---------------------------------------------------------------------------
# Servo placement
# ---------------------------------------------------------------------------

class TestServoPlacement:
    @pytest.mark.parametrize("placement", ["top", "bottom"])
    def test_valid_placements(self, placement):
        ted = TrailingEdgeDevice(name="flap", servo_placement=placement)
        assert ted.servo_placement == placement


# ---------------------------------------------------------------------------
# Deflection angles
# ---------------------------------------------------------------------------

class TestDeflectionAngles:
    def test_zero_deflection(self):
        ted = TrailingEdgeDevice(
            name="flap", positive_deflection_deg=0, negative_deflection_deg=0
        )
        assert ted.positive_deflection_deg == 0
        assert ted.negative_deflection_deg == 0

    def test_asymmetric_deflection(self):
        ted = TrailingEdgeDevice(
            name="aileron",
            positive_deflection_deg=30,
            negative_deflection_deg=15,
            symmetric=False,
        )
        assert ted.positive_deflection_deg == 30
        assert ted.negative_deflection_deg == 15
        assert ted.symmetric is False

    def test_large_deflection(self):
        ted = TrailingEdgeDevice(
            name="flap", positive_deflection_deg=90, negative_deflection_deg=45
        )
        assert ted.positive_deflection_deg == 90
        assert ted.negative_deflection_deg == 45


# ---------------------------------------------------------------------------
# servo() method
# ---------------------------------------------------------------------------

@requires_cadquery
class TestServoMethod:
    """Test the servo() accessor which resolves servo references."""

    def test_servo_none_returns_none(self):
        ted = TrailingEdgeDevice(name="flap", servo=None)
        assert ted.servo(servo_information=None) is None
        assert ted.servo(servo_information={}) is None

    def test_servo_object_returned_directly(self):
        servo = _make_servo()
        ted = TrailingEdgeDevice(name="flap", servo=servo)
        result = ted.servo(servo_information=None)
        assert result is servo

    def test_servo_object_returned_with_info_dict(self):
        servo = _make_servo()
        ted = TrailingEdgeDevice(name="flap", servo=servo)
        result = ted.servo(servo_information={1: "dummy"})
        assert result is servo

    def test_servo_int_resolved_from_info(self):
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        servo = _make_servo()
        info = ServoInformation(
            height=servo.height,
            width=servo.width,
            length=servo.length,
            lever_length=5.0,
            servo=servo,
        )
        ted = TrailingEdgeDevice(name="flap", servo=42)
        result = ted.servo(servo_information={42: info})
        assert result is servo

    def test_servo_int_missing_in_info_raises(self):
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        servo = _make_servo()
        info = ServoInformation(
            height=servo.height,
            width=servo.width,
            length=servo.length,
            lever_length=5.0,
            servo=servo,
        )
        ted = TrailingEdgeDevice(name="flap", servo=99)
        with pytest.raises(ValueError, match="No servo information for servo '99'"):
            ted.servo(servo_information={42: info})

    def test_servo_int_no_info_dict_raises(self):
        ted = TrailingEdgeDevice(name="flap", servo=42)
        with pytest.raises(ValueError, match="No servo information provided"):
            ted.servo(servo_information=None)


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestRepr:
    def test_repr_contains_name(self):
        ted = TrailingEdgeDevice(name="aileron")
        r = repr(ted)
        assert "aileron" in r


# ---------------------------------------------------------------------------
# __getstate__ / serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_getstate_contains_all_keys(self):
        ted = TrailingEdgeDevice(name="flap")
        state = ted.__getstate__()
        assert state["name"] == "flap"
        assert state["rel_chord_root"] == 0.8
        assert state["hinge_type"] == "top"
        assert "_servo" in state

    def test_getstate_servo_none(self):
        ted = TrailingEdgeDevice(name="flap", servo=None)
        state = ted.__getstate__()
        assert state["_servo"] is None

    def test_getstate_servo_int(self):
        ted = TrailingEdgeDevice(name="flap", servo=7)
        state = ted.__getstate__()
        assert state["_servo"] == 7

    @requires_cadquery
    def test_getstate_servo_object_serialized(self):
        servo = _make_servo()
        ted = TrailingEdgeDevice(name="flap", servo=servo)
        state = ted.__getstate__()
        assert isinstance(state["_servo"], dict)
        assert state["_servo"]["model"] == "Servo"
        assert state["_servo"]["length"] == 23.0


# ---------------------------------------------------------------------------
# from_json_dict
# ---------------------------------------------------------------------------

class TestFromJsonDict:
    def test_roundtrip_basic(self):
        ted = TrailingEdgeDevice(
            name="flap",
            rel_chord_root=0.75,
            rel_chord_tip=0.6,
            hinge_spacing=3.0,
            positive_deflection_deg=20,
            negative_deflection_deg=10,
            hinge_type="middle",
            servo_placement="bottom",
            symmetric=False,
        )
        state = ted.__getstate__()
        restored = TrailingEdgeDevice.from_json_dict(state)
        assert restored.name == "flap"
        assert restored.rel_chord_root == 0.75
        assert restored.rel_chord_tip == 0.6
        assert restored.hinge_spacing == 3.0
        assert restored.positive_deflection_deg == 20
        assert restored.negative_deflection_deg == 10
        assert restored.hinge_type == "middle"
        assert restored.servo_placement == "bottom"
        assert restored.symmetric is False

    def test_roundtrip_servo_none(self):
        ted = TrailingEdgeDevice(name="flap", servo=None)
        state = ted.__getstate__()
        restored = TrailingEdgeDevice.from_json_dict(state)
        assert restored._servo is None

    def test_roundtrip_servo_int(self):
        ted = TrailingEdgeDevice(name="flap", servo=5)
        state = ted.__getstate__()
        restored = TrailingEdgeDevice.from_json_dict(state)
        assert restored._servo == 5

    @requires_cadquery
    def test_roundtrip_servo_object(self):
        servo = _make_servo()
        ted = TrailingEdgeDevice(name="flap", servo=servo)
        state = ted.__getstate__()
        restored = TrailingEdgeDevice.from_json_dict(state)
        assert isinstance(restored._servo, Servo)
        assert restored._servo.length == servo.length
        assert restored._servo.width == servo.width
        assert restored._servo.height == servo.height
