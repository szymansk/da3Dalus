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
