"""Tests for GET/PUT /aeroplanes/{id}/wings/{name}/wingconfig endpoints.

Exercises the full round-trip: create an aeroplane and wing via the
from-wingconfig endpoint, then read back the wing configuration via GET,
update it via PUT, and verify the update sticks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


airfoil_path = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


def _make_wingconfig(root_chord: float = 150.0) -> dict:
    """Return a minimal WingConfiguration payload with one segment."""
    return {
        "segments": [
            {
                "root_airfoil": {"airfoil": airfoil_path, "chord": root_chord, "incidence": 0},
                "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
            }
        ],
        "nose_pnt": [0, 0, 0],
        "symmetric": True,
    }


def _create_aeroplane_and_wing(client: TestClient, wingconfig: dict) -> str:
    """Create an aeroplane + wing via the REST API, return the aeroplane UUID."""
    resp = client.post("/aeroplanes", params={"name": "wc_test"})
    assert resp.status_code == 201, resp.text
    aeroplane_id = resp.json()["id"]

    resp = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/test_wing/from-wingconfig",
        json=wingconfig,
    )
    assert resp.status_code == 201, resp.text
    return aeroplane_id


def test_get_wingconfig_returns_created_configuration(client):
    """GET wingconfig returns the configuration that was used to create the wing."""
    wingconfig = _make_wingconfig(root_chord=150.0)
    aeroplane_id = _create_aeroplane_and_wing(client, wingconfig)

    resp = client.get(f"/aeroplanes/{aeroplane_id}/wings/test_wing/wingconfig")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert isinstance(body["segments"], list)
    assert len(body["segments"]) == 1

    seg = body["segments"][0]
    assert seg["root_airfoil"]["chord"] == pytest.approx(150.0)
    assert seg["length"] == pytest.approx(500.0)
    assert body["symmetric"] is True


def test_put_wingconfig_updates_configuration(client):
    """PUT wingconfig updates the stored configuration; a subsequent GET reflects the change."""
    wingconfig = _make_wingconfig(root_chord=150.0)
    aeroplane_id = _create_aeroplane_and_wing(client, wingconfig)

    # Mutate the config and PUT it back.
    updated_config = _make_wingconfig(root_chord=200.0)
    resp = client.put(
        f"/aeroplanes/{aeroplane_id}/wings/test_wing/wingconfig",
        json=updated_config,
    )
    assert resp.status_code == 200, resp.text

    # GET again and verify the update took effect.
    resp = client.get(f"/aeroplanes/{aeroplane_id}/wings/test_wing/wingconfig")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["segments"][0]["root_airfoil"]["chord"] == pytest.approx(200.0)


# --------------------------------------------------------------------------- #
# gh#93 — symmetric roundtrip + Servo schema validation
# --------------------------------------------------------------------------- #


def test_symmetric_false_roundtrip(client):
    """POST with symmetric=false → GET returns symmetric=false."""
    wc = _make_wingconfig()
    wc["symmetric"] = False
    aeroplane_id = _create_aeroplane_and_wing(client, wc)

    resp = client.get(f"/aeroplanes/{aeroplane_id}/wings/test_wing/wingconfig")
    assert resp.status_code == 200, resp.text
    assert resp.json()["symmetric"] is False


def test_symmetric_defaults_to_true_when_omitted(client):
    """POST without 'symmetric' key → defaults to True (backward compat)."""
    wc = _make_wingconfig()
    wc.pop("symmetric", None)
    aeroplane_id = _create_aeroplane_and_wing(client, wc)

    resp = client.get(f"/aeroplanes/{aeroplane_id}/wings/test_wing/wingconfig")
    assert resp.status_code == 200, resp.text
    assert resp.json()["symmetric"] is True


def test_servo_with_missing_required_field_returns_422(client):
    """POST a TED with a Servo missing a required field → HTTP 422, not 500."""
    wc = _make_wingconfig()
    wc["segments"][0]["trailing_edge_device"] = {
        "name": "aileron",
        "rel_chord_root": 0.8,
        "servo": {
            "length": 23,
            "width": 12.5,
            # height is missing — required field
            "leading_length": 6,
            "latch_z": 14.5,
            "latch_x": 7.25,
            "latch_thickness": 2.6,
            "latch_length": 6,
            "cable_z": 26,
            "screw_hole_lx": 0,
            "screw_hole_d": 0,
        },
    }
    resp = client.post("/aeroplanes", params={"name": "servo_test"})
    assert resp.status_code == 201
    aeroplane_id = resp.json()["id"]

    resp = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/test_wing/from-wingconfig",
        json=wc,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for missing Servo.height, got {resp.status_code}: {resp.text}"
    )


def test_servo_with_all_fields_accepted(client):
    """POST a TED with a complete Servo → HTTP 201."""
    wc = _make_wingconfig()
    wc["segments"][0]["trailing_edge_device"] = {
        "name": "flap",
        "rel_chord_root": 0.7,
        "servo": {
            "length": 23,
            "width": 12.5,
            "height": 31.5,
            "leading_length": 6,
            "latch_z": 14.5,
            "latch_x": 7.25,
            "latch_thickness": 2.6,
            "latch_length": 6,
            "cable_z": 26,
            "screw_hole_lx": 0,
            "screw_hole_d": 0,
        },
    }
    resp = client.post("/aeroplanes", params={"name": "servo_ok"})
    assert resp.status_code == 201
    aeroplane_id = resp.json()["id"]

    resp = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/test_wing/from-wingconfig",
        json=wc,
    )
    assert resp.status_code == 201, resp.text
