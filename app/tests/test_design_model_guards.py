"""Tests for design_model API endpoint guards (gh#162).

Verifies that WC wings reject ASB write endpoints (409) and vice versa,
while read endpoints remain accessible for both design models.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.aeroplanemodel import AeroplaneModel

airfoil_path = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)

MINIMAL_WINGCONFIG = {
    "segments": [
        {
            "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
            "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
            "length": 500.0,
            "sweep": 10.0,
            "number_interpolation_points": 101,
        }
    ],
    "nose_pnt": [0, 0, 0],
}


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


@pytest.fixture()
def db(client_and_db):
    _, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_aeroplane(client: TestClient, name: str) -> str:
    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_wc_wing(client: TestClient, aeroplane_id: str, wing_name: str = "w") -> None:
    resp = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
        json=MINIMAL_WINGCONFIG,
    )
    assert resp.status_code == 201, resp.text


def _create_asb_wing(client: TestClient, aeroplane_id: str, wing_name: str = "w") -> None:
    asb_wing = {
        "name": wing_name,
        "x_secs": [
            {"xyz_le": [0, 0, 0], "chord": 0.15, "twist": 0, "airfoil": "naca0012"},
            {"xyz_le": [0.01, 0.5, 0], "chord": 0.12, "twist": 0, "airfoil": "naca0012"},
        ],
        "symmetric": True,
    }
    resp = client.put(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}", json=asb_wing)
    assert resp.status_code == 201, resp.text


class TestWcWingGuards:
    """WC wings must reject ASB write endpoints with 409."""

    def test_wc_wing_rejects_asb_update(self, client):
        aid = _create_aeroplane(client, "wc_guard_update")
        _create_wc_wing(client, aid)
        asb_wing = {
            "name": "w",
            "x_secs": [
                {"xyz_le": [0, 0, 0], "chord": 0.15, "twist": 0, "airfoil": "naca0012"},
                {"xyz_le": [0.01, 0.5, 0], "chord": 0.12, "twist": 0, "airfoil": "naca0012"},
            ],
            "symmetric": True,
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/w", json=asb_wing)
        assert resp.status_code == 409
        assert "design_model='wc'" in resp.json()["detail"]

    def test_wc_wing_rejects_cross_section_create(self, client):
        aid = _create_aeroplane(client, "wc_guard_xsec")
        _create_wc_wing(client, aid)
        xsec = {"xyz_le": [0, 0.3, 0], "chord": 0.1, "twist": 0, "airfoil": "naca0012"}
        resp = client.post(f"/aeroplanes/{aid}/wings/w/cross_sections/0", json=xsec)
        assert resp.status_code == 409

    def test_wc_wing_allows_wingconfig_put(self, client):
        aid = _create_aeroplane(client, "wc_guard_wc_put")
        _create_wc_wing(client, aid)
        resp = client.put(
            f"/aeroplanes/{aid}/wings/w/wingconfig",
            json=MINIMAL_WINGCONFIG,
        )
        assert resp.status_code == 200

    def test_wc_wing_allows_get_as_asb(self, client):
        aid = _create_aeroplane(client, "wc_guard_get_asb")
        _create_wc_wing(client, aid)
        resp = client.get(f"/aeroplanes/{aid}/wings/w")
        assert resp.status_code == 200

    def test_wc_wing_allows_get_as_wingconfig(self, client):
        aid = _create_aeroplane(client, "wc_guard_get_wc")
        _create_wc_wing(client, aid)
        resp = client.get(f"/aeroplanes/{aid}/wings/w/wingconfig")
        assert resp.status_code == 200

    def test_wc_wing_allows_delete(self, client):
        aid = _create_aeroplane(client, "wc_guard_del")
        _create_wc_wing(client, aid)
        resp = client.delete(f"/aeroplanes/{aid}/wings/w")
        assert resp.status_code == 200


class TestAsbWingGuards:
    """ASB wings must reject WC write endpoints with 409."""

    def test_asb_wing_rejects_wingconfig_put(self, client):
        aid = _create_aeroplane(client, "asb_guard_wc_put")
        _create_asb_wing(client, aid)
        resp = client.put(
            f"/aeroplanes/{aid}/wings/w/wingconfig",
            json=MINIMAL_WINGCONFIG,
        )
        assert resp.status_code == 409
        assert "design_model='asb'" in resp.json()["detail"]

    def test_asb_wing_rejects_from_wingconfig_overwrite(self, client):
        """from-wingconfig POST on a name that already has an ASB wing -> 409."""
        aid = _create_aeroplane(client, "asb_guard_wc_create")
        _create_asb_wing(client, aid)
        resp = client.post(
            f"/aeroplanes/{aid}/wings/w/from-wingconfig",
            json=MINIMAL_WINGCONFIG,
        )
        assert resp.status_code == 409

    def test_asb_wing_allows_asb_update(self, client):
        aid = _create_aeroplane(client, "asb_guard_asb_up")
        _create_asb_wing(client, aid)
        asb_wing = {
            "name": "w",
            "x_secs": [
                {"xyz_le": [0, 0, 0], "chord": 0.15, "twist": 0, "airfoil": "naca0012"},
                {"xyz_le": [0.01, 0.5, 0], "chord": 0.12, "twist": 0, "airfoil": "naca0012"},
            ],
            "symmetric": True,
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/w", json=asb_wing)
        assert resp.status_code == 200

    def test_asb_wing_allows_cross_section_crud(self, client):
        aid = _create_aeroplane(client, "asb_guard_xsec")
        _create_asb_wing(client, aid)
        # Create
        xsec = {"xyz_le": [0.01, 0.3, 0], "chord": 0.1, "twist": 0, "airfoil": "naca0012"}
        resp = client.post(f"/aeroplanes/{aid}/wings/w/cross_sections/1", json=xsec)
        assert resp.status_code == 201
        # Update
        resp = client.put(f"/aeroplanes/{aid}/wings/w/cross_sections/1", json=xsec)
        assert resp.status_code == 200
        # Delete
        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections/1")
        assert resp.status_code == 200

    def test_asb_wing_allows_get_as_wingconfig(self, client):
        aid = _create_aeroplane(client, "asb_guard_get_wc")
        _create_asb_wing(client, aid)
        resp = client.get(f"/aeroplanes/{aid}/wings/w/wingconfig")
        assert resp.status_code == 200

    def test_asb_wing_allows_delete(self, client):
        aid = _create_aeroplane(client, "asb_guard_del")
        _create_asb_wing(client, aid)
        resp = client.delete(f"/aeroplanes/{aid}/wings/w")
        assert resp.status_code == 200


class TestCreationGuards:
    """PUT wings/{name} allows creation of new wings regardless of design_model."""

    def test_put_creates_new_asb_wing(self, client):
        aid = _create_aeroplane(client, "create_guard_asb")
        asb_wing = {
            "name": "new_wing",
            "x_secs": [
                {"xyz_le": [0, 0, 0], "chord": 0.15, "twist": 0, "airfoil": "naca0012"},
                {"xyz_le": [0.01, 0.5, 0], "chord": 0.12, "twist": 0, "airfoil": "naca0012"},
            ],
            "symmetric": True,
        }
        resp = client.put(f"/aeroplanes/{aid}/wings/new_wing", json=asb_wing)
        assert resp.status_code == 201

    def test_from_wingconfig_creates_new_wc_wing(self, client):
        aid = _create_aeroplane(client, "create_guard_wc")
        resp = client.post(
            f"/aeroplanes/{aid}/wings/new_wing/from-wingconfig",
            json=MINIMAL_WINGCONFIG,
        )
        assert resp.status_code == 201
