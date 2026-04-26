"""Tests for cross-section CRUD on WC-mode wings (gh-349).

Verifies that adding, deleting, and bulk-deleting cross-sections works
on wings with design_model='wc', not just 'asb'.
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


def _seed_wc_wing(client: TestClient, name: str = "wc_test") -> str:
    """Create an aeroplane with a WC wing (design_model='wc')."""
    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code == 201
    aeroplane_id = resp.json()["id"]

    wc = {
        "segments": [
            {
                "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
                "spare_list": [],
            }
        ],
        "nose_pnt": [0, 0, 0],
    }
    resp = client.post(f"/aeroplanes/{aeroplane_id}/wings/w/from-wingconfig", json=wc)
    assert resp.status_code == 201, resp.text
    return aeroplane_id


class TestWcWingXsecCrud:

    def test_add_cross_section_to_wc_wing(self, client):
        aid = _seed_wc_wing(client, "wc_add")
        new_xsec = {
            "xyz_le": [0, 0.6, 0],
            "chord": 0.1,
            "twist": 0,
            "airfoil": "naca0012",
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/w/cross_sections/2", json=new_xsec)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_delete_cross_section_from_wc_wing(self, client):
        aid = _seed_wc_wing(client, "wc_del")
        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections")
        assert len(resp.json()) == 2

        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections")
        assert len(resp.json()) == 1

    def test_delete_all_cross_sections_from_wc_wing(self, client):
        aid = _seed_wc_wing(client, "wc_del_all")
        resp = client.delete(f"/aeroplanes/{aid}/wings/w/cross_sections")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_update_cross_section_on_wc_wing(self, client):
        aid = _seed_wc_wing(client, "wc_update")
        updated_xsec = {
            "xyz_le": [0, 0, 0],
            "chord": 0.2,
            "twist": 2.0,
            "airfoil": "naca2412",
        }
        resp = client.put(f"/aeroplanes/{aid}/wings/w/cross_sections/0", json=updated_xsec)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_insert_cross_section_into_wc_wing(self, client):
        aid = _seed_wc_wing(client, "wc_insert")
        new_xsec = {
            "xyz_le": [0, 0.25, 0],
            "chord": 0.135,
            "twist": 0,
            "airfoil": "naca0012",
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/w/cross_sections/1", json=new_xsec)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        resp = client.get(f"/aeroplanes/{aid}/wings/w/cross_sections")
        assert resp.status_code == 200
        assert len(resp.json()) == 3
