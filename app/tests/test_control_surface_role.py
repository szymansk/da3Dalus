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


# ================================================================== #
# TED PATCH endpoint — integration tests (role / label round-trip)
# ================================================================== #

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_AIRFOIL_PATH = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


def _seed_wing_with_ted(client: TestClient, name: str, *, db) -> str:
    """Create an aeroplane + wing (design_model='asb') with one TED on xsec 0."""
    from app.models.aeroplanemodel import AeroplaneModel

    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code == 201
    aeroplane_id = resp.json()["id"]

    wc = {
        "segments": [
            {
                "root_airfoil": {"airfoil": _AIRFOIL_PATH, "chord": 150.0, "incidence": 0},
                "tip_airfoil": {"airfoil": _AIRFOIL_PATH, "chord": 120.0, "incidence": 0},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
                "spare_list": [],
                "trailing_edge_device": {
                    "name": "aileron",
                    "rel_chord_root": 0.8,
                    "rel_chord_tip": 0.8,
                    "positive_deflection_deg": 25,
                    "negative_deflection_deg": 25,
                    "symmetric": False,
                },
            }
        ],
        "nose_pnt": [0, 0, 0],
    }
    resp = client.post(f"/aeroplanes/{aeroplane_id}/wings/w/from-wingconfig", json=wc)
    assert resp.status_code == 201, resp.text

    # Flip design_model to 'asb' so TED CRUD endpoints operate on this wing
    plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
    wing = next(w for w in plane.wings if w.name == "w")
    wing.design_model = "asb"
    db.commit()

    return aeroplane_id


@pytest.fixture()
def _client(client_and_db):
    c, _ = client_and_db
    yield c


@pytest.fixture()
def _db(client_and_db):
    _, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestTedPatchEndpoint:
    def test_patch_ted_with_role(self, _client, _db):
        aid = _seed_wing_with_ted(_client, "ted_role_patch", db=_db)
        resp = _client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device",
            json={"role": "elevator"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["role"] == "elevator"

    def test_patch_ted_with_label(self, _client, _db):
        aid = _seed_wing_with_ted(_client, "ted_label_patch", db=_db)
        resp = _client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device",
            json={"role": "aileron", "label": "Left Aileron"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["role"] == "aileron"
        assert body["label"] == "Left Aileron"
        assert body["name"] == "Left Aileron"

    def test_patch_ted_role_persists_across_get(self, _client, _db):
        aid = _seed_wing_with_ted(_client, "ted_role_persist", db=_db)
        _client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device",
            json={"role": "rudder"},
        )
        resp = _client.get(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "rudder"

    def test_patch_ted_label_without_role_keeps_existing_role(self, _client, _db):
        """Patching only label must not reset role to 'other'."""
        aid = _seed_wing_with_ted(_client, "ted_label_only", db=_db)
        # First set a role
        _client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device",
            json={"role": "flap"},
        )
        # Then patch only the label
        resp = _client.patch(
            f"/aeroplanes/{aid}/wings/w/cross_sections/0/trailing_edge_device",
            json={"label": "Inboard Flap"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["role"] == "flap"
        assert body["label"] == "Inboard Flap"
