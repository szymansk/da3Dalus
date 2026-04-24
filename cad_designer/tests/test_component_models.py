"""Tests for component information models (Servo, ComponentInformation,
EngineInformation, ServoInformation).

ComponentInformation, EngineInformation, and ServoInformation import OCP.gp
at module level, so they require CadQuery. Tests for those classes are
guarded with requires_cadquery.

Servo imports cadquery at module level (for Workplane/Sketch), so its
data-model tests are also guarded.
"""

import pytest

try:
    from cad_designer.airplane.aircraft_topology.components.Servo import Servo

    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False

requires_cadquery = pytest.mark.skipif(
    not HAS_CADQUERY, reason="CadQuery / OCP not available"
)


# ---------------------------------------------------------------------------
# Servo data model
# ---------------------------------------------------------------------------

@requires_cadquery
class TestServoConstructor:
    """Test Servo.__init__ stores all fields correctly."""

    @pytest.fixture
    def servo(self):
        return Servo(
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

    def test_dimensions(self, servo):
        assert servo.length == 23.0
        assert servo.width == 12.5
        assert servo.height == 25.0

    def test_leading_trailing_length(self, servo):
        assert servo.leading_length == 8.0
        assert servo.trailing_length == 23.0 - 8.0  # length - leading

    def test_latch_params(self, servo):
        assert servo.latch_z == 3.0
        assert servo.latch_x == 2.0
        assert servo.latch_thickness == 1.5
        assert servo.latch_length == 4.0

    def test_cable_and_screws(self, servo):
        assert servo.cable_z == 10.0
        assert servo.screw_hole_lx == 1.0
        assert servo.screw_hole_d == 2.0

    def test_trailing_length_computed(self):
        servo = Servo(
            length=30.0,
            width=10.0,
            height=20.0,
            leading_length=12.0,
            latch_z=0,
            latch_x=0,
            latch_thickness=0,
            latch_length=0,
            cable_z=0,
            screw_hole_lx=0,
            screw_hole_d=0,
        )
        assert servo.trailing_length == 18.0

    def test_zero_leading_length(self):
        """When leading_length is 0, trailing_length equals full length."""
        servo = Servo(
            length=20.0,
            width=10.0,
            height=15.0,
            leading_length=0,
            latch_z=0,
            latch_x=0,
            latch_thickness=0,
            latch_length=0,
            cable_z=0,
            screw_hole_lx=0,
            screw_hole_d=0,
        )
        assert servo.trailing_length == 20.0


@requires_cadquery
class TestServoGetState:
    """Test Servo.__getstate__ serialization."""

    @pytest.fixture
    def servo(self):
        return Servo(
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

    def test_getstate_keys(self, servo):
        state = servo.__getstate__()
        expected_keys = {
            "model",
            "length",
            "width",
            "height",
            "leading_length",
            "latch_z",
            "latch_x",
            "latch_thickness",
            "latch_length",
            "cable_z",
            "screw_hole_lx",
            "screw_hole_d",
            "trailing_length",
        }
        assert set(state.keys()) == expected_keys

    def test_getstate_model_name(self, servo):
        state = servo.__getstate__()
        assert state["model"] == "Servo"

    def test_getstate_values(self, servo):
        state = servo.__getstate__()
        assert state["length"] == 23.0
        assert state["width"] == 12.5
        assert state["height"] == 25.0
        assert state["trailing_length"] == 15.0


@requires_cadquery
class TestServoFromJsonDict:
    """Test Servo.from_json_dict deserialization."""

    def test_roundtrip(self):
        original = Servo(
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
        state = original.__getstate__()
        restored = Servo.from_json_dict(state)

        assert restored.length == original.length
        assert restored.width == original.width
        assert restored.height == original.height
        assert restored.leading_length == original.leading_length
        assert restored.latch_z == original.latch_z
        assert restored.latch_x == original.latch_x
        assert restored.latch_thickness == original.latch_thickness
        assert restored.latch_length == original.latch_length
        assert restored.cable_z == original.cable_z
        assert restored.screw_hole_lx == original.screw_hole_lx
        assert restored.screw_hole_d == original.screw_hole_d
        assert restored.trailing_length == original.trailing_length

    def test_from_json_dict_preserves_trailing_length(self):
        """When trailing_length is in the dict, it should be set."""
        data = {
            "model": "Servo",
            "length": 30.0,
            "width": 10.0,
            "height": 20.0,
            "leading_length": 10.0,
            "latch_z": 0,
            "latch_x": 0,
            "latch_thickness": 0,
            "latch_length": 0,
            "cable_z": 0,
            "screw_hole_lx": 0,
            "screw_hole_d": 0,
            "trailing_length": 20.0,  # length - leading_length
        }
        servo = Servo.from_json_dict(data)
        assert servo.trailing_length == 20.0

    def test_from_json_dict_overrides_computed_trailing_length(self):
        """trailing_length from JSON overrides the computed value."""
        data = {
            "model": "Servo",
            "length": 30.0,
            "width": 10.0,
            "height": 20.0,
            "leading_length": 10.0,
            "latch_z": 0,
            "latch_x": 0,
            "latch_thickness": 0,
            "latch_length": 0,
            "cable_z": 0,
            "screw_hole_lx": 0,
            "screw_hole_d": 0,
            "trailing_length": 99.0,  # intentionally wrong
        }
        servo = Servo.from_json_dict(data)
        # from_json_dict explicitly sets trailing_length from data
        assert servo.trailing_length == 99.0


# ---------------------------------------------------------------------------
# ComponentInformation
# ---------------------------------------------------------------------------

@requires_cadquery
class TestComponentInformation:
    """Test ComponentInformation data model."""

    def test_constructor_defaults(self):
        from cad_designer.airplane.aircraft_topology.components.ComponentInformation import (
            ComponentInformation,
        )

        ci = ComponentInformation(height=10.0, width=20.0, length=30.0)
        assert ci.height == 10.0
        assert ci.width == 20.0
        assert ci.length == 30.0
        assert ci.rot_x == 0.0
        assert ci.rot_y == 0.0
        assert ci.rot_z == 0.0
        assert ci.trans_x == 0.0
        assert ci.trans_y == 0.0
        assert ci.trans_z == 0.0

    def test_constructor_all_params(self):
        from cad_designer.airplane.aircraft_topology.components.ComponentInformation import (
            ComponentInformation,
        )

        ci = ComponentInformation(
            height=10.0,
            width=20.0,
            length=30.0,
            rot_x=1.0,
            rot_y=2.0,
            rot_z=3.0,
            trans_x=4.0,
            trans_y=5.0,
            trans_z=6.0,
        )
        assert ci.rot_x == 1.0
        assert ci.rot_y == 2.0
        assert ci.rot_z == 3.0
        assert ci.trans_x == 4.0
        assert ci.trans_y == 5.0
        assert ci.trans_z == 6.0

    def test_get_corner_point(self):
        from cad_designer.airplane.aircraft_topology.components.ComponentInformation import (
            ComponentInformation,
        )

        ci = ComponentInformation(
            height=10.0, width=20.0, length=30.0,
            trans_x=1.0, trans_y=2.0, trans_z=3.0,
        )
        pt = ci.get_corner_point()
        assert pt.X() == pytest.approx(1.0)
        assert pt.Y() == pytest.approx(2.0)
        assert pt.Z() == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# EngineInformation
# ---------------------------------------------------------------------------

@requires_cadquery
class TestEngineInformation:
    """Test EngineInformation data model."""

    def test_constructor(self):
        from cad_designer.airplane.aircraft_topology.components.EngineInformation import (
            EngineInformation,
        )
        from cad_designer.airplane.aircraft_topology.Position import Position

        pos = Position(x=10.0, y=20.0, z=30.0)
        ei = EngineInformation(
            down_thrust=5.0,
            side_thrust=2.0,
            position=pos,
            length=100.0,
            width=50.0,
            height=40.0,
            screw_hole_circle=15.0,
            mount_box_length=20.0,
            screw_din_diameter=3.0,
            screw_length=10.0,
        )
        assert ei.down_thrust == 5.0
        assert ei.side_thrust == 2.0
        assert ei.position is pos
        assert ei.length == 100.0
        assert ei.width == 50.0
        assert ei.height == 40.0
        assert ei.engine_screw_hole_circle == 15.0
        assert ei.engine_mount_box_length == 20.0
        assert ei.engine_screw_din_diameter == 3.0
        assert ei.engine_screw_length == 10.0

    def test_inherits_component_transforms(self):
        from cad_designer.airplane.aircraft_topology.components.EngineInformation import (
            EngineInformation,
        )
        from cad_designer.airplane.aircraft_topology.Position import Position

        pos = Position(x=10.0, y=20.0, z=30.0)
        ei = EngineInformation(
            down_thrust=5.0,
            side_thrust=2.0,
            position=pos,
            length=100.0,
            width=50.0,
            height=40.0,
            screw_hole_circle=15.0,
            mount_box_length=20.0,
            screw_din_diameter=3.0,
            screw_length=10.0,
        )
        # super().__init__ maps position coords to trans_* and thrusts to rot_*
        assert ei.trans_x == 10.0
        assert ei.trans_y == 20.0
        assert ei.trans_z == 30.0
        assert ei.rot_y == 5.0   # down_thrust
        assert ei.rot_z == 2.0   # side_thrust

    def test_rot_x_default_and_custom(self):
        from cad_designer.airplane.aircraft_topology.components.EngineInformation import (
            EngineInformation,
        )
        from cad_designer.airplane.aircraft_topology.Position import Position

        pos = Position(x=0, y=0, z=0)
        defaults = dict(
            down_thrust=0, side_thrust=0, position=pos,
            length=10, width=10, height=10,
            screw_hole_circle=5, mount_box_length=5,
            screw_din_diameter=2, screw_length=5,
        )
        ei_default = EngineInformation(**defaults)
        assert ei_default.rot_x == 0.0

        ei_custom = EngineInformation(**defaults, rot_x=15.0)
        assert ei_custom.rot_x == 15.0


# ---------------------------------------------------------------------------
# ServoInformation
# ---------------------------------------------------------------------------

@requires_cadquery
class TestServoInformation:
    """Test ServoInformation data model."""

    def test_constructor_with_servo(self):
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        servo = Servo(
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
        si = ServoInformation(
            height=25.0,
            width=12.5,
            length=23.0,
            lever_length=5.0,
            servo=servo,
        )
        assert si.lever_length == 5.0
        assert si.servo is servo

    def test_dimensions_come_from_servo(self):
        """length, width, height properties delegate to the servo."""
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        servo = Servo(
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
        si = ServoInformation(
            height=1.0,  # ignored -- property reads from servo
            width=1.0,
            length=1.0,
            lever_length=5.0,
            servo=servo,
        )
        assert si.length == 23.0
        assert si.width == 12.5
        assert si.height == 25.0

    def test_auto_created_servo_when_none_provided(self):
        """When no servo is passed, a default Servo is created from dimensions."""
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        si = ServoInformation(
            height=25.0,
            width=12.5,
            length=23.0,
            lever_length=5.0,
        )
        assert si.servo is not None
        assert si.servo.length == 23.0
        assert si.servo.width == 12.5
        assert si.servo.height == 25.0

    def test_transform_defaults(self):
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        si = ServoInformation(
            height=25.0, width=12.5, length=23.0, lever_length=5.0,
        )
        assert si.trans_x == 0.0
        assert si.trans_y == 0.0
        assert si.trans_z == 0.0
        assert si.rot_x == 0.0
        assert si.rot_y == 0.0
        assert si.rot_z == 0.0

    def test_transform_custom(self):
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        si = ServoInformation(
            height=25.0,
            width=12.5,
            length=23.0,
            lever_length=5.0,
            trans_x=1.0,
            trans_y=2.0,
            trans_z=3.0,
            rot_x=10.0,
            rot_y=20.0,
            rot_z=30.0,
        )
        assert si.trans_x == 1.0
        assert si.trans_y == 2.0
        assert si.trans_z == 3.0
        assert si.rot_x == 10.0
        assert si.rot_y == 20.0
        assert si.rot_z == 30.0

    def test_dimension_setters_are_noop(self):
        """The property setters for length/width/height are no-ops."""
        from cad_designer.airplane.aircraft_topology.components.ServoInformation import (
            ServoInformation,
        )

        servo = Servo(
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
        si = ServoInformation(
            height=25.0, width=12.5, length=23.0,
            lever_length=5.0, servo=servo,
        )
        # Setters are intentionally no-ops
        si.length = 999.0
        si.width = 999.0
        si.height = 999.0
        # Values unchanged -- backed by servo
        assert si.length == 23.0
        assert si.width == 12.5
        assert si.height == 25.0
