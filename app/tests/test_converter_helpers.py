"""Tests for private helper functions in model_schema_converters.

These tests cover the refactored ternary expressions (_control_surface_from_ted)
and servo conversion helpers (_servo_to_schema, _servo_to_wing_servo, _to_payload)
from GH #192 (S3358, S1542).

They import only the helper functions — NOT the full converter module — to avoid
requiring aerosandbox/cadquery at import time.
"""

import pytest

# These helpers are private but we test them to cover the refactored ternary paths.
# They live in a module that imports aerosandbox at module level, so we must
# skip if aerosandbox is unavailable.
asb = pytest.importorskip("aerosandbox")
pytest.importorskip("cadquery")

pytestmark = [
    pytest.mark.requires_cadquery,
    pytest.mark.requires_aerosandbox,
]

from app import schemas  # noqa: E402
from app.converters.model_schema_converters import (  # noqa: E402
    _control_surface_from_ted,
    _servo_to_schema,
    _servo_to_wing_servo,
    _to_payload,
)


# ---------------------------------------------------------------------------
# _to_payload
# ---------------------------------------------------------------------------

class TestToPayload:
    def test_none_returns_none(self):
        assert _to_payload(None) is None

    def test_pydantic_model_returns_dict(self):
        cs = schemas.ControlSurfaceSchema(name="Aileron")
        result = _to_payload(cs)
        assert isinstance(result, dict)
        assert result["name"] == "Aileron"

    def test_dict_passes_through(self):
        d = {"key": "value"}
        assert _to_payload(d) is d

    def test_plain_object_uses_dict(self):
        class Obj:
            def __init__(self):
                self.x = 1
                self._private = 2
        result = _to_payload(Obj())
        assert result == {"x": 1}

    def test_primitive_passes_through(self):
        assert _to_payload(42) == 42
        assert _to_payload("hello") == "hello"


# ---------------------------------------------------------------------------
# _servo_to_schema
# ---------------------------------------------------------------------------

class TestServoToSchema:
    def test_none_returns_none(self):
        assert _servo_to_schema(None) is None

    def test_int_returns_int(self):
        assert _servo_to_schema(3) == 3

    def test_pydantic_servo_converts(self):
        from app.schemas.Servo import Servo as ServoSchema

        data = ServoSchema(
            length=10.0, width=5.0, height=3.0,
            leading_length=4.0, latch_z=1.0, latch_x=2.0,
            latch_thickness=0.5, latch_length=3.0,
            cable_z=1.5, screw_hole_lx=2.0, screw_hole_d=0.3,
        )
        result = _servo_to_schema(data)
        assert result is not None
        assert result.length == 10.0

    def test_dict_with_invalid_data_returns_none(self):
        result = _servo_to_schema({"bad": "data"})
        assert result is None


# ---------------------------------------------------------------------------
# _servo_to_wing_servo
# ---------------------------------------------------------------------------

class TestServoToWingServo:
    def test_none_returns_none(self):
        assert _servo_to_wing_servo(None) is None

    def test_int_returns_int(self):
        assert _servo_to_wing_servo(5) == 5

    def test_dict_with_invalid_data_returns_none(self):
        result = _servo_to_wing_servo({"bad": "data"})
        assert result is None


# ---------------------------------------------------------------------------
# _control_surface_from_ted — refactored ternary branches (S3358)
# ---------------------------------------------------------------------------

class TestControlSurfaceFromTed:
    """Each test targets a specific branch of the if/elif/else chains."""

    def test_all_fields_from_ted(self):
        """When TED has all values, use them directly (first branch)."""
        ted = schemas.TrailingEdgeDeviceDetailSchema(
            name="Aileron",
            rel_chord_root=0.75,
            symmetric=False,
            deflection_deg=15.0,
        )
        result = _control_surface_from_ted(ted)
        assert result.name == "Aileron"
        assert result.hinge_point == 0.75
        assert result.symmetric is False
        assert result.deflection == 15.0

    def test_fallback_values_from_existing_control_surface(self):
        """When TED fields are None but fallback exists, use fallback (elif branch).

        NOTE: deflection_deg defaults to 0.0 (not None) in the schema, so the
        deflection fallback branch is unreachable for default-constructed TEDs.
        We explicitly set deflection_deg=None to test that path.
        """
        ted = schemas.TrailingEdgeDeviceDetailSchema(deflection_deg=None)
        fallback = schemas.ControlSurfaceSchema(
            name="Existing Flap",
            hinge_point=0.7,
            symmetric=True,
            deflection=10.0,
        )
        result = _control_surface_from_ted(ted, fallback=fallback)
        assert result.hinge_point == 0.7
        assert result.symmetric is True
        assert result.deflection == 10.0

    def test_default_values_when_no_fallback(self):
        """When TED fields are None and no fallback, use hardcoded defaults (else branch).

        NOTE: deflection_deg defaults to 0.0 in the schema, so we explicitly
        set it to None to reach the else branch for deflection.
        """
        ted = schemas.TrailingEdgeDeviceDetailSchema(deflection_deg=None)
        result = _control_surface_from_ted(ted, fallback=None)
        assert result.hinge_point == 0.8
        assert result.symmetric is True
        assert result.deflection == 0.0
        assert result.name == "Control Surface"

    def test_ted_name_with_fallback_name(self):
        """TED name takes precedence over fallback name."""
        ted = schemas.TrailingEdgeDeviceDetailSchema(name="My TED")
        fallback = schemas.ControlSurfaceSchema(name="Old Name")
        result = _control_surface_from_ted(ted, fallback=fallback)
        assert result.name == "My TED"

    def test_fallback_name_when_ted_has_none(self):
        """Fallback name used when TED name is None."""
        ted = schemas.TrailingEdgeDeviceDetailSchema()
        fallback = schemas.ControlSurfaceSchema(name="Fallback Name")
        result = _control_surface_from_ted(ted, fallback=fallback)
        assert result.name == "Fallback Name"
