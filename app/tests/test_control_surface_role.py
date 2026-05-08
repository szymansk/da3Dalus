import pytest
from app.schemas.aeroplaneschema import (
    ControlSurfaceRole,
    TrailingEdgeDeviceDetailSchema,
    TrailingEdgeDevicePatchSchema,
)


class TestControlSurfaceRole:
    def test_enum_values(self):
        assert ControlSurfaceRole.ELEVATOR == "elevator"
        assert ControlSurfaceRole.FLAP == "flap"
        assert ControlSurfaceRole.OTHER == "other"

    def test_all_roles_present(self):
        expected = {"elevator", "aileron", "rudder", "elevon", "stabilator", "flap", "spoiler", "other"}
        assert {r.value for r in ControlSurfaceRole} == expected


class TestTedSchemaRoleField:
    def test_role_defaults_to_other(self):
        ted = TrailingEdgeDeviceDetailSchema()
        assert ted.role == ControlSurfaceRole.OTHER

    def test_role_set_explicitly(self):
        ted = TrailingEdgeDeviceDetailSchema(role="elevator")
        assert ted.role == ControlSurfaceRole.ELEVATOR

    def test_label_optional(self):
        ted = TrailingEdgeDeviceDetailSchema(role="aileron", label="Left Aileron")
        assert ted.label == "Left Aileron"

    def test_name_computed_from_role_when_no_label(self):
        ted = TrailingEdgeDeviceDetailSchema(role="elevator")
        assert ted.name == "elevator"

    def test_name_computed_from_label_when_present(self):
        ted = TrailingEdgeDeviceDetailSchema(role="aileron", label="Left Aileron")
        assert ted.name == "Left Aileron"

    def test_name_field_still_accepted_for_backwards_compat(self):
        ted = TrailingEdgeDeviceDetailSchema(name="Höhenruder", role="elevator")
        assert ted.role == ControlSurfaceRole.ELEVATOR
        assert ted.name == "Höhenruder"

    def test_invalid_role_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TrailingEdgeDeviceDetailSchema(role="invalid_role")


class TestTedPatchSchemaRoleField:
    def test_patch_with_role_only(self):
        patch = TrailingEdgeDevicePatchSchema(role="flap")
        assert patch.role == ControlSurfaceRole.FLAP

    def test_patch_with_label_only(self):
        patch = TrailingEdgeDevicePatchSchema(label="Inboard Flap")
        assert patch.label == "Inboard Flap"


from app.converters.model_schema_converters import _control_surface_from_ted


class TestConverterRoleEncoding:
    def test_role_encoded_in_name(self):
        ted = TrailingEdgeDeviceDetailSchema(role="elevator")
        cs = _control_surface_from_ted(ted)
        assert cs.name == "[elevator]elevator"

    def test_role_with_label_encoded(self):
        ted = TrailingEdgeDeviceDetailSchema(role="aileron", label="Left Aileron")
        cs = _control_surface_from_ted(ted)
        assert cs.name == "[aileron]Left Aileron"

    def test_other_role_uses_name(self):
        ted = TrailingEdgeDeviceDetailSchema(role="other", name="Custom Thing")
        cs = _control_surface_from_ted(ted)
        assert cs.name == "[other]Custom Thing"


# ================================================================== #
# Role-based detection in OP generator service
# ================================================================== #

from unittest.mock import MagicMock
from app.services.operating_point_generator_service import (
    _detect_control_capabilities,
    _pick_control_name,
)


def _mock_airplane_with_controls(names: list[str]):
    airplane = MagicMock()
    xsec = MagicMock()
    controls = []
    for n in names:
        cs = MagicMock()
        cs.name = n
        controls.append(cs)
    xsec.control_surfaces = controls
    wing = MagicMock()
    wing.xsecs = [xsec]
    airplane.wings = [wing]
    return airplane


class TestRoleBasedDetection:
    def test_detect_elevator_by_role(self):
        airplane = _mock_airplane_with_controls(["[elevator]Höhenruder"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True

    def test_detect_aileron_by_role(self):
        airplane = _mock_airplane_with_controls(["[aileron]Querruder"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_roll_control"] is True

    def test_detect_rudder_by_role(self):
        airplane = _mock_airplane_with_controls(["[rudder]Seitenruder"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_yaw_control"] is True

    def test_detect_flap_by_role(self):
        airplane = _mock_airplane_with_controls(["[flap]Landeklappe"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_flap"] is True

    def test_no_flap_when_none_present(self):
        airplane = _mock_airplane_with_controls(["[elevator]Elevator"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_flap"] is False

    def test_elevon_detected_as_both_pitch_and_roll(self):
        airplane = _mock_airplane_with_controls(["[elevon]Elevon"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True
        assert caps["has_roll_control"] is True

    def test_other_role_not_detected_as_control(self):
        airplane = _mock_airplane_with_controls(["[other]Custom"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is False
        assert caps["has_roll_control"] is False
        assert caps["has_yaw_control"] is False
        assert caps["has_flap"] is False

    def test_fallback_to_substring_for_untagged_names(self):
        airplane = _mock_airplane_with_controls(["elevator"])
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True


class TestRoleBasedPickControl:
    def test_pick_by_role_tag(self):
        result = _pick_control_name(
            ["[aileron]Left Aileron", "[elevator]Höhenruder"],
            roles={"elevator"},
        )
        assert result == "[elevator]Höhenruder"

    def test_pick_flap(self):
        result = _pick_control_name(
            ["[elevator]Elevator", "[flap]Inboard Flap"],
            roles={"flap"},
        )
        assert result == "[flap]Inboard Flap"
