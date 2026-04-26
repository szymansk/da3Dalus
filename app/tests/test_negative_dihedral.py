"""Tests for negative dihedral (anhedral) support in wing schema (gh-353).

Verifies that the API accepts negative dihedral values and that they
survive the WingConfig save/load roundtrip.
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


def _make_wingconfig(tip_dihedral: float) -> dict:
    return {
        "segments": [
            {
                "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0, "dihedral_as_rotation_in_degrees": 0},
                "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0, "dihedral_as_rotation_in_degrees": tip_dihedral},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
            }
        ],
        "nose_pnt": [0, 0, 0],
    }


class TestNegativeDihedral:

    def test_negative_dihedral_accepted(self, client):
        resp = client.post("/aeroplanes", params={"name": "anhedral_test"})
        assert resp.status_code == 201
        aid = resp.json()["id"]

        resp = client.post(f"/aeroplanes/{aid}/wings/w/from-wingconfig", json=_make_wingconfig(-5.0))
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    def test_negative_dihedral_roundtrip(self, client):
        """Interior dihedral survives roundtrip; terminal tip is lossy by design."""
        resp = client.post("/aeroplanes", params={"name": "anhedral_rt"})
        aid = resp.json()["id"]

        wc = {
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0, "dihedral_as_rotation_in_degrees": -5.0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 130.0, "incidence": 0, "dihedral_as_rotation_in_degrees": -3.0},
                    "length": 500.0, "sweep": 10.0, "number_interpolation_points": 101,
                },
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 130.0, "incidence": 0, "dihedral_as_rotation_in_degrees": -3.0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 100.0, "incidence": 0, "dihedral_as_rotation_in_degrees": 0},
                    "length": 300.0, "sweep": 5.0, "number_interpolation_points": 101,
                },
            ],
            "nose_pnt": [0, 0, 0],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/w/from-wingconfig", json=wc)
        assert resp.status_code == 201

        resp = client.get(f"/aeroplanes/{aid}/wings/w/wingconfig")
        assert resp.status_code == 200
        data = resp.json()
        root_d = data["segments"][0]["root_airfoil"]["dihedral_as_rotation_in_degrees"]
        assert root_d == pytest.approx(-5.0, abs=0.5)

    def test_boundary_minus_180(self, client):
        resp = client.post("/aeroplanes", params={"name": "anhedral_180"})
        aid = resp.json()["id"]

        resp = client.post(f"/aeroplanes/{aid}/wings/w/from-wingconfig", json=_make_wingconfig(-180.0))
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    def test_boundary_plus_180(self, client):
        resp = client.post("/aeroplanes", params={"name": "dihedral_180"})
        aid = resp.json()["id"]

        resp = client.post(f"/aeroplanes/{aid}/wings/w/from-wingconfig", json=_make_wingconfig(180.0))
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    def test_out_of_range_rejected(self, client):
        resp = client.post("/aeroplanes", params={"name": "dihedral_oor"})
        aid = resp.json()["id"]

        resp = client.post(f"/aeroplanes/{aid}/wings/w/from-wingconfig", json=_make_wingconfig(181.0))
        assert resp.status_code == 422
